---
name: paper-companion
description: Builds a long-form, distill.pub-style HTML companion artifact for a research paper. Emphasizes narrative arc, visual intuition, interactive widgets where they help, and explicit cross-paper continuity when papers form a lineage. Use when the user wants to deeply understand a paper or set of papers, or asks for an "explainer," "companion," "study guide," or "tutorial." Accepts arXiv URLs, paper PDFs, paper titles, or direct prompts describing the paper. Produces a single self-contained HTML file per paper, ~700-1200 lines, with KaTeX math, custom SVG diagrams, ablation visualizations, callout boxes, and self-check questions.
---

# Paper Companion Skill

## What this skill is for

Producing a pedagogical HTML companion for a research paper — the kind of artifact someone would read to **internalize** a paper. The output is a long-form scrollable essay with custom SVG diagrams, interactive widgets where they earn their place, KaTeX equations integrated into prose, and explicit cross-paper continuity when papers form a lineage.

## When to trigger

Trigger when the user:
- Asks for an "explainer," "companion," "tutorial," "study guide," or "deep dive" for a paper
- Says "help me understand X paper" or "build me something to learn this from"
- Is working through a series of related papers (a research program lineage)
- Asks to compare two or more papers in a connected way
- Asks for visual or interactive explanations of paper content

## Inputs

Accept any of:
- arXiv URL (e.g., `https://arxiv.org/abs/2301.08243`)
- arXiv ID (e.g., `2301.08243`)
- Paper slug (e.g., `i-jepa` — only when an explainer folder already exists under `$PAPERS_DIR`)
- Paper PDF path
- Paper title
- Direct prompt describing the paper

After the model-check (see Process Step 0) and after locating prior work (Step 1), ask the user three authoring questions. These govern *how* the companion is written, not what gets extracted, so they're asked regardless of whether a scratchpad already exists:

1. **Delivery cadence** — *session-level.* "One paper at a time with review between each, or batched?" Ask once per session; remember the answer for every subsequent companion in the same conversation.
2. **Math depth** — *paper-level.* "Lean rigorous (core equations + intuitions, point to paper for derivations) or full rigor?" Ask for each paper — even mid-lineage. The user may want lean math for paper 5 even after picking full rigor for paper 4.
3. **Visual style** — *lineage-level.* "Clean academic / distill.pub style is the default. Anything to adjust?" Ask once at the start of a lineage; for subsequent papers in the same lineage, confirm with a one-keystroke "Same as last? (Enter=yes)" rather than re-asking.

Lineage position is **detected automatically** from `$PAPERS_DIR/.lineages/*.json` — do not ask the user "paper 3 of 6". See Process Step 1 (Lineage section) for the read/write logic and the user-prompt that bootstraps a brand-new lineage.

## Output

A single self-contained HTML file per paper at `$PAPER_EXPLAINER_OUTPUT_DIR/<paper-slug>/companion.html` (default `~/papers/<slug>/companion.html`). Resolve once at the start of every run:

```bash
PAPERS_DIR="${PAPER_EXPLAINER_OUTPUT_DIR:-$HOME/papers}"
```

No `NN_` numeric prefix — lineage ordering lives in the lineage manifest (see **Process → Lineage** below) and in the global index, not in filenames.

Size target: 700–1200 lines, ~40–60 KB.

Companion writes only `companion.html`. It does **not** write `memory-bank.md`, `mind-graph.md`, or `references.bib` — those are `paper-explainer`'s artifacts. Companion may *read* them when relevant (e.g., to find related papers within a lineage), but it never produces or modifies them.

## Required structure

Every artifact must include the following sections, in this order. Adapt names to the paper but keep the structural pattern.

### 1. Header (within a wide block)

- **Eyebrow** — small uppercase label, e.g. `JEPA companion · paper 3 of 6`
- **H1 title** — usually just the model/method name ("V-JEPA", not the full paper title)
- **Subtitle** — italic serif, restate the paper title or its core claim in one sentence
- **Byline** — authors (first ~5 then "et al."), venue/year, arXiv link

### 2. Lede + prereqs box

- **Lede paragraph** (`<p class="lede">`) — 4–7 sentences. The paper's central claim, what it builds on, what it adds. Must include `<strong>` highlights and end with a forward-looking statement.
- **Prereqs box** (`.prereqs`) — bulleted list of 2–4 prerequisites. Each is a concept the reader should already know going in, with a one-sentence framing.

### 3. §1 — What changes / context

- For lineage papers: open with a `<div class="recap">` summarizing the previous paper in 2–3 sentences. This is non-negotiable for any paper in a series.
- Establish what this paper changes relative to the field or to its predecessors. Don't recap fundamentals.
- One **pull quote** (`<p class="pull">`) here is often appropriate.

### 4. §2 — Architecture or core mechanism

- Custom SVG diagram showing the model architecture, training pipeline, or key mechanism. SVG must be hand-coded (no AI image gen).
- The SVG should:
  - Use the established color tokens (`--teal` for context/known, `--accent` for target/predicted, `--purple` for actions/inputs)
  - Label every box with paper's actual terminology
  - Include a thoughtful caption explaining what the figure adds
- Follow with H3 subsections describing each component (encoder, predictor, target, etc.)

### 5. §3 — Main objective / loss / mechanism

- Lay out the loss function with KaTeX. Use **`$$ ... $$`** for display equations.
- Define notation explicitly before using it. Avoid double subscripts/superscripts on the same base (KaTeX rejects `\hat s_y^{(i)}_j` — use `\hat s^{(i)}_j` or `\hat s_{y,j}^{(i)}` instead).
- For lineage papers, refer the reader back to a previous paper's objective if the loss is similar, rather than re-deriving.
- Insert at least one **callout** (`.callout` with `Design` or `Note` badge) here addressing a non-obvious design decision.

### 6. §4 — Key results / ablations

- Either an `.ablation` block with bar visualization (when ablations are the headline) or a `.benchmark-strip` of 3 cards (when results are the headline).
- Ablation numbers should be drawn directly from the paper's tables. Cite the table number if possible.
- The text around the visualization should explain what the comparison is testing and what conclusion to draw.

### 7. §5 — Additional concept (often)

- Many papers have a key conceptual contribution beyond architecture (e.g., V-JEPA's "feature prediction matters more for video", VL-JEPA's selective decoding, LeJEPA's Cramér-Wold trick). Give it its own section with visualization.

### 8. §N-1 — Results / what it achieves

- Concrete benchmark numbers in `.benchmark-strip`.
- One or two paragraphs explaining what to take away.

### 9. Final § — Limitations + bridge

- 2–4 acknowledged limitations from the paper.
- For lineage papers: explicit forward link to what the next paper addresses. The bridge is what makes the lineage coherent.

### 10. Self-check section

- 5 questions in an ordered list inside `<section class="self-check">`.
- Each question has a collapsible answer (`<details><summary>Answer</summary>...`).
- Questions should test conceptual understanding, not memorization. "Why does X work?" rather than "What is X?"

### 11. Footer

- `<footer class="paper-footer wide">` with prev/next paper links auto-populated from the lineage manifest (Process Step 1). Empty prev for paper 1; empty next for the last paper.
- One generation line below the prev/next nav: `Generated YYYY-MM-DD · v<N>` — sans, `var(--ink-mute)`, 11px. `<N>` is the regen count for *this paper's* companion HTML: 1 on the first run, increment by 1 every time the user picks "regenerate from scratch" or "regenerate with updated scratchpad" in Step 1's skip prompt. Parse the existing `companion.html` for the previous `Generated …· v<N>` line before overwriting; if no prior file or value can't be parsed, write `v1`.
- Do **not** include absolute paths (no `/Users/<name>/...`) — the page is portable.

## Required visual elements

### Reusable component classes

- `.recap` — gray box recapping previous paper, only for lineage papers
- `.callout` — design-decision Q&A box, used 1–3 times per artifact
- `.pull` — italic pull quote with accent left border, used 0–2 times
- `.ablation` — table with horizontal bars for ablation comparisons
- `.benchmark-strip` — 3-card horizontal layout for benchmark numbers
- `.split` — 2-column comparison cells (e.g. "before/after", "MAE vs JEPA")
- `.self-check` — collapsible questions section at the end
- `<aside class="aside">` — small margin notes (desktop only — degrades to inline on mobile)

### SVGs

- Architecture diagram in §2 — mandatory
- 2–4 additional figures throughout: ablation viz, mechanism illustration, results comparison, etc.
- Hand-coded SVGs only. Use `viewBox="0 0 W H"` with W around 900, scale fluidly.
- Color tokens consistent across the artifact.

### Interactive widgets (when they earn their place)

If the paper has a mechanism that benefits from being explored (masking patterns, sampling distributions, attention patterns), include a small interactive widget — typically a resample button and a stats display. Use vanilla JS, no libraries.

Examples already implemented:
- I-JEPA: 14×14 patch masking visualizer with multi-block sampler
- V-JEPA: 4-frame × 10×10 tube masking visualizer with short/long-range toggle
- V-JEPA 2.1: stylized dense-feature before/after comparison (static)

Don't add widgets when there's nothing to interact with.

## Style guide

### Typography stack

```
--serif: 'Crimson Pro', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
--sans: 'Karla', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
--mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
```

Body is serif. All headers, figures, callouts, asides, and code are sans. Math via KaTeX.

### Color tokens

```
--ink: #1a1a1a;     /* body text */
--ink-soft: #444;
--ink-mute: #7a7a7a;
--paper: #fdfdfb;
--rule: #e8e6e1;
--rule-soft: #f5f3ee; /* shaded blocks, recap card bg, aside bg on mobile */
--accent: #8b3a1f;   /* primary accent — borders, links, target features */
--teal: #1d6a6a;     /* secondary — context features, "known" side */
--purple: #534ab7;   /* tertiary — actions, query, "intervention" */
```

Tokens are identical to `paper-explainer`'s `<style>` block — side-by-side, one-pager + companion for the same paper share these verbatim.

Avoid using more than 3 colors per figure. Avoid blue + green together (color-blindness pitfall).

### Tone

- Pedagogical narrative. Like a senior researcher writing a tutorial for a smart junior.
- Use intuitions and analogies before formal definitions when possible.
- "Why" callouts for non-obvious design decisions.
- Avoid hype words: "groundbreaking," "revolutionary," "novel" without justification.
- Use the paper's own terminology consistently.

### Math

- Define notation before use.
- Use KaTeX `$$ ... $$` for display, `$...$` for inline.
- For predicted/target pairs, use $\hat s_j$ and $s_j$ (or $s_{y,j}$ to disambiguate). NEVER `\hat s_y^{(i)}_j` (double subscript breaks KaTeX).
- Indicate stop-gradient explicitly as `\text{sg}[ ... ]` when relevant.
- Keep equations under 80 characters per line.

### Length

- Each section: ~3–6 paragraphs + 0–2 figures.
- Total per paper: 700–1200 lines of HTML, 40–60 KB.
- Self-check: 5 questions.

## Required `<head>` includes

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><PaperName> — Paper companion</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Karla:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload='renderMathInElement(document.body, {delimiters: [{left: "$$", right: "$$", display: true},{left: "$", right: "$", display: false}], throwOnError: false});'></script>
```

## Layout (CSS grid)

The article uses a two-column grid: main column (max 720px) + margin column for `.aside` notes. Falls back to single column on mobile.

```css
article {
  max-width: 1100px;
  margin: 0 auto;
  padding: 4rem 2rem 6rem;
  display: grid;
  grid-template-columns: minmax(0, 720px) minmax(0, 1fr);
  gap: 2.5rem;
}
article > * { grid-column: 1; }
article > .wide { grid-column: 1 / -1; max-width: 100%; }
article > .aside { grid-column: 2; font-size: 14px; font-family: var(--sans); color: var(--ink-mute); }
@media (max-width: 900px) {
  article { grid-template-columns: 1fr; gap: 1.5rem; padding: 2rem 1.25rem 4rem; }
  article > .aside { padding: 0.75rem 1rem; background: var(--rule-soft); border-left: 2px solid var(--rule); }
}
```

## Process

### Step 0 — Confirm model (mandatory, before any other work)

Companion produces deep narrative artifacts that benefit substantially from a frontier model. Before touching the filesystem or the network:

- Detect the current model. If it's the strongest frontier option for the host agent — `claude-opus-4-7` with `/effort max` in Claude Code; GPT-5.5 max thinking fast in Cursor/Codex; equivalent best in other agents — proceed silently.
- Otherwise, print:
  > paper-companion produces deep narrative artifacts and benefits substantially from a frontier model. Currently on `<model>`. Switch to `<best available>` (recommended: `/model opus[1m]` + `/effort max` in Claude Code) or continue?
  Wait for `y` (continue on current model) / instructions to switch.
- Skip the warning entirely if the user explicitly pinned a model in their request (e.g. "use sonnet", "stay on opus").
- Skip the warning if the active model is already the strongest — that's the case when the user opted into Opus via `paper-explainer`'s Step 0 earlier in the session (their `/model` call switched the actual model, so detection just sees Opus).

This step is the only opinionated one in the pipeline — explainer asks gently, companion presumes the strongest.

### Step 1 — Resolve input & locate prior work

1. **Resolve to a slug.** arXiv URL / ID → fetch metadata → derive `<safe-kebab-title>`. PDF path → extract title from page 1 → kebab. Plain slug → use as-is. Paper title → kebab. Direct prompt → kebab from the most salient noun phrase.

2. **Skip if already done.** If `$PAPERS_DIR/<slug>/companion.html` already exists, ask the user one short question: *regenerate from scratch / regenerate with updated scratchpad / open existing / skip*. Do not silently overwrite. Increment the `v<N>` regen counter on either regenerate branch (see FOOTER section).

3. **Check the scratchpad.** Look for `$PAPERS_DIR/<slug>/scratchpad.md`:
   - **Exists** → read it. This populates *all* required content fields: metadata, section anchors, named components & terminology, loss function (verbatim), key equations, headline benchmarks, ablations with table attribution, nuances, and lede/prereqs material. **Skip all web-search and paper-extraction.** No `WebFetch`, no `WebSearch`, no `curl arxiv.org`.
   - **Does not exist** →
     - If `--force` was passed → proceed with an on-the-fly compressed version of `paper-explainer`'s Steps 2 + 3 (metadata + body + optionally code + project page → equivalent in-memory state). **Do not write `scratchpad.md`, do not write `code-snapshot.md`, and do not update the global knowledge base files** (`memory-bank.md` / `mind-graph.md` / `references.bib`) — those are all explainer's outputs. If you cloned a repo in `--force` mode, delete the clone before exiting Step 1. Print to the user:
       > Running with `--force`. This will not produce `scratchpad.md` or `code-snapshot.md`, and will not update the knowledge base. Run `/paper-explainer <arxiv-id>` afterwards if you want the orient layer.
     - Otherwise → print and **stop**:
       > No explainer found for `<slug>`. Run `/paper-explainer <arxiv-id>` first, or re-run with `--force` to extract from scratch.

4. **Check supplementary artifacts.**
   - If `$PAPERS_DIR/<slug>/one-pager.html` exists (or the legacy `<slug>.html` for pre-0.2.0 folders), read it for already-rendered KaTeX equations and attributed result strings. Use these to *complement* the scratchpad as cross-references — never to substitute for what the scratchpad says.
   - If `$PAPERS_DIR/<slug>/code-snapshot.md` exists, read it for code-grounded details: the exact loss form derived from code, named-component conventions, hyperparameter defaults, and code-vs-paper discrepancies. The §2 SVG should label components with the notation in the snapshot, and the §3 loss should match the canonical form recorded there.

5. **Lineage detection.** Scan `$PAPERS_DIR/.lineages/*.json` for any manifest whose `papers[].slug` array contains `<slug>`.
   - **Found** → use the manifest's `title` for the eyebrow text (`<title> · paper <position> of <total>`), set `prev_slug` / `next_slug` from neighboring entries, populate the footer prev/next links to `../<prev_slug>/companion.html` and `../<next_slug>/companion.html`. Empty prev for position 1; empty next for the last position.
   - **Not found** → ask the user once:
     > Is this paper part of a series? If yes, paste the full list of arXiv IDs (or slugs) in reading order — comma-separated — or press Enter for standalone.

     If a list is given, write a new manifest to `$PAPERS_DIR/.lineages/<lineage-slug>.json` with schema:
     ```json
     {
       "slug": "jepa",
       "title": "JEPA series",
       "papers": [
         {"slug": "i-jepa", "arxiv_id": "2301.08243", "position": 1},
         {"slug": "v-jepa", "arxiv_id": "2404.08471", "position": 2}
       ],
       "hub_html": null
     }
     ```
     The user picks `<lineage-slug>` (default-derived from the title via kebab). If they press Enter, treat as standalone — eyebrow text is `companion`, no prev/next, no manifest written.

   Edge cases:
   - **Insertion mid-series** → if the user later runs companion on a paper that conceptually belongs at position N inside an existing manifest, prompt *"Insert at position N? This will renumber papers ≥N"*. Rewrite manifest, then batch-update eyebrow text + prev/next links in the affected `companion.html` files.
   - **Removal** → an orphan check on `prev`/`next` of neighbors; ask explicit confirmation before rewriting manifest.
   - **Rename** → change only the manifest's `slug`/`title`. HTMLs encode position not lineage slug, so no rewrite is needed.
   - **Multi-lineage membership** (paper belongs to 2+ series) is out of scope v1. If a paper matches multiple manifests, prefer the most recently modified one and warn the user.

### Step 2 — Ask the three authoring questions

As specified in **Inputs** above: delivery cadence (session-level), math depth (paper-level), visual style (lineage-level). Skip cadence if already answered earlier in the session. Visual-style "Same as last?" prompt for subsequent papers in the same lineage.

### Step 3 — Plan the artifact

Sketch the section structure, the figures needed, the callouts, the self-check questions. Match the structure template (**Required structure** above) but adapt section titles to the paper. Lift the SVG component labels from scratchpad's **Named components & terminology** verbatim. Lift the §3 loss from scratchpad's **Loss function (verbatim)**.

### Step 4 — Write lineage recap (if applicable)

If `position > 1`, write a `<div class="recap">` that compresses the previous paper in 2–3 sentences. Pull from the previous paper's scratchpad (`$PAPERS_DIR/<prev_slug>/scratchpad.md`'s **Lede + prereqs material**) — concrete, not generic. This is what makes a lineage coherent.

### Step 5 — Write the artifact

Write the HTML via the `Write` tool to `$PAPERS_DIR/<slug>/companion.html` in a single call. Keep CSS consolidated at the top, HTML structured in order. Use the established class names (`.recap`, `.callout`, `.pull`, `.ablation`, `.benchmark-strip`, `.split`, `.self-check`, `.aside`) so reusable components work without re-defining.

### Step 6 — Sanity check

- `wc -l "$PAPERS_DIR/<slug>/companion.html"` to confirm length (700–1200 lines).
- `grep -E '\\hat[^_]*_\w\^\{[^}]+\}_\w' "$PAPERS_DIR/<slug>/companion.html"` should return nothing.
- Run the SVG validator: `uv run python scripts/validate_svg.py "$PAPERS_DIR/<slug>/companion.html"`. Fix any overflow before opening.
- Verify section count, figure count, callout count match the **Required structure** above.

### Step 7 — Regenerate the global index

Run the shared script so the new companion shows up with a `deep companion` badge:

```bash
uv run python scripts/regen_index.py
```

### Step 8 — Open and report

1. `open "$PAPERS_DIR/<slug>/companion.html"` (macOS) or `xdg-open "$PAPERS_DIR/<slug>/companion.html"` (Linux).
2. Tell the user: output path, paper title, lineage position if applicable, sections covered, key design decisions specific to this paper, and one specific nuance the artifact emphasizes.
3. For lineage work, ask sign-off before proceeding to the next paper.

## Things to avoid

- **Don't use AI image generation** for figures. All visuals are hand-coded SVG.
- **Don't use libraries beyond KaTeX**. No D3, no Chart.js, no React. Vanilla JS for any interactivity.
- **Don't reproduce paper figures verbatim** — synthesize new ones.
- **Don't write report-style prose with heavy bullets and headers**. This is an essay. Use prose, with bullets only when listing genuinely parallel items.
- **Don't pad shallow papers.** If a paper genuinely has only 4 sections of content, use 4 sections — don't invent material.
- **Don't add "Future Work" or "Implications" speculation unless the paper itself makes those claims.** Stick to what the paper does.
- **Don't include emojis or decorative flourishes.** Academic tone.
- **Don't link to URLs that haven't been verified.** All hyperlinks should resolve.

## Example invocations

> `/paper-companion i-jepa`

> `/paper-companion https://arxiv.org/abs/2301.08243`

> "Build me a companion artifact for I-JEPA" *(natural-language form; lineage detected from manifest if present)*

> "Continue the JEPA series — V-JEPA next" *(lineage manifest auto-populates position; no need to say "paper 3 of 6")*

> `/paper-companion 2511.08544 --force` *(extract from scratch when no explainer has been run; does not write `scratchpad.md`)*

> "Build me a study guide for the original Transformer paper"

The full pipeline:
1. `/paper-finder <topic>` — discover candidates, populate `memory-bank.md`.
2. `/paper-explainer <arxiv-id>` — orient: one-pager HTML + `scratchpad.md` + KB updates.
3. `/paper-companion <slug>` — master: deep companion artifact consuming the scratchpad.

## Notes for lineage projects

Lineage state lives in `$PAPERS_DIR/.lineages/<lineage-slug>.json` (schema in Process Step 1). When the user starts a series for the first time, Step 1 prompts for the full paper list and creates the manifest. Subsequent companions in the same lineage read from this manifest — the user never has to specify "paper 3 of 6" by hand.

If the lineage prompt is the first time a series is being defined, also ask:
- The ordering (chronological? conceptual? user-preferred?) — this determines the `position` field in the manifest
- Whether they want a final hub artifact (a navigation index linking all papers with a conceptual idea-flow map) — if yes, set `hub_html` to a filename like `<lineage-slug>-hub.html`; build it after the last paper.

Maintain consistency across the series:
- Same color tokens (from the shared distill.pub palette in this file's **Style guide**)
- Same component classes
- Same lede-prereqs-recap-sections-selfcheck-footer structure
- Recap card in each paper from §1 references the previous paper (pulled from the previous paper's scratchpad)

After the series is complete, optionally produce a hub artifact at `$PAPERS_DIR/.lineages/<lineage-slug>-hub.html` (or whatever `hub_html` names it) with:
- Timeline showing paper order with dates
- Concept dependency graph showing which ideas flow into which papers
- Quick-access links to each artifact
- A "what to read first" suggestion based on the user's background