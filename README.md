# paper-skills

> Drop-in skills for AI coding agents that turn an arXiv URL into a beautiful, deeply-researched paper one-pager — and, when a paper earns it, a long-form distill.pub-style companion artifact.

`paper-skills` ships three markdown skill specs plus three small Python utilities. The pipeline is **discover → orient → master**:

| Stage | Skill | Volume | Output |
|---|---|---|---|
| **Discover** | [`paper-finder`](skills/paper-finder.md) | hundreds | topic-folder `memory-bank.md` / `mind-graph.md` / `references.bib` (and feeds the global KB) |
| **Orient** | [`paper-explainer`](skills/paper-explainer.md) | dozens | `one-pager.html` + `scratchpad.md` + `code-snapshot.md` (if a repo is found) + global-KB updates |
| **Master** | [`paper-companion`](skills/paper-companion.md) | a handful | long-form `companion.html` (700–1200 lines) consuming the scratchpad + code snapshot |

You install the skills once for your agent (Claude Code, Cursor, Aider, Cline, Codex CLI, …) and from then on you can drop an arXiv link into any chat and get back:

- a single-file HTML one-pager with a custom SVG architecture diagram, key equations + verbatim paper quotes, embedded paper figures, attributed metric cards, "what most summaries miss" nuances, and a tiered chip cloud of related work,
- a durable `scratchpad.md` — the structured contract between explainer and companion — so the deep companion run is free of duplicated fetching,
- a `code-snapshot.md` (when a GitHub repo is found) — the distilled record of the linked code: key files with annotated excerpts, code-vs-paper discrepancies, configs. The clone itself is deleted after the snapshot is written; the snapshot is canonical.
- a persistent **global** knowledge base at the `$PAPER_EXPLAINER_OUTPUT_DIR/` root (`memory-bank.md`, `mind-graph.md`, `references.bib`) that grows as you read more papers — one canonical KB, not per-paper duplicates,
- on demand, a distill.pub-style companion artifact with hand-coded SVGs, interactive widgets, lineage continuity (recap cards + prev/next nav across a paper series), and self-check questions.

The agent does the deep reading — body, code, project page, related work — and is told (via the spec) to *complement*, not duplicate, the paper's own visuals. The companion run after an explainer **reads only from disk** — no re-fetch, no re-search.

The page below was built end-to-end by an agent following [`skills/paper-explainer.md`](skills/paper-explainer.md), no manual edits:

[**→ examples/screener-pathology-segmentation/**](examples/screener-pathology-segmentation/) — full output for [Screener (ICLR 2026)](https://arxiv.org/abs/2502.08321). Open the `.html` in a browser.

---

## What's in the repo

```
paper-skills/
├── README.md                      ← you are here
├── pyproject.toml                 ← uv-managed Python project (Pillow + PyMuPDF)
├── skills/
│   ├── paper-finder.md            ← discover: multi-angle paper discovery + topic KB
│   ├── paper-explainer.md         ← orient: arXiv URL → one-pager + scratchpad + code-snapshot
│   └── paper-companion.md         ← master: scratchpad → long-form distill.pub companion
├── scripts/
│   ├── extract_figure.py          ← cross-platform figure+caption crop from PDF
│   ├── validate_svg.py            ← SVG text-overflow validator
│   ├── regen_index.py             ← regenerates the global index with depth badges
│   ├── prune_cache.py             ← removes stale clones, source bundles, redundant fetches
│   └── migrate_kb.py              ← one-shot: consolidate per-paper KB → global KB (0.1.x → 0.2.x)
├── install/
│   ├── claude-code.md             ← detailed setup for Claude Code (slash commands)
│   └── other-agents.md            ← generic setup for any other agent
└── examples/
    └── screener-pathology-segmentation/
        ├── one-pager.html         ← orient: the visual explainer
        ├── companion.html         ← master: the deep companion
        ├── scratchpad.md          ← structured contract between explainer and companion
        └── figure.png             ← (code-snapshot.md would also live here when a repo is read;
                                       absent for Screener because no clone was made in this run)
```

The **global** KB (`memory-bank.md`, `mind-graph.md`, `references.bib`) and `index.html` live one level up at `$PAPER_EXPLAINER_OUTPUT_DIR/` — not inside the per-paper folder.

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

## How the pipeline works

### `paper-explainer` — 8 steps (orient)

1. **Resolve input** — arXiv URL/ID, or local PDF path. If `one-pager.html` already exists in the output dir, ask whether to regenerate, update related-work only, open the existing one, or skip.
2. **Parallel fetch** — metadata (Atom API), full body (ar5iv → arxiv.org/html → PDF text fallback), Semantic Scholar reference list, GitHub repo URL, project-page URL. Each fetch is cached under `$PAPER_EXPLAINER_OUTPUT_DIR/.cache/<arxiv-id>/` so re-runs on the same paper are free.
3. **Deep reading** — full paper body (Method, Experiments, Ablations, Limitations, Appendix), the source code (loss + forward pass + config), the project page (author-curated TL;DR, official BibTeX), and 1-hop citation follow when the context demands it. The agent persists `scratchpad.md` (metadata, section anchors, named components, loss verbatim, key equations, benchmarks, ablations with table attribution, nuances, lede/prereqs material) — this is the contract consumed by `paper-companion`.
4. **Figure extraction** — classify each figure in the paper by its caption (architecture / concept / qualitative / chart / teaser), pick **one or two** figures that *complement* the SVG diagram instead of duplicating it. Default is Fig. 1; override when Fig. 1 is a pure architecture overview (use Fig. 2/3 instead) or pair a teaser Fig. 1 with a separate mechanism figure. Run `scripts/extract_figure.py` (cross-platform PyMuPDF, with `qlmanage` as a fast macOS shortcut for page 1), then verify visually that neither figure nor caption is truncated.
5. **Multi-angle paper discovery** — direct-topic + cross-domain-synonym + venue-aware + mechanism-level searches, dedupe against the cited list, tier each paper.
6. **HTML generation** — render all sections per the spec, with KaTeX math, distill.pub design tokens (Crimson Pro + Karla + JetBrains Mono; ink/accent/teal/purple palette shared with `paper-companion`), tiered chips with hover tooltips, copy-BibTeX button.
7. **SVG validation** — `scripts/validate_svg.py` parses every inline SVG and verifies every `<text>` element fits inside its parent `<rect>` (predicted width = `chars × font_size × 0.55`, with 8 px margin). Re-roll any overflow.
8. **Knowledge base + index + cleanup** — append paper metadata to the **global** `$PAPER_EXPLAINER_OUTPUT_DIR/{memory-bank,mind-graph,references.bib}` (deduped by short-id / topic / citation key); regenerate `$PAPER_EXPLAINER_OUTPUT_DIR/index.html` via `scripts/regen_index.py`; delete the cached PDF, source bundle (if any), and repo clone (after `code-snapshot.md` is written); open the page.

### `paper-companion` — consume the scratchpad (master)

When invoked with `/paper-companion <slug>` (or arXiv ID/URL), the companion reads only from disk:

1. **Step 0** — confirm a frontier model (Opus 4.7 max thinking in Claude Code, GPT-5.5 max thinking fast in Cursor/Codex). Warn if you're on a lesser model.
2. **Step 1** — locate prior work and detect lineage. Read `scratchpad.md` if present (skip all web-fetching); if not, prompt the user to run `/paper-explainer <arxiv-id>` first — or pass `--force` to extract from scratch *without* writing scratchpad/KB. Then scan `$PAPER_EXPLAINER_OUTPUT_DIR/.lineages/*.json` — if the paper is part of a series, eyebrow text and footer prev/next links populate automatically. New lineages prompt once for the paper list.
3. **Steps 2–4** — ask three authoring questions (delivery cadence, math depth, visual style), plan the artifact, write the lineage recap card.
4. **Steps 5–6** — `Write` the HTML in one call, sanity-check (length, KaTeX patterns, SVG validation).
5. **Step 7** — regen the global index via the shared script so the new companion shows up with a `deep companion` badge.
6. **Step 8** — open the page and report.

### End-to-end on one paper

```bash
/paper-finder Find papers on self-supervised pathology segmentation in CT
# → topic-folder memory-bank.md / mind-graph.md / references.bib
#   (also feeds the global KB at $PAPERS_DIR/)

/paper-explainer https://arxiv.org/abs/2301.08243
# → ~/papers/i-jepa/
#     ├── one-pager.html         (the visual explainer, distill.pub theme)
#     ├── scratchpad.md          (structured deep-read; 9-section contract)
#     ├── code-snapshot.md       (annotated key files from the linked GitHub repo;
#     │                           clone was deleted after the snapshot)
#     └── figure.png
# Plus ~/papers/memory-bank.md, mind-graph.md, references.bib appended to.
# Plus ~/papers/index.html regenerated with a `one-pager` badge.
# Cache reduced: PDF + repo clone + source bundle all gone.

/paper-companion i-jepa
# Reads scratchpad.md + code-snapshot.md; no WebFetch / WebSearch / arxiv.org curl.
# → ~/papers/i-jepa/companion.html
# Index regenerates with an additional `deep companion` badge.
```

---

## Agent setup

The skills are agent-agnostic — they're markdown specs telling the agent how to behave. The setup just decides *where* the agent finds them.

### Claude Code (most polished)

[`install/claude-code.md`](install/claude-code.md) walks through the slash-command setup. The short version:

```bash
mkdir -p ~/.claude/commands
ln -sf "$(pwd)/skills/paper-finder.md"    ~/.claude/commands/paper-finder.md
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.claude/commands/paper-explainer.md
ln -sf "$(pwd)/skills/paper-companion.md" ~/.claude/commands/paper-companion.md
```

Then in any Claude Code chat:

```
/paper-explainer https://arxiv.org/abs/2502.08321
/paper-companion screener-pathology-segmentation
```

### Cursor

```bash
mkdir -p ~/.cursor/skills/paper-finder ~/.cursor/skills/paper-explainer ~/.cursor/skills/paper-companion
ln -sf "$(pwd)/skills/paper-finder.md"    ~/.cursor/skills/paper-finder/SKILL.md
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.cursor/skills/paper-explainer/SKILL.md
ln -sf "$(pwd)/skills/paper-companion.md" ~/.cursor/skills/paper-companion/SKILL.md
```

The YAML frontmatter on each skill is what Cursor reads to auto-suggest the skill when the user pastes an arXiv URL or says "build me a companion for X". Then in any chat just say "explain this paper: https://arxiv.org/abs/2502.08321" or "build me a deep companion for screener-pathology-segmentation".

### Any other agent (Aider, Cline, Continue, Codex CLI, Goose, …)

See [`install/other-agents.md`](install/other-agents.md). The generic recipe:

1. Install dependencies: `uv sync`.
2. Set the env var: `export PAPER_EXPLAINER_OUTPUT_DIR="$HOME/papers"`.
3. Provide all three markdown specs (`paper-finder.md`, `paper-explainer.md`, `paper-companion.md`) as system prompts / project rules / skills, depending on what your agent supports. The YAML frontmatter is optional for non-Cursor agents.
4. Make sure the agent can run `uv run python scripts/extract_figure.py`, `scripts/validate_svg.py`, `scripts/regen_index.py`, `scripts/prune_cache.py`, and `scripts/migrate_kb.py` via shell.

---

## Scripts

`scripts/extract_figure.py` — auto-detects and crops Fig. N + its caption from a PDF using content-density scanning. Cross-platform via PyMuPDF; uses `qlmanage` as a fast macOS shortcut for page 1 and `pdftoppm` if installed. Merges short caption blocks both above and below the figure.

```bash
uv run python scripts/extract_figure.py paper.pdf figure.png
uv run python scripts/extract_figure.py paper.pdf figure.png --page 3
uv run python scripts/extract_figure.py paper.pdf figure.png --x-band 80 1000   # narrow column
uv run python scripts/extract_figure.py paper.pdf figure.png --first            # first block, not largest
```

`scripts/validate_svg.py` — parses every inline SVG in an HTML file (or every HTML file under a directory) and reports text labels that overflow their parent `<rect>`. Used by `paper-explainer.md` and `paper-companion.md` to catch overflow before saving.

```bash
uv run python scripts/validate_svg.py output.html
uv run python scripts/validate_svg.py "$PAPER_EXPLAINER_OUTPUT_DIR"     # scan everything
uv run python scripts/validate_svg.py                                    # default = above
```

`scripts/regen_index.py` — walks `$PAPER_EXPLAINER_OUTPUT_DIR` and regenerates the global `index.html` with one row per paper, depth badges (`one-pager` and `deep companion`), and a depth-filter pill toggle that persists via `localStorage`. Both `paper-explainer` and `paper-companion` call this at the end of their runs — a single source of truth for the index template.

```bash
uv run python scripts/regen_index.py                # uses $PAPER_EXPLAINER_OUTPUT_DIR
uv run python scripts/regen_index.py ~/papers       # explicit root
```

`scripts/prune_cache.py` — audits and trims `$PAPER_EXPLAINER_OUTPUT_DIR/.cache/`. Removes (with `--yes`; dry-run otherwise): orphan files at the cache root, redundant body-fetch fallbacks (`body.html`, `abs.html`, `ar5iv.html`, …) once `body.txt` exists, repo clones once `code-snapshot.md` exists, source bundles once `figure.png` exists, and cached PDFs once both `body.txt` and `figure.png` exist. Safe by default — never touches paper folders or the global KB.

```bash
uv run python scripts/prune_cache.py                  # dry-run on $PAPER_EXPLAINER_OUTPUT_DIR
uv run python scripts/prune_cache.py --yes            # actually delete
uv run python scripts/prune_cache.py --older-than 30  # also evict cache subdirs untouched for >30 days
```

`scripts/migrate_kb.py` — one-shot migration from the 0.1.x per-paper KB layout to the 0.2.x global KB. Walks `<slug>/memory-bank.md`, `<slug>/mind-graph.md`, `<slug>/references.bib`, dedupes (by short-id / topic name / citation key), writes the merged result to `$PAPER_EXPLAINER_OUTPUT_DIR/{memory-bank,mind-graph,references.bib}`, and either backs up the per-paper files to `$PAPER_EXPLAINER_OUTPUT_DIR/.legacy-kb/<slug>/` or deletes them with `--purge`.

```bash
uv run python scripts/migrate_kb.py                # dry-run
uv run python scripts/migrate_kb.py --yes          # migrate; back up per-paper files
uv run python scripts/migrate_kb.py --yes --purge  # migrate; delete per-paper files
```

---

## Output directory

All pipeline output lands in `$PAPER_EXPLAINER_OUTPUT_DIR` (defaults to `~/papers/`):

```
$PAPER_EXPLAINER_OUTPUT_DIR/
├── index.html                                  ← global index with depth badges
├── memory-bank.md                              ← global KB: every paper discovered across all runs
├── mind-graph.md                               ← global topic-paper graph
├── references.bib                              ← global BibTeX
├── .cache/<arxiv-id>/                          ← lean cache: metadata, body.txt, references.json,
│                                                  readme.md, project-page.md, *_url.txt
├── .lineages/<lineage-slug>.json               ← lineage manifest (paper list + ordering)
└── <paper-slug>/
    ├── one-pager.html                          ← orient (paper-explainer)
    ├── scratchpad.md                           ← structured deep-read (paper-explainer)
    ├── code-snapshot.md                        ← annotated code findings (when a GitHub repo exists)
    ├── companion.html                          ← long-form companion (paper-companion, optional)
    └── figure.png   (or figure-1.png + figure-2.png)
```

Re-running `paper-explainer` on the same paper will hit the cache, skip every WebFetch, and prompt before overwriting. Running `paper-companion` after `paper-explainer` reads only from `scratchpad.md` (and `code-snapshot.md` if present) — no re-fetch, no re-search.

After every successful run, the cache trims itself: the cached PDF is removed once `body.txt` + `figure.png` are confirmed; the GitHub repo clone is removed once `code-snapshot.md` is written; the arxiv source bundle is removed once `figure.png` is extracted. The cache stays bounded to the durable artifacts.

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
