# paper-skills

> Drop-in skills for AI coding agents that turn an arXiv URL into a beautiful, deeply-researched paper one-pager — not a typical AI summary.

`paper-skills` ships two markdown skill specs plus two small Python utilities. You install them once for your agent (Claude Code, Cursor, Aider, Cline, Codex CLI, …) and from then on you can drop an arXiv link into any chat and get back:

- a single-file HTML page with a custom SVG architecture diagram, key equations + verbatim paper quotes, embedded paper figures, attributed metric cards, "what most summaries miss" nuances, and a tiered chip cloud of related work,
- a persistent knowledge base (`memory-bank.md`, `mind-graph.md`, `references.bib`) that grows as you read more papers in the same area.

The agent does the deep reading — body, code, project page, related work — and is told (via the spec) to *complement*, not duplicate, the paper's own visuals.

The page below was built end-to-end by an agent following [`skills/paper-explainer.md`](skills/paper-explainer.md), no manual edits:

[**→ examples/screener-pathology-segmentation/**](examples/screener-pathology-segmentation/) — full output for [Screener (ICLR 2026)](https://arxiv.org/abs/2502.08321). Open the `.html` in a browser.

---

## What's in the repo

```
paper-skills/
├── README.md                      ← you are here
├── pyproject.toml                 ← uv-managed Python project (Pillow + PyMuPDF)
├── skills/
│   ├── paper-explainer.md         ← the main skill: arXiv URL → 1-pager HTML
│   └── paper-finder.md            ← multi-angle paper discovery + knowledge base
├── scripts/
│   ├── extract_figure.py          ← cross-platform figure+caption crop from PDF
│   └── validate_svg.py            ← SVG text-overflow validator
├── install/
│   ├── claude-code.md             ← detailed setup for Claude Code (slash commands)
│   └── other-agents.md            ← generic setup for any other agent
└── examples/
    └── screener-pathology-segmentation/
        ├── screener-pathology-segmentation.html
        ├── figure.png
        ├── memory-bank.md
        ├── mind-graph.md
        └── references.bib
```

---

## Quickstart (≈ 2 min)

```bash
git clone https://github.com/<you>/paper-skills.git
cd paper-skills
uv sync                                     # installs Pillow + PyMuPDF
export PAPER_EXPLAINER_OUTPUT_DIR="$HOME/papers"
```

Then wire the skills into your agent of choice (instructions per agent below).

Once wired up, in any chat:

> Use the paper-explainer skill on `https://arxiv.org/abs/2502.08321`

…and the agent will spend a few minutes reading the paper carefully, then drop a fresh `screener-pathology-segmentation/` folder into `$PAPER_EXPLAINER_OUTPUT_DIR/` with the HTML and knowledge-base files.

---

## What the explainer page contains

In order, top to bottom:

1. **Header card** — title, authors, date, version, venue, arXiv / GitHub / project page / Colab / HF demo / checkpoints pills, reading-time estimate, and a **copy-BibTeX** button (uses the official BibTeX from the project page when found, else generates one).
2. **TL;DR** — 2-3 punchy sentences with inline KaTeX math.
3. **Problem ↔ Method** — two-column bullets, each annotated with section anchors (`§3.2`, `Eq. 4`, `Table 4`) so the reader can dive deeper.
4. **Custom SVG diagram** — a synthesized mental model of the method, validated for text overflow.
5. **Key Equations & Quotes** — block-level KaTeX equations with labels alongside verbatim paper quotes (with anchors) so you can sanity-check the formal claims.
6. **From the Paper** — one or two cropped figures from the PDF (Fig. 1 by default; Fig. 2/3 if Fig. 1 is a pure architecture overview that the SVG already covers). Each is labeled by *type* (`qualitative results`, `mechanism`, `concept`, `teaser`, …) and captioned with what it adds beyond the SVG.
7. **Key Results** — 4-6 attributed metric cards (`dataset · setup · table`).
8. **What Most Summaries Miss** — 5-7 nuance bullets: acknowledged limitations, surprising ablations, code/paper discrepancies, training-stability quirks. The point of the whole exercise is that this section is non-trivial.
9. **Contributions + Related Work** — two-column.
10. **Tiered chip cloud** — Tier 1 directly comparable, Tier 2 related methods, Tier 3 background. Hover for a one-line factual hook drawn from each abstract.
11. **Footer** — official BibTeX citation, resources line (project page · GitHub · demo · video), and a single `Generated YYYY-MM-DD · v<N>` line. No paths, no usernames.

Plus **dark mode** and **print stylesheet**.

---

## How the pipeline works (8 steps)

1. **Resolve input** — arXiv URL/ID, or local PDF path. If `<paper-slug>.html` already exists in the output dir, ask whether to regenerate, update related-work only, open the existing one, or skip.
2. **Parallel fetch** — metadata (Atom API), full body (ar5iv → arxiv.org/html → PDF text fallback), Semantic Scholar reference list, GitHub repo URL, project-page URL. Each fetch is cached under `$PAPER_EXPLAINER_OUTPUT_DIR/.cache/<arxiv-id>/` so re-runs on the same paper are free.
3. **Deep reading** — full paper body (Method, Experiments, Ablations, Limitations, Appendix), the source code (loss + forward pass + config), the project page (author-curated TL;DR, official BibTeX), and 1-hop citation follow when the context demands it. The agent emits a scratchpad of section anchors + 4-7 nuances before doing anything visual.
4. **Figure extraction** — classify each figure in the paper by its caption (architecture / concept / qualitative / chart / teaser), pick **one or two** figures that *complement* the SVG diagram instead of duplicating it. Default is Fig. 1; override when Fig. 1 is a pure architecture overview (use Fig. 2/3 instead) or pair a teaser Fig. 1 with a separate mechanism figure. Run `scripts/extract_figure.py` (cross-platform PyMuPDF, with `qlmanage` as a fast macOS shortcut for page 1), then verify visually that neither figure nor caption is truncated.
5. **Multi-angle paper discovery** — direct-topic + cross-domain-synonym + venue-aware + mechanism-level searches, dedupe against the cited list, tier each paper.
6. **HTML generation** — render all sections per the spec, with KaTeX math, dark-mode tokens, tiered chips with hover tooltips, copy-BibTeX button.
7. **SVG validation** — `scripts/validate_svg.py` parses every inline SVG and verifies every `<text>` element fits inside its parent `<rect>` (predicted width = `chars × font_size × 0.55`, with 8 px margin). Re-roll any overflow.
8. **Knowledge base + index** — write `memory-bank.md` / `mind-graph.md` / `references.bib`, append entry to `$PAPER_EXPLAINER_OUTPUT_DIR/index.html`, open the page.

---

## Agent setup

The skills are agent-agnostic — they're markdown specs telling the agent how to behave. The setup just decides *where* the agent finds them.

### Claude Code (most polished)

[`install/claude-code.md`](install/claude-code.md) walks through the slash-command setup. The short version:

```bash
mkdir -p ~/.claude/commands
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.claude/commands/paper-explainer.md
ln -sf "$(pwd)/skills/paper-finder.md" ~/.claude/commands/paper-finder.md
```

Then in any Claude Code chat:

```
/paper-explainer https://arxiv.org/abs/2502.08321
```

### Cursor

```bash
mkdir -p ~/.cursor/skills/paper-explainer ~/.cursor/skills/paper-finder
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.cursor/skills/paper-explainer/SKILL.md
ln -sf "$(pwd)/skills/paper-finder.md" ~/.cursor/skills/paper-finder/SKILL.md
```

The YAML frontmatter on each skill is what Cursor reads to auto-suggest the skill when the user pastes an arXiv URL. Then in any chat just say "explain this paper: https://arxiv.org/abs/2502.08321".

### Any other agent (Aider, Cline, Continue, Codex CLI, Goose, …)

See [`install/other-agents.md`](install/other-agents.md). The generic recipe:

1. Install dependencies: `uv sync`.
2. Set the env var: `export PAPER_EXPLAINER_OUTPUT_DIR="$HOME/papers"`.
3. Provide the markdown content as a system prompt / project rule / skill, depending on what your agent supports. The YAML frontmatter is optional for non-Cursor agents.
4. Make sure the agent can run `uv run python scripts/extract_figure.py` and `scripts/validate_svg.py` via shell.

---

## Scripts

`scripts/extract_figure.py` — auto-detects and crops Fig. N + its caption from a PDF using content-density scanning. Cross-platform via PyMuPDF; uses `qlmanage` as a fast macOS shortcut for page 1 and `pdftoppm` if installed. Merges short caption blocks both above and below the figure.

```bash
uv run python scripts/extract_figure.py paper.pdf figure.png
uv run python scripts/extract_figure.py paper.pdf figure.png --page 3
uv run python scripts/extract_figure.py paper.pdf figure.png --x-band 80 1000   # narrow column
uv run python scripts/extract_figure.py paper.pdf figure.png --first            # first block, not largest
```

`scripts/validate_svg.py` — parses every inline SVG in an HTML file (or every HTML file under a directory) and reports text labels that overflow their parent `<rect>`. Used by `paper-explainer.md` to catch overflow before saving.

```bash
uv run python scripts/validate_svg.py output.html
uv run python scripts/validate_svg.py "$PAPER_EXPLAINER_OUTPUT_DIR"     # scan everything
uv run python scripts/validate_svg.py                                    # default = above
```

---

## Output directory

All explainer output lands in `$PAPER_EXPLAINER_OUTPUT_DIR` (defaults to `~/papers/`):

```
$PAPER_EXPLAINER_OUTPUT_DIR/
├── index.html                                  ← global index of all explainers
├── .cache/<arxiv-id>/                          ← cached metadata / body / refs / pdf
└── <paper-slug>/
    ├── <paper-slug>.html
    ├── figure.png   (or figure-1.png + figure-2.png)
    ├── memory-bank.md
    ├── mind-graph.md
    └── references.bib
```

Re-running `paper-explainer` on the same paper will hit the cache, skip every WebFetch, and prompt before overwriting.

---

## Troubleshooting

**Figure is truncated at the caption.** The auto-detector is mostly robust; for edge cases override:
- `--blank-run 16` for tighter caption merging
- `--caption-gap 120` if the caption is unusually far below the figure
- `--y-band 380 1450` to specify exact pixel bounds

**Figure on a later page wasn't extracted.** Pass `--page N`. PyMuPDF handles any page; `qlmanage` only does page 1.

**Semantic Scholar returns 402.** The API has hit a rate/billing limit. The skill falls back to extracting references from the paper body — slightly noisier but it works.

**SVG overflow keeps re-firing.** Look at the offender label, shorten it, or widen its `<rect>`. The validator's heuristic (`chars × font_size × 0.55`) is conservative; very narrow CJK glyphs are an edge case.

**ar5iv / arxiv.org/html return blank.** Some preprints aren't rendered as HTML. The skill falls back to `pdftotext -layout`. If `pdftotext` isn't installed (`brew install poppler`), PyMuPDF can extract text instead — both are supported.

**The agent over-reads / takes too long.** This is intentional — the spec asks for nuance-level depth, not a typical AI summary. Expect 2-6 minutes of reading + ~30 s of HTML generation per paper.

---

## Design choices worth knowing

- **Figures complement the SVG, not duplicate it.** The synthesized SVG is the agent's *mental model* of the method. The embedded figures are the paper's actual content (qualitative results, mechanism diagrams, training dynamics) — never the same thing twice.
- **Verbatim quotes over paraphrases.** The "Key Equations & Quotes" section quotes the paper directly with section anchors so a reader can sanity-check the agent's interpretation.
- **No mobile.** This pipeline is currently optimized for desktop / laptop browsers. Mobile rendering of the SVG diagrams + KaTeX is a known limitation.
- **No license, yet.** Ask the maintainer before redistributing.

---

## License

(TBD)
