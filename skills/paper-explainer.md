---
name: paper-explainer
description: "Compresses a thorough deep-reading of a research paper into a single beautiful 1-pager HTML — including a TL;DR, problem/method breakdown with section anchors (e.g. §3.2, Eq. 4, Table 4), a custom SVG architecture diagram, attributed key results, nuances most summaries miss, and a related-papers knowledge base. Reads the paper body in full, the source code when available, and follows citations into related work as needed. Accepts arXiv URLs (e.g., https://arxiv.org/abs/2301.07041), bare arXiv IDs (e.g., 2301.07041), or local PDF file paths. Output lands in $PAPER_EXPLAINER_OUTPUT_DIR/<paper-slug>/ (defaults to ~/papers/). Use when the user wants to explain, summarize, visualize, understand, or break down a research paper, build a paper one-pager, or generate a paper summary page. Also use when the user pastes an arxiv URL/ID or PDF path with phrases like 'explain this paper', 'make a 1-pager', or 'summarize this'."
---

# Paper Explainer

The goal of this skill is to **compress a thorough understanding of the paper into a beautiful page** — not to produce a generic AI summary. Read the paper carefully (full body, methodology, ablations, appendix when relevant), read the source code when available, and follow citations into related papers when context demands. Then compress all of that into a single visual page that lets the reader grasp the contributions at a glance, with explicit pointers (§3.2, Eq. 4, Table 4, Fig. 5, Appendix B.1) so they can dive into nuance whenever they want.

**Tone**: senior researcher's compressed notes. Use the paper's own terminology. Numbers, equations, and section pointers — not generic adjectives. Skip phrases like "groundbreaking", "revolutionary", "this paper proposes". Just say what it does and where to find more.

**Input**: the user provides one of
- an arXiv URL (`https://arxiv.org/abs/XXXX.XXXXX` or `https://arxiv.org/pdf/XXXX.XXXXX`)
- a bare arXiv ID (`XXXX.XXXXX`)
- a local PDF file path

---

## Output directory

The output directory is `$PAPER_EXPLAINER_OUTPUT_DIR` if set, otherwise `~/papers/`. Resolve it once at the start of every run with:
```bash
PAPERS_DIR="${PAPER_EXPLAINER_OUTPUT_DIR:-$HOME/papers}"
```
and use `$PAPERS_DIR` everywhere below. All file references in this spec assume this resolution.

All files for this paper live in `$PAPERS_DIR/<safe-kebab-title>/`:
- `<safe-kebab-title>.html` — the visual explainer
- `figure.png` — extracted teaser/architecture figure from the PDF (when one figure is enough)
- `figure-1.png` + `figure-2.png` — when two complementary figures are extracted
- `memory-bank.md` — list of all discovered papers, with the main paper marked `analyzed`
- `mind-graph.md` — topic-paper connection graph
- `references.bib` — BibTeX for all papers
- `summaries/` — per-paper deep dives (on request only)
- `discussions/` — comparison notes (on request only)

A shared cache lives at `$PAPERS_DIR/.cache/<arxiv-id>/` with subkeys `metadata.xml`, `body.txt`, `references.json`, `readme.md`, `project-page.md`, `<arxiv-id>.pdf`. Use it: before any WebFetch in Step 2, check whether the cache file exists; if so, read it and skip the network call. Cache is append-only during a run — never delete entries mid-run. Pruning between runs is safe: `rm -rf $PAPERS_DIR/.cache` only drops fetch caches and never touches paper folders, summaries, or `index.html`. If the user asks to "clear the cache" or notices stale data (e.g. a paper was revised on arXiv), it's safe to remove the single `$PAPERS_DIR/.cache/<arxiv-id>/` subfolder for that paper.

A global index lives at `$PAPERS_DIR/index.html` listing every explained paper; regenerate it after each successful run.

Create the paper's directory and `$PAPERS_DIR/.cache/<arxiv-id>/` before fetching anything.

---

## Step 0 — Confirm model (mandatory; ask once, before any other work)

Before touching the filesystem or the network, ask the user one short question and wait for their answer:

> This run will use **Sonnet (latest, max thinking)** as the default. Want to switch to **Opus (latest, 1M context, max thinking)** for this paper instead? (`y` = switch to Opus / `n` / Enter = stay on Sonnet)

Rules:
- Ask only once per session — if the user already answered for an earlier paper in the same session, don't ask again.
- If `y`: tell the user to run `/model opus[1m]` (and `/effort max` if not already set), then resume the skill from Step 1 in the upgraded session. Do not try to switch models yourself.
- If `n` / Enter / anything else: continue on the current model.
- Skip both the question and the switch entirely if the user explicitly pinned a model in their request (e.g. "use opus", "stay on sonnet").

This step exists because deep paper reading benefits a lot from the strongest model when the paper is dense or long, but Sonnet is the right default for cost/latency on the average paper.

---

## Step 1 — Resolve input

- `https://arxiv.org/abs/XXXX.XXXXX` or `https://arxiv.org/pdf/XXXX.XXXXX` → ID is `XXXX.XXXXX`
- Bare `XXXX.XXXXX` → use as-is
- PDF file path → no arXiv ID; jump to **Step 2 (PDF branch)**

**Skip if already done**. Before doing anything else, check whether `$PAPERS_DIR/<safe-kebab-title>/<safe-kebab-title>.html` already exists. If it does, ask the user one short question: regenerate from scratch / update related-work only / open the existing one / skip. Do not silently overwrite.

---

## Step 2 — Fetch raw paper data (run all in parallel)

For each fetch below, **first check** `$PAPERS_DIR/.cache/<arxiv-id>/<key>` — if it exists, read it instead of fetching. After a successful fetch, write the response to that path so the next run is free.

**Metadata** — cache key `metadata.xml` — `https://export.arxiv.org/api/query?id_list=<ID>`
Extract: title, authors, published date, abstract, categories.

**Full text** — cache key `body.txt` — try in order until one succeeds:
1. `https://ar5iv.org/html/<ID>` (follow redirects to ar5iv.labs.arxiv.org)
2. `https://arxiv.org/html/<ID>` (modern HTML rendering)
3. PDF download via `curl -sL https://arxiv.org/pdf/<ID> -o $PAPERS_DIR/.cache/<ID>/<ID>.pdf` then `pdftotext -layout` (or PyMuPDF)

Keep the body text with section headings preserved (so section pointers like "§3.2" are recoverable).

**Cited papers** — cache key `references.json` — `https://api.semanticscholar.org/graph/v1/paper/arXiv:<ID>/references?fields=title,authors,year,venue,externalIds,citationCount&limit=50`. Sort by `citationCount` desc. Note: the public Semantic Scholar endpoint sometimes returns 402 Payment Required; if so, fall back to extracting the reference list from the paper body.

**GitHub repo locator** — cache key `github_url.txt` — WebSearch `"<paper title>" arxiv github` and any URL printed in the abstract.

**Project page locator** — cache key `project_page_url.txt` — many papers have an associated project page or blog (e.g., `lambertae.github.io/projects/drifting/`, `gdm-tipsv2.github.io/`). It's typically linked in the arXiv abstract's "Comments" field, in the GitHub README, or via `WebSearch "<paper title>" project page`. Save the URL for Step 3 — project pages have author-curated TL;DRs, training-dynamics figures, sample galleries, demo links, and an authoritative BibTeX entry.

**PDF branch**: read locally via `pdftotext -layout <path> -` or PyMuPDF. Extract title/authors from page 1.

---

## Step 3 — Deep reading (mandatory before any HTML)

Most generic AI summaries skip this. This is what makes the output useful.

### Read the paper body

Walk through the full body. Keep a scratchpad with **section anchors** as you go:

- **Method** — record exact equation labels (Eq. 4, Eq. 9), the section number where each component is defined, and any non-obvious design decisions
- **Experiments** — record the table number and dataset+metric combination behind every headline number you'll cite
- **Ablations** — these almost always reveal what the authors found surprising; note which components contribute which gain
- **Limitations / Discussion / Appendix** — record any acknowledged failure mode, hyperparameter sensitivity, or finding the abstract glossed over

### Read the code (if available)

If a GitHub repo is found:
1. Fetch the README (`/main/README.md` then `/master/README.md`)
2. List the repo tree and identify the actual model + loss + training files (not just the README)
3. Read the **loss function** and the **forward pass** of the main model — these reveal the real algorithm
4. Read the default config — note the actual hyperparameters used (often differ from paper claims)
5. If anything in the code contradicts or refines the paper, note it as a nuance for Step 5

Don't dump the full repo into context. Pick the 3-5 files that matter.

### Read the project page (if available)

If a project page URL was found in Step 2, fetch it via `WebFetch`. Project pages often contain content the paper PDF doesn't:

- An **author-curated TL;DR** with the framing the authors chose for non-specialists. If it's well-phrased and matches your understanding, lift selected sentences (with quotes) into the explainer's TL;DR or Key Equations & Quotes section.
- **Training-dynamics GIFs / videos** showing the method in motion (e.g., distributions evolving). These can be linked from the explainer's footer under a small "Resources" line.
- **Gallery of sample outputs** — useful as a mention ("see project page for uncurated samples") but don't try to embed many images.
- **Official BibTeX** — sometimes differs from the auto-derived one (e.g., updated venue, conference vs. preprint). Use this in `references.bib` if found.
- **Demo links / Colab notebooks** — surface in the header pills as "demo" or in the footer.

Add the project page link as a header pill if not already present.

### Follow citations only when needed

For any concept the paper treats as known (e.g. "we use iBOT-style distillation"), fetch the cited paper's abstract + the one defining section. Don't traverse more than 1 hop unless the user asked for a comparison.

### Extract the teaser figure(s)

The "FROM THE PAPER" section embeds **one or two figures** from the paper. The goal is to **complement the SVG diagram**, not duplicate it.

#### Selection criteria — pick figures that complement the SVG

First, classify each figure in the paper by reading its caption (every paper has all captions in the body text). Common types:

| Type | Examples | Use as embedded figure? |
|------|----------|-------------------------|
| **architecture / pipeline** | "Illustration of <Method>: First, we ...", "<Method> overview" | **Avoid if it duplicates the SVG.** Most SVG diagrams already serve this role. |
| **concept / mechanism** | "Geometric illustration of $\mathbf{V}$", "How <X> attracts and repels samples" | **Strong complement** — visualizes intuition the SVG can only label |
| **qualitative results** | "Examples of generated samples", "CT slices + GT masks + predictions" | **Strong complement** — shows what the model actually produces |
| **qualitative comparison** | "Side-by-side with baselines" | **Strong complement** when the paper's edge is mostly visual |
| **chart / scaling / ablation** | "FID vs CFG scale", "AUROC by training step" | **Avoid** — these belong in Key Results as metric cards or text |
| **teaser / motivational** | "$q$ evolves toward $p$ over training", "Failure mode demo" | **Good** — sets up the story |

**Decision rule**: pick **Fig 1 by default**. Only deviate if Fig 1 is *purely an architecture overview* that duplicates the SVG (in that case use Fig 2 or 3, whichever is qualitative/concept).

**Two-figure rule**: include a second figure (max two total) when:
- The first is conceptual/teaser AND there's a separate strong qualitative-results figure (good story arc)
- The first is qualitative results AND there's a strong "mechanism" figure that pairs with the SVG (good algorithmic depth)
- Drifting is a textbook case: Fig 1 (training dynamics, the "what") + Fig 2 (kernel attraction/repulsion, the "how")

#### How to extract

Use the `extract_figure.py` utility, which auto-detects the figure+caption block via content-density scanning:

```bash
uv run python scripts/extract_figure.py <pdf-path> <output.png> [options]
# or, if installed: paper-extract-figure <pdf-path> <output.png> [options]
```

**Per-paper-layout flags** (try defaults first; fall back to these if the result looks wrong):
- **Single-column paper, figure on top of page 1**: pass `--first` to pick the first big block (skips abstract below).
  - If the authors line merges into the figure, pass `--skip-top 470` (or higher) to skip past it.
- **Two-column paper, figure in right column**: pass `--x-band <x_left> <x_right>` to scan only that column.
- **Default behavior**: picks the largest content block by density — works for most papers without explicit flags.
- **Figure on a later page**: pass `--page N` to render page N. Cross-platform via PyMuPDF.

The script automatically merges short blocks (captions) both above and below the chosen figure block within 80 px, so captions are never truncated regardless of caption position.

**Mandatory verification step**: after running the script, **read the saved `figure.png` with the Read tool** to visually verify:
1. The figure (panels, plots, diagrams) is fully visible — top and bottom not cut off.
2. The caption is fully visible — last sentence ends with a period, no mid-word hyphen continuation.

If either is truncated, re-run with adjusted `--skip-top`, `--y-band <y0> <y1>`, or `--blank-run` (smaller = more granular splits, larger = absorbs internal gaps in multi-panel figures).

If extraction fails entirely (PDF page renders blank, all blocks rejected, or the saved PNG fails the visual verification on every flag combination you tried), fall back to the **ar5iv HTML** before giving up:

1. WebFetch `https://ar5iv.org/html/<ID>` (already in the cache from Step 2 — re-read `body.txt`'s source if you saved the raw HTML, otherwise refetch).
2. Find the first `<figure>` whose `<img>` `src` looks like a real figure (not a logo / equation / inline icon). The `src` is usually a relative path under `/html/<ID>/assets/...`.
3. Resolve it to an absolute URL and download via `curl -sL <url> -o $PAPERS_DIR/<safe-kebab-title>/figure.png`.
4. Read the saved `figure.png` to visually verify the same way as the pdftotext path.
5. If ar5iv has no usable figure either, skip the figure section silently — the SVG remains the primary diagram.

Only fall back when the pdftotext path has genuinely failed; don't substitute ar5iv just because the first crop looked imperfect (the script's flags fix that case).

#### Naming

- Single figure: save as `figure.png` in the paper folder
- Two figures: save as `figure-1.png` and `figure-2.png` (and update the HTML's "FROM THE PAPER" section to render both, each with its own type label)

### Scratchpad output (kept in memory, not written to disk)

By the end of Step 3 you must have:
- 5-10 section pointers ready for attribution (e.g., `"§3.1 defines V"`, `"Eq. 4"`, `"Table 4 ablation"`, `"Fig. 5"`)
- 2-4 nuances most summaries miss (acknowledged limitation, surprising ablation, code/paper discrepancy, hyperparameter sensitivity)
- The path to `figure.png` if extracted

---

## Step 4 — Discover additional related papers

Run multi-angle searches in parallel to find papers not in the cited list. **Never filter by year** — the canonical paper for a topic might be from 2014 (GAN), 2017 (Transformer), or last week. Year-bias is the #1 cause of missed classics.

**Search 1 — Direct topic** via Semantic Scholar:
`https://api.semanticscholar.org/graph/v1/paper/search?query=<paper title>&limit=20&fields=title,authors,year,venue,abstract,externalIds,citationCount`

**Search 2 — Cross-domain synonyms** via WebSearch:
Brainstorm 2-3 alternative framings of the core contribution (e.g. "patch-text alignment" ↔ "dense vision-language pretraining" ↔ "pixel-level contrastive learning"). Search those framings.

**Search 3 — Venue-aware** via WebSearch:
`<core topic> <relevant venue> site:openreview.net OR site:arxiv.org` — include the current year and the previous 1-2 years to surface recent work, but **don't restrict the query to those years**.

**Search 4 (if needed) — Mechanism-level** via WebSearch:
Search for the technical building blocks the method requires (e.g. "RoPE positional embedding multi-resolution", "stop-gradient distillation").

De-duplicate against Step 2's reference list. Combine into a single **papers list** with: title, authors, year, venue, arXiv ID, citation count, one-line relevance note, and a tier:

- **Tier 1** — directly comparable (compared in tables, or proposes the same problem)
- **Tier 2** — related methods, datasets, or building blocks
- **Tier 3** — broader context / classical foundations

---

## Step 5 — Generate the HTML

### Design tokens

```
Page bg (light):     #f3ede3   warm sandy beige
Card bg (light):     #faf6ef
Page bg (dark):      #1a1612   deep warm brown
Card bg (dark):      #25201a
Card border:         1px solid var(--border)  →  #e4d9c8 light / #3a3128 dark
Hover border:        #b07d3c (both modes)
Accent blue:         #4a7296
Accent mauve:        #7a5c96
Accent sage:         #3d7858
Accent amber:        #a06c24
Text primary:        #1c150e light / #f0e8d8 dark
Text muted:          #7a6a58 light / #b0a090 dark
Text subtle:         #b0a090 light / #7a6a58 dark
Font:                -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif
Layout:              max-width 960px, centered, padding 32px 24px
Cards:               border-radius 12px, padding 20px 24px, margin-bottom 16px, box-shadow: 0 1px 4px rgba(80,60,30,0.07)
Section hdrs:        11px, font-weight 700, letter-spacing 0.1em, uppercase, color #8a7764
```

Use CSS custom properties on `:root` so dark mode is a single `prefers-color-scheme` override.

### Required `<head>` includes

- `<meta charset="UTF-8">`, `<meta name="viewport">`
- KaTeX CDN for math (auto-render):
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]})"></script>
  ```
- `@media print { body { background: white; } .no-print { display: none; } }` for printable archives.
- Dark mode block via `@media (prefers-color-scheme: dark)`.

### Sections (in order)

**1. HEADER**
- Card with `linear-gradient(135deg, #f0e6d4, #e8dcc8)` (light) / `linear-gradient(135deg, #2a241c, #20180e)` (dark)
- Title large bold, `clamp(18px, 3vw, 27px)`
- Authors (first 4, then "et al.") + affiliation if obvious + venue / submission date
- **Pill badges in row** (in this order; skip any that don't apply):
  1. Date (e.g. "Feb 2026") + version if not v1 (e.g. "v2 · Sep 2025")
  2. Categories ("cs.CV · cs.LG")
  3. Venue ("NeurIPS 2025", "CVPR 2026", "ICLR 2026") if accepted
  4. arXiv link (`badge.blue` class, "arXiv 2502.08321")
  5. GitHub repo (`badge.sage` class, with `&#x2328;&#xfe0e;` keyboard glyph + `<owner>/<repo>`)
  6. Project page ("project page")
  7. Demo links — Colab, HuggingFace Spaces ("Colab demo", "HF demo"). Add when the project page or README links to one.
  8. Checkpoints ("checkpoints" → HuggingFace collection / Drive)
  9. OpenReview, Author's homepage PDF — when arXiv body is paywalled or noticeably different from the conference version
  10. Reading time pill (e.g. `~22 min read`) with `title` tooltip "Estimated from body word count". Compute as `ceil(body_words / 220)` minutes, where `body_words` is the whitespace-split word count of the paper body (`body.txt` from the cache, post pdftotext/ar5iv, with the references section stripped). 220 wpm is the rough target for technical reading; do not retune per paper.
- **Copy BibTeX** button — small `<button class="no-print">` that, on click, copies the paper's BibTeX entry to clipboard via `navigator.clipboard.writeText(...)`. Use the **official BibTeX from the project page** if found; otherwise auto-generate `@misc` from the arXiv ID. Avoid escaped Unicode in the JS string — write `é` not `\\\'e`.

**2. TL;DR**
- Left-border card: `border-left: 4px solid; border-image: linear-gradient(to bottom, #4a7296, #7a5c96) 1`
- 2-3 punchy sentences, 18-20px, line-height 1.65
- Math allowed via `$...$` (KaTeX inline). Use math when the paper's contribution is fundamentally an equation (e.g. a new loss).

**3. PROBLEM ↔ METHOD** (2-col grid, gap 16px)
- Left — "THE PROBLEM": 3-5 bullets on the gap/limitation
- Right — "THE METHOD" (or "THE APPROACH"): 3-5 bullets on the solution
- **Each bullet that makes a specific claim must include a section pointer in muted text**: e.g. `iBOT++: extends self-distillation to all tokens (§3.1, Eq. 4)`
- Bullet length budget: ≤ 180 chars including pointer
- **Bullet CSS — DO NOT use `display: flex` on `<li>`**. Inline children (`<em>`, `<strong>`, KaTeX math, anchor span) become separate flex items and the text columnizes. Use absolute positioning instead:
  ```css
  .bullet-list { padding-left: 14px; list-style: none; }
  .bullet-list li {
    position: relative; margin-bottom: 9px;
    font-size: 14px; line-height: 1.55; color: var(--text);
  }
  .bullet-list li::before {
    content: ''; position: absolute; left: -14px; top: 10px;
    width: 5px; height: 5px; background: var(--accent-blue);
    border-radius: 1px;
  }
  ```
- Bullet content can freely mix plain text, `<strong>`, `<em>`, inline KaTeX (`$...$`), and `<span class="anchor">§x.y</span>` — all flow as inline text under this CSS.

**4. CORE DIAGRAM** (full-width card) ← most important
- Section header: "HOW IT WORKS" + 1-line subtitle naming the figure (e.g. "Architecture overview, mirrors Fig. 2")
- Inline SVG `width="100%"`, `viewBox="0 0 900 H"` where H is whatever fits
- SVG background `#f0e8d6` with subtle grid pattern `#c8b89a` at 0.35 opacity, 40px spacing
- Component rects: deep gradient fills, `rx="10"` for blocks, `rx="20"` for pill I/O nodes
- Component names MUST use the paper's actual terminology (V, f_θ, iBOT++, etc.)
- 2-3 sentence caption below the SVG

**Text overflow validation (mandatory)**: before writing the SVG, check every `<text>` element against its parent rect using `char_count × font_size × 0.55 ≤ rect_width`. If any label fails, shorten the label or widen the rect, then re-check. After writing the HTML, run:

```bash
uv run python scripts/validate_svg.py <output.html>
# or: paper-validate-svg <output.html>
```

If it reports any overflow, fix the offending labels and re-save before opening the page.

SVG branch colour guide:
- Primary branch: deep steel blue `#1a4870` → `#4a90c8`
- Secondary branch: deep mauve `#4a2870` → `#8060c8`
- Language/text branch: deep teal `#0d4848` → `#3a9090`
- Input/output nodes: deep sage `#1a4a2e` → `#4a9060`
- Loss annotations (warm): amber `#7a4800` text, `#3a1800` bg
- Loss annotations (cool): sage `#1a5030` text, `#0a2818` bg

**4b. KEY EQUATIONS & QUOTES** (full-width card; mandatory if the paper has a defining equation or any non-trivial loss/objective)
- Section header: "KEY EQUATIONS & QUOTES"
- Render the 1-3 equations that define the paper as **block-level KaTeX** (`$$...$$`), each with its own label pointing to the source (`§3.2, Eq. 4` style).
- Pair each equation (or stand-alone) with **direct verbatim quotes from the paper body** — at least one per equation, plus 2-4 stand-alone quotes for non-equation core claims.
- Quotes must be the paper's actual prose, italicized, with a small uppercase anchor showing the exact source (e.g. `§3.2 — Why masking-invariance works`).
- Suggested CSS:
  ```css
  .eq-row { margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px dashed var(--border); }
  .eq-row:last-child { border-bottom: none; padding-bottom: 0; margin-bottom: 0; }
  .eq-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent-blue);
    margin-bottom: 6px;
  }
  .eq-quote, .paper-quote blockquote {
    font-size: 13px; font-style: italic; color: var(--muted);
    line-height: 1.55; margin: 8px 0 0;
    padding: 6px 12px; border-left: 2px solid var(--border);
  }
  .paper-quote { margin: 12px 0; }
  .paper-quote .quote-anchor {
    display: block; font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 4px;
  }
  ```
- HTML pattern for an equation row:
  ```html
  <div class="eq-row">
    <div class="eq-label">Anomaly score (§3.3)</div>
    $$\text{score}(p) = -\log q_{\theta^{\text{dens}}}(\mathbf{y}[p] \mid \mathbf{c}[p])$$
    <p class="eq-quote">"<em>...the conditional density model can be viewed as a predictive model... anomaly scores are position-wise prediction errors.</em>" — §3.3</p>
  </div>
  ```
- Stand-alone quote pattern:
  ```html
  <div class="paper-quote">
    <div class="quote-anchor">§3.2 — Why masking-invariance works</div>
    <blockquote>"<em>...verbatim quote from the paper body...</em>"</blockquote>
  </div>
  ```
- Purpose: this is the section where the paper speaks for itself. Don't paraphrase if the paper said it well.

**4c. FROM THE PAPER** (only if at least one figure was extracted; up to 2 figures)
- **Section label format is mandatory**: `FROM THE PAPER · Fig. <N> (<type>)` — where `<type>` is one of `qualitative results`, `architecture`, `concept`, `mechanism`, `comparison`, `motivation`, `teaser`. Pick from the caption's intent, not its position. For two figures, list both: `FROM THE PAPER · Fig. 1 (training dynamics) · Fig. 2 (kernel mechanism)`.
- Each `<img>` MUST have **descriptive alt text** that conveys the figure's content for screen readers — not just "paper figure". Example: `alt="Three rows of CT slices: input images, ground truth pathology masks, Screener anomaly maps. Annotation highlights pneumothorax detected by Screener but missing from the ground-truth mask."` Never use placeholder alt.
- Below each image: a short italic caption that says where it's from and **what the figure adds beyond the SVG diagram**. Example: "Reproduced from arXiv:XXXX.XXXXX, Fig. 2. Visualizes the kernel-attraction/repulsion mechanism that the SVG above only labels symbolically."
- If using two figures, separate them with a `<hr>` styled to match the card's dashed border, OR stack them in a single card with two image+caption blocks.
- Purpose: complement the synthesized SVG with the paper's own visuals. Skip silently if extraction failed.

**5. KEY RESULTS** (full-width card)
- 4-6 metric cards, flex-wrap, min-width 140px, flex 1
- Large value: 32px bold, color depends on type (sage `#2e5f3e` improvement, blue `#2a4f70` neutral, amber `#7a4c10` cost/efficiency)
- Label: 11px uppercase
- **Context line is mandatory and must attribute the result**: dataset + setup + table/figure pointer.
  Example: `ImageNet-256 · L/2 model · Table 5` (not just `ImageNet`).
- Card background `#f0e8d8`, hover border `#b07d3c`

**6. NUANCES** (full-width card; only render if you found ≥2 nuances)
- Section header: "WHAT MOST SUMMARIES MISS"
- 2-4 bullets — each captures a non-obvious finding, an honest limitation acknowledged in the paper, a surprising ablation, or a code/paper discrepancy
- Each bullet must include a section pointer (e.g. `§6.2 acknowledges scaling beyond g/14 was not explored`, `code uses lr=1e-4 despite paper text saying 5e-4`)
- This is the section that distinguishes a deep reading from a HuggingFace blurb. Don't skip it for shallow papers — for shallow papers, omit the section entirely rather than padding it.

**7. CONTRIBUTIONS + RELATED WORK** (2-col grid)
- Left — "KEY CONTRIBUTIONS": 3-5 novel contributions as bullets (with section pointers)
- Right — "RELATED WORK": 3-5 Tier 1 papers — name bold 13px, one-line note explaining the *specific* relationship (not "related to X"), small arXiv link in `#4a7296`

**8. RELATED PAPERS — TIERED CHIP CLOUD** (full-width card)
- Section header: "RELATED PAPERS"
- Three sub-rows, in order: Tier 1, Tier 2, Tier 3 — each with a small label `"DIRECTLY COMPARABLE"` / `"RELATED METHODS"` / `"BACKGROUND"` in the muted section-header style
- Tier 1 chips: stronger border `#b07d3c`, slightly larger `font-size: 13px`, padding `5px 14px`
- Tier 2 chips: standard `#e0d0b8` border, `font-size: 12px`
- Tier 3 chips: subdued (`color: #a09080`, `border-color: #ece0cc`)
- Every chip: `<a href="https://arxiv.org/abs/<id>" target="_blank" title="<one-line factual hook from the paper's abstract>">Title — Authors (Year)</a>`
- **Tooltip rules**: the `title` must be a single factual sentence drawn from the abstract or a comparable-fact relationship to the main paper. **Never** describe content the chip itself doesn't contain — e.g. don't promise an architecture diagram if the linked paper doesn't have one. **Never** copy boilerplate ("a paper about X") — be concrete ("Replaces patch tokens with learned slots; +2.3 mIoU on ADE20K"). Aim for ≤ 120 chars.
- Aim for 18-35 chips total across all tiers

**9. FOOTER**
- Citation line, 12px muted (use the official BibTeX from the project page if available; otherwise a self-generated `@misc{<authorYear>, ...}`).
- One Resources line: `Project page · GitHub · Demo · Video` (only those that exist) as small `#4a7296` links.
- One generation line: `Generated YYYY-MM-DD · v<N>` only — **do not include absolute paths** (no `/Users/<name>/...`) since the page is portable. `<N>` is the regen count for *this paper's* HTML: 1 on the first run, increment by 1 every time the user picks "regenerate from scratch" or "update related-work only" in Step 1's skip prompt. Determine the previous value by parsing the existing `<safe-kebab-title>.html` (look for the `Generated …· v` line) before overwriting; if no prior file or value can't be parsed, write `v1`.

### CSS extras

```css
@media (max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
@media print {
  body { background: white !important; padding: 16px; }
  .card { box-shadow: none !important; break-inside: avoid; }
  .no-print, .copy-bibtex { display: none !important; }
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1612; --card: #25201a; --border: #3a3128;
    --text: #f0e8d8; --muted: #b0a090; --subtle: #7a6a58;
  }
  body { background: var(--bg); color: var(--text); }
  .card { background: var(--card); border-color: var(--border); }
  /* The SVG card uses its own warm background, so it stays cream in dark mode for readability — desired. */
}
```

---

## Step 6 — Write knowledge base files

In `$PAPERS_DIR/<safe-kebab-title>/`:

**`memory-bank.md`** — write the paper itself as the first entry (`status: analyzed`), then all related papers (cited + discovered) using the paper-finder format:
```
### [short-id] Title
- **Authors**: ...
- **Venue**: ..., Year
- **URL**: https://arxiv.org/abs/<id>
- **Citations**: N
- **Status**: discovered
- **Topics**: topic1, topic2
- **Tier**: 1 | 2 | 3
- **Abstract**: 1-2 sentence summary
- **Notes**: relevance to this paper
```

**`mind-graph.md`** — identify 3-6 key topics from the paper. For each topic, list the most relevant papers from the papers list with one-line notes. Use the paper-finder mind-graph format.

**`references.bib`** — BibTeX for all papers with arXiv IDs. `@misc` for arXiv preprints, `@inproceedings` for confirmed conference papers. Citation key = short-id. This is the canonical PDF source — `paper-finder` reads from here for downloads.

---

## Step 7 — Update the global index

Append (or update if the entry exists) `$PAPERS_DIR/index.html`:
- Each row: paper title, authors, date, link to its folder, link to its `.html`
- Sort newest first
- Use the same design tokens as the explainers
- Keep this file simple — it's a directory, not another visual artifact

---

## Step 8 — Save and open

1. Save HTML to `$PAPERS_DIR/<safe-kebab-title>/<safe-kebab-title>.html` using the Write tool
2. Run `open "$PAPERS_DIR/<safe-kebab-title>/<safe-kebab-title>.html"` via Bash (macOS) or `xdg-open` (Linux)
3. Tell the user: output path, paper title, total related papers (cited + discovered, with tier counts), the knowledge base location, and one specific nuance you found that was not in the abstract
4. Offer: "Want me to dive deeper on any related paper, generate a summary in `summaries/`, or compare specific papers?"
