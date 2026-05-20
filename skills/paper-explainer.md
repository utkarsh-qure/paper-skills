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
- `scratchpad.md` — structured deep-read of the paper (metadata, section anchors, named components, loss, equations, benchmarks, ablations, nuances, lede/prereqs material). Every explainer run produces one. This is the **contract** consumed by `paper-companion` to skip re-fetching and re-searching.
- `figure.png` — extracted teaser/architecture figure from the PDF (when one figure is enough)
- `figure-1.png` + `figure-2.png` — when two complementary figures are extracted
- `companion.html` — optional long-form companion artifact (only present if `/paper-companion` was run on this paper)
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

The **regenerate** and **update related-work only** branches also rewrite `scratchpad.md` (so the orient layer stays in sync with the HTML). The **open existing** and **skip** branches leave both files untouched.

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

### Persist deep-read state — write `scratchpad.md`

By the end of Step 3, write `$PAPERS_DIR/<safe-kebab-title>/scratchpad.md`. This file is the **contract** between `paper-explainer` and `paper-companion`: every explainer run produces one, and the companion reads from it to skip its own web-search + paper-extraction. Step 5 (HTML generation) also reads from this file for the fields below — single source of truth, no drift between scratchpad and HTML.

Structure (all sections required, in this order):

```markdown
# <Paper Title>

## Metadata
- **Title**: ...
- **Authors**: ...
- **arXiv ID**: XXXX.XXXXX
- **Categories**: cs.CV, cs.LG
- **Date**: YYYY-MM
- **Venue**: NeurIPS 2025 / preprint / ...
- **GitHub**: <url or "—">
- **Project page**: <url or "—">

## Section anchors
5–10 bullets in `§X.Y — short description` form (e.g., `§3.2 — defines V`,
`Eq. 4 — anomaly score`, `Table 4 — main ablation`).

## Named components & terminology
The paper's actual notation for model components — one line each
(`encoder f_θ`, `predictor g_φ`, `target s`, `context c`). Companion §2
SVG labels lift from here verbatim.

## Loss function (verbatim)
The canonical loss in LaTeX form, derived from code when available. Use
`\text{sg}[...]` for stop-gradient. Avoid double subscripts on the same base
(`\hat s_y^{(i)}_j` breaks KaTeX — use `\hat s^{(i)}_j` or `\hat s_{y,j}^{(i)}`).
Companion §3 renders this directly.

## Key equations (additional)
1–3 more equations beyond the loss, each with a source label
(`Eq. 4 — anomaly score`).

## Benchmarks (headline)
3–6 main results with dataset + setup + table attribution.
Example: `ImageNet linear probe: 79.3 (ViT-H/14, Table 2)`.

## Ablations (with table attribution)
2–4 ablation deltas in the form `(component removed → metric drop, Table N)`.
Companion §6 needs deltas, not just headline numbers.

## Nuances
2–4 items: acknowledged limitations, surprising ablations,
code/paper discrepancies, hyperparameter sensitivities. Section pointers
mandatory (`§6.2 acknowledges scaling beyond g/14 was not explored`).

## Lede + prereqs material
1–2 paragraphs framing what this paper changes relative to predecessors
(feeds the companion's §1 + lede paragraph). Followed by 2–4 concept
prerequisites with one-sentence framings (feeds the companion's prereqs box).
```

Additional in-memory state (figure paths, related-papers tiering, BibTeX, design-token decisions) is **presentation-layer** and stays in memory — don't put it in scratchpad. Scratchpad is the structured intermediate; HTML is the presentation.

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

The explainer one-pager uses the same distill.pub-inspired palette as `paper-companion`. Side-by-side, the one-pager and companion for the same paper should look like two outputs of one project — typography stack and color tokens overlap verbatim.

```css
:root {
  --serif: 'Crimson Pro', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
  --sans:  'Karla', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
  --mono:  'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;

  --ink:        #1a1a1a;   /* body text */
  --ink-soft:   #444;
  --ink-mute:   #7a7a7a;   /* section labels, anchors, captions */
  --paper:      #fdfdfb;   /* page bg + card bg */
  --rule:       #e8e6e1;   /* card border, hairlines */
  --rule-soft:  #f5f3ee;   /* shaded blocks, header gradient end */
  --accent:     #8b3a1f;   /* primary accent — borders, links, target features */
  --teal:       #1d6a6a;   /* secondary — context features, "known" side */
  --purple:     #534ab7;   /* tertiary — actions, query, eq-row labels */
}
```

- Body text in `var(--serif)`. All headers, figures, callouts, captions, badges, code, and section labels in `var(--sans)`. Math via KaTeX.
- Layout: `max-width: 960px`, centered, `padding: 32px 24px`.
- Cards: `background: var(--paper); border: 1px solid var(--rule); border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(26,26,26,0.04);`.
- Section labels: `font-family: var(--sans); font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-mute);`.
- Light-only — distill.pub's reference theme is light-mode. No `prefers-color-scheme: dark` block here. (If dark mode is needed later, add it as a separate override; not in scope.)
- Avoid using more than 3 colors per figure. Avoid blue + green together (color-blindness pitfall).

### Required `<head>` includes

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><PaperName> — Paper explainer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Karla:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload='renderMathInElement(document.body, {delimiters: [{left: "$$", right: "$$", display: true},{left: "$", right: "$", display: false}], throwOnError: false});'></script>
```

This block is **identical** to `paper-companion`'s `<head>` includes (KaTeX version, font preconnect, auto-render config). Keep them in sync.

Also include a print stylesheet via `@media print { body { background: white; } .no-print { display: none; } }` for printable archives.

### Sections (in order)

**1. HEADER**
- Wide card with subtle gradient `linear-gradient(180deg, var(--paper), var(--rule-soft))` and a 3px left rule in `var(--accent)`.
- Title in `var(--sans)`, large semibold, `clamp(20px, 3.2vw, 30px)`. Color `var(--ink)`.
- Authors (first 4, then "et al.") + affiliation if obvious + venue / submission date — all `var(--sans)`, `var(--ink-soft)`.
- **Pill badges in row** (in this order; skip any that don't apply):
  1. Date (e.g. "Feb 2026") + version if not v1 (e.g. "v2 · Sep 2025")
  2. Categories ("cs.CV · cs.LG")
  3. Venue ("NeurIPS 2025", "CVPR 2026", "ICLR 2026") if accepted
  4. arXiv link (`badge.accent` class — accent border + accent text, "arXiv 2502.08321")
  5. GitHub repo (`badge.teal` class, with `&#x2328;&#xfe0e;` keyboard glyph + `<owner>/<repo>`)
  6. Project page ("project page")
  7. Demo links — Colab, HuggingFace Spaces ("Colab demo", "HF demo"). Add when the project page or README links to one.
  8. Checkpoints ("checkpoints" → HuggingFace collection / Drive)
  9. OpenReview, Author's homepage PDF — when arXiv body is paywalled or noticeably different from the conference version
  10. Reading time pill (e.g. `~22 min read`) with `title` tooltip "Estimated from body word count". Compute as `ceil(body_words / 220)` minutes, where `body_words` is the whitespace-split word count of the paper body (`body.txt` from the cache, post pdftotext/ar5iv, with the references section stripped). 220 wpm is the rough target for technical reading; do not retune per paper.
- Badge base style: `.badge { display: inline-flex; align-items: center; padding: 3px 10px; border: 1px solid var(--rule); border-radius: 20px; font-family: var(--sans); font-size: 12px; color: var(--ink-mute); text-decoration: none; }`. `.badge:hover { border-color: var(--accent); color: var(--ink); }`. `.badge.accent` overrides border + text to `var(--accent)`. `.badge.teal` overrides to `var(--teal)`.
- **Copy BibTeX** button — small `<button class="no-print copy-btn">` that, on click, copies the paper's BibTeX entry to clipboard via `navigator.clipboard.writeText(...)`. Use the **official BibTeX from the project page** if found; otherwise auto-generate `@misc` from the arXiv ID. Avoid escaped Unicode in the JS string — write `é` not `\\\'e`. Style matches the badge pill (border `var(--rule)`, hover `var(--accent)`); flash `border-color: var(--teal); color: var(--teal);` on success.

**2. TL;DR**
- Card with a 4px solid left border in `var(--accent)`.
- 2-3 punchy sentences, 18-20px, line-height 1.65, `var(--serif)`, `color: var(--ink)`.
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
    font-family: var(--serif); font-size: 15px; line-height: 1.55; color: var(--ink);
  }
  .bullet-list li::before {
    content: ''; position: absolute; left: -14px; top: 10px;
    width: 5px; height: 5px; background: var(--accent);
    border-radius: 1px;
  }
  .anchor { font-family: var(--sans); font-size: 12px; color: var(--ink-mute); margin-left: 4px; white-space: nowrap; }
  ```
- Bullet content can freely mix plain text, `<strong>`, `<em>`, inline KaTeX (`$...$`), and `<span class="anchor">§x.y</span>` — all flow as inline text under this CSS.

**4. CORE DIAGRAM** (full-width card) ← most important
- Section header: "HOW IT WORKS" + 1-line subtitle naming the figure (e.g. "Architecture overview, mirrors Fig. 2")
- Inline SVG `width="100%"`, `viewBox="0 0 900 H"` where H is whatever fits
- SVG background `var(--rule-soft)` (creamy off-white) with optional subtle grid `var(--rule)` at 0.5 opacity, 40px spacing. Keep it quiet — the diagram is the focus, not the texture.
- Component rects: solid fills using the branch palette below, `rx="10"` for blocks, `rx="20"` for pill I/O nodes. Text inside rects is `var(--paper)` (light) for readability against the saturated fill.
- Component names MUST use the paper's actual terminology (V, f_θ, iBOT++, etc.) — lift them from `scratchpad.md`'s **Named components & terminology** section verbatim.
- 2-3 sentence caption below the SVG, `var(--sans)`, `var(--ink-soft)`.

**Text overflow validation (mandatory)**: before writing the SVG, check every `<text>` element against its parent rect using `char_count × font_size × 0.55 ≤ rect_width`. If any label fails, shorten the label or widen the rect, then re-check. After writing the HTML, run:

```bash
uv run python scripts/validate_svg.py <output.html>
# or: paper-validate-svg <output.html>
```

If it reports any overflow, fix the offending labels and re-save before opening the page.

SVG branch colour guide (matches `paper-companion`):
- Primary / context / "known" branch: `var(--teal)` `#1d6a6a` fill, `var(--paper)` text
- Secondary / target / "predicted" branch: `var(--accent)` `#8b3a1f` fill, `var(--paper)` text
- Action / query / intervention: `var(--purple)` `#534ab7` fill, `var(--paper)` text
- Input / output nodes: `var(--ink-soft)` `#444` fill, `var(--paper)` text (or `var(--rule-soft)` fill + `var(--ink)` text for "passive" nodes)
- Loss annotations: `var(--ink-soft)` text on `var(--rule-soft)` bg, sans 11px

Stick to at most 3 branch colors per diagram. Avoid mixing teal with green-adjacent hues elsewhere in the figure (color-blindness pitfall).

**4b. KEY EQUATIONS & QUOTES** (full-width card; mandatory if the paper has a defining equation or any non-trivial loss/objective)
- Section header: "KEY EQUATIONS & QUOTES"
- Render the 1-3 equations that define the paper as **block-level KaTeX** (`$$...$$`), each with its own label pointing to the source (`§3.2, Eq. 4` style).
- Pair each equation (or stand-alone) with **direct verbatim quotes from the paper body** — at least one per equation, plus 2-4 stand-alone quotes for non-equation core claims.
- Quotes must be the paper's actual prose, italicized, with a small uppercase anchor showing the exact source (e.g. `§3.2 — Why masking-invariance works`).
- Suggested CSS:
  ```css
  .eq-row { margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px dashed var(--rule); }
  .eq-row:last-child { border-bottom: none; padding-bottom: 0; margin-bottom: 0; }
  .eq-label {
    font-family: var(--sans); font-size: 11px; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--purple); margin-bottom: 6px;
  }
  .eq-quote, .paper-quote blockquote {
    font-family: var(--serif); font-size: 14px; font-style: italic;
    color: var(--ink-soft); line-height: 1.55; margin: 8px 0 0;
    padding: 6px 12px; border-left: 2px solid var(--rule);
  }
  .paper-quote { margin: 12px 0; }
  .paper-quote .quote-anchor {
    display: block; font-family: var(--sans); font-size: 10px;
    font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-mute); margin-bottom: 4px;
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
- Large value: 32px sans semibold, `font-variant-numeric: tabular-nums`. Color depends on type:
  - `var(--teal)` for improvement / strong positive
  - `var(--ink)` for neutral
  - `var(--accent)` for cost / efficiency
- Label: 11px sans uppercase, `var(--ink-mute)`
- **Context line is mandatory and must attribute the result**: dataset + setup + table/figure pointer.
  Example: `ImageNet-256 · L/2 model · Table 5` (not just `ImageNet`). Sourced from `scratchpad.md`'s **Benchmarks (headline)** section.
- Card background `var(--rule-soft)`, border `1px solid var(--rule)`, hover border `var(--accent)`.

**6. NUANCES** (full-width card; only render if you found ≥2 nuances)
- Section header: "WHAT MOST SUMMARIES MISS"
- 2-4 bullets sourced from `scratchpad.md`'s **Nuances** section — each captures a non-obvious finding, an honest limitation acknowledged in the paper, a surprising ablation, or a code/paper discrepancy
- Each bullet must include a section pointer (e.g. `§6.2 acknowledges scaling beyond g/14 was not explored`, `code uses lr=1e-4 despite paper text saying 5e-4`)
- Styling: each bullet as a small block with `border-left: 3px solid var(--accent); background: var(--rule-soft); padding: 10px 12px;` and `font-family: var(--serif);` for readability. Section pointers in `var(--sans) var(--ink-mute)`.
- This is the section that distinguishes a deep reading from a HuggingFace blurb. Don't skip it for shallow papers — for shallow papers, omit the section entirely rather than padding it.

**7. CONTRIBUTIONS + RELATED WORK** (2-col grid)
- Left — "KEY CONTRIBUTIONS": 3-5 novel contributions as bullets (with section pointers)
- Right — "RELATED WORK": 3-5 Tier 1 papers — name semibold 13px sans, one-line note explaining the *specific* relationship (not "related to X"), small arXiv link in `var(--accent)`

**8. RELATED PAPERS — TIERED CHIP CLOUD** (full-width card)
- Section header: "RELATED PAPERS"
- Three sub-rows, in order: Tier 1, Tier 2, Tier 3 — each with a small label `"DIRECTLY COMPARABLE"` / `"RELATED METHODS"` / `"BACKGROUND"` in the muted section-header style
- All chips share base style: `font-family: var(--sans); padding: 4px 12px; border: 1px solid var(--rule); border-radius: 18px; text-decoration: none; color: var(--ink-soft);`
- Tier 1 chips: stronger `border-color: var(--accent); color: var(--accent);` slightly larger `font-size: 13px; padding: 5px 14px;`
- Tier 2 chips: `border-color: var(--rule)` default; `font-size: 12px`; `color: var(--ink-soft)`
- Tier 3 chips: subdued — `color: var(--ink-mute); border-color: var(--rule);` `font-size: 12px`
- Every chip: `<a href="https://arxiv.org/abs/<id>" target="_blank" title="<one-line factual hook from the paper's abstract>">Title — Authors (Year)</a>`
- **Tooltip rules**: the `title` must be a single factual sentence drawn from the abstract or a comparable-fact relationship to the main paper. **Never** describe content the chip itself doesn't contain — e.g. don't promise an architecture diagram if the linked paper doesn't have one. **Never** copy boilerplate ("a paper about X") — be concrete ("Replaces patch tokens with learned slots; +2.3 mIoU on ADE20K"). Aim for ≤ 120 chars.
- Aim for 18-35 chips total across all tiers

**9. FOOTER**
- Citation line, 12px sans `var(--ink-mute)` (use the official BibTeX from the project page if available; otherwise a self-generated `@misc{<authorYear>, ...}`).
- One Resources line: `Project page · GitHub · Demo · Video` (only those that exist) as small links in `var(--accent)`.
- One generation line: `Generated YYYY-MM-DD · v<N>` only — **do not include absolute paths** (no `/Users/<name>/...`) since the page is portable. `<N>` is the regen count for *this paper's* HTML: 1 on the first run, increment by 1 every time the user picks "regenerate from scratch" or "update related-work only" in Step 1's skip prompt. Determine the previous value by parsing the existing `<safe-kebab-title>.html` (look for the `Generated …· v` line) before overwriting; if no prior file or value can't be parsed, write `v1`.

### CSS extras

```css
@media (max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
@media print {
  body { background: white !important; padding: 16px; }
  .card { box-shadow: none !important; break-inside: avoid; }
  .no-print, .copy-bibtex { display: none !important; }
}
```

No dark-mode override — the distill.pub palette is light-only by design, matching `paper-companion`. Add a separate `@media (prefers-color-scheme: dark)` block later if needed; out of scope here.

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

Regenerate `$PAPERS_DIR/index.html` by running the shared script:

```bash
uv run python scripts/regen_index.py
```

The script walks `$PAPERS_DIR/*/` (one level deep), reads each folder's `<slug>.html` for title/authors/date, checks for an adjacent `companion.html`, and emits a fresh `index.html` with:
- One row per paper, recency-sorted
- A `one-pager` badge linking to `<slug>.html` (always present when the row exists)
- A `deep companion` badge linking to `companion.html` when present
- A depth-filter pill toggle at the top (`[All papers (N)] [With companion (M)]`), state persisted via `localStorage`
- The same distill.pub design tokens as the explainer / companion HTML

Both `paper-explainer` and `paper-companion` call this script at the end of their runs — keep them in sync via the script, not duplicate templates.

---

## Step 8 — Save and open

1. Save HTML to `$PAPERS_DIR/<safe-kebab-title>/<safe-kebab-title>.html` using the Write tool. (`scratchpad.md` was already written in Step 3.)
2. Run `open "$PAPERS_DIR/<safe-kebab-title>/<safe-kebab-title>.html"` via Bash (macOS) or `xdg-open` (Linux)
3. Tell the user: output path, paper title, total related papers (cited + discovered, with tier counts), the knowledge base location, and one specific nuance you found that was not in the abstract
4. Offer: "Want me to dive deeper on any related paper, generate a summary in `summaries/`, compare specific papers, or **build a deep companion artifact** with `/paper-companion <slug>`?"
