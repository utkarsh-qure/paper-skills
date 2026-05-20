---
name: paper-finder
description: "Finds and organizes ML, CV, NLP, and AI research papers based on textual descriptions and keywords. Searches across arxiv, Google Scholar, Semantic Scholar, and top venues (CVPR, ECCV, ICCV, NeurIPS, ICML, ICLR, SIGGRAPH, SIGGRAPH Asia, EMNLP, ACL, CoRL, RSS, AAAI, IJCAI, WACV, BMVC, MICCAI, KDD, WWW, NAACL, COLM, and more). Maintains a persistent memory bank of discovered papers, a mind-graph linking papers to topics, individual paper summaries, and BibTeX entries. Use this skill whenever the user wants to find papers, search for related work, build a literature review, discover what exists on a topic, compare papers, organize references, generate BibTeX, or manage a research paper collection. Also use when the user mentions 'find me papers on...', 'what papers exist about...', 'related work for...', 'literature search', 'paper survey', or references any ML conference/venue by name."
---

# Paper Finder

Research paper discovery and organization agent. Find relevant ML/AI/CV/NLP papers, organize them into a persistent knowledge base, and connect them across topics.

## Step 0 — Confirm model (mandatory; ask once, before any other work)

Before any web search or filesystem write, ask the user one short question and wait for their answer:

> This run will use **Sonnet (latest, max thinking)** as the default. Want to switch to **Opus (latest, 1M context, max thinking)** for this search instead? (`y` = switch to Opus / `n` / Enter = stay on Sonnet)

Rules:
- Ask only once per session — if the user already answered earlier in the same session, don't ask again.
- If `y`: tell the user to run `/model opus[1m]` (and `/effort max` if not already set), then resume the skill in the upgraded session. Do not try to switch models yourself.
- If `n` / Enter / anything else: continue on the current model.
- Skip both the question and the switch entirely if the user explicitly pinned a model in their request (e.g. "use opus", "stay on sonnet").

Sonnet is the right default for breadth-style searches; Opus is worth the upgrade for long related-work synthesis or when the topic is very niche.

## Directory Structure

Each search/topic gets its own folder. The folder name should be a short, descriptive kebab-case name for the search topic (e.g., `mixed-resolution-diffusion/`, `video-generation-efficiency/`). The user may also specify a custom folder name. Create on first use:

```
<topic-name>/
  memory-bank.md        # Master list of all discovered papers
  mind-graph.md         # Topic-paper connection graph
  summaries/            # Per-paper .md files (via paper-explainer skill)
  references.bib        # Combined BibTeX for all papers
  pdfs/                 # Downloaded PDFs (only when user asks)
  discussions/          # Paper comparison logs
```

If the user references an existing folder (e.g., `@mixed-resolution-diffusion/`), operate within that folder. If starting a new search without a specified folder, derive a descriptive name from the search query.

## Searching for Papers

### Web search is mandatory

Use WebSearch and WebFetch for every search. Training knowledge alone is stale and misses anything published after the model's cutoff. If web tools are denied, retry once, then tell the user you need web access and explain what you'd search for.

### Search strategy

Run 2-3 parallel searches per query:

1. **Semantic Scholar API** via WebFetch: `https://api.semanticscholar.org/graph/v1/paper/search?query=<query>&limit=20&fields=title,authors,year,venue,abstract,externalIds,citationCount,url`. The public endpoint sometimes returns `402 Payment Required` or rate-limits silently. On 402 / 429 / empty payload: don't retry in a tight loop — fall back to WebSearch with the same query (`"<query>" site:semanticscholar.org` and `"<query>" arxiv`) and continue. Note the failure to the user once; don't repeat the warning per query.
2. **WebSearch** with queries like `<topic> paper <venue>` — good for Google Scholar results. Include the current year and previous year when looking for recent work, but **never use a year as a filter** — the canonical paper for a topic might be from 2014 (GANs) or 2017 (Transformers).
3. **Venue-specific** when relevant: `<topic> CVPR`, `<topic> site:openreview.net`
4. **Follow citations** on Semantic Scholar for highly relevant papers

Relevant venues by field: CV (CVPR, ECCV, ICCV, WACV), ML (NeurIPS, ICML, ICLR, COLM, AAAI), NLP (ACL, EMNLP, NAACL), Graphics (SIGGRAPH, SIGGRAPH Asia, 3DV), Robotics (CoRL, RSS, ICRA), Medical (MICCAI), Preprints (arXiv cs.CV/CL/LG/AI).

### Multi-angle search (mandatory)

A single concept can be described using very different vocabulary depending on the angle. After the initial direct-concept searches, you MUST run at least one additional search round covering these three angles. Skipping these is the #1 cause of missed papers.

1. **Cross-domain synonyms**: The same idea often has established names in adjacent fields. Before searching, brainstorm 2-3 alternative terms from related domains (graphics, neuroscience, signal processing, HCI, information theory, etc.). For example, "mixed-resolution spatial tokens" in ML maps to "foveated rendering" in graphics, "saliency-driven attention" in neuroscience, or "non-uniform sampling" in signal processing. Search using these alternative vocabularies.

2. **Enabling mechanisms / building blocks**: Search for the specific technical components needed to *implement* the concept — not just the concept itself. Every novel representation requires changes to attention, positional encodings, loss functions, normalization, etc. For example, mixed-resolution tokens require modified RoPE/positional embeddings, cross-resolution attention alignment, and boundary handling. Search for these mechanism-level terms (e.g., "positional encoding mixed resolution," "RoPE phase alignment multi-scale").

3. **Motivating applications / problem framing**: Papers solving the same technical problem may frame it as a different goal. Search from the perspective of *why* someone would build this (efficiency, speed, perceptual quality, hardware constraints). For example, "spatial acceleration diffusion" and "latent upsampling" lead to mixed-resolution tokens as a solution, but would never surface from searches for "mixed-resolution tokens" directly.

After initial results come in, also **follow the citation graph**: fetch the related-work section of 1-2 top-relevance papers and scan for references you haven't found yet.

### Understand the concept precisely

Before searching, understand the exact technical distinction the user cares about. If they describe a specific mechanism (e.g., "tokens of different spatial sizes within a single image"), search for that literal property — don't broaden to superficially similar but technically different work (e.g., cascaded pipelines, super-resolution).

### Filtering

- **Prioritize algorithmic contributions** over architecture/engineering/systems papers
- **Don't bias by year**. Surface both classics and recent work. Skip well-known background (DiT, VQGAN, ResNet, etc.) only when they're not directly relevant to the user's specific concept.
- **Note citation counts** when available — useful signal but not a filter
- **Tier results** by relevance to the user's specific concept (Tier 1 directly comparable, Tier 2 related methods/datasets, Tier 3 background)

## Memory Bank (`memory-bank.md`)

Master record of all discovered papers. Append new entries, never overwrite. Read existing file before searching to avoid duplicates.

```markdown
# Paper Memory Bank
Last updated: YYYY-MM-DD

### [short-id] Paper Title
- **Authors**: Author list
- **Venue**: Conference/Journal, Year
- **URL**: Link to paper
- **Citations**: N (if known)
- **Status**: discovered | summarized | analyzed
- **Topics**: topic1, topic2
- **Abstract**: 1-2 sentence description
- **Notes**: Relevance observations
---
```

## Mind Graph (`mind-graph.md`)

Topic-centric hierarchy — NOT pairwise paper comparisons. Each topic has 1-3 umbrella/landmark papers plus other relevant work.

```markdown
# Mind Graph
Last updated: YYYY-MM-DD

### Topic Name
- **Description**: One-line description
- **Related topics**: [other topic], [other topic]
- **Key papers**:
  - [short-id] Paper Title (Venue Year) — why it's key for this topic
- **Other relevant papers**:
  - [short-id] Paper Title — one-line note
```

## BibTeX (`references.bib`)

Write a single combined `references.bib` file with all papers. Use `@inproceedings` for conferences, `@article` for journals, `@misc` for arXiv preprints. Citation key = short-id.

## Paper Summaries and Comparisons

- **Summaries (long-form HTML 1-pager)**: Invoke the **paper-explainer** skill on the arXiv ID. It generates the full HTML explainer + `scratchpad.md` (+ optionally `code-snapshot.md` if a GitHub repo is found) under `$PAPER_EXPLAINER_OUTPUT_DIR/<paper-slug>/`, and appends related-paper metadata to the **global KB** at `$PAPER_EXPLAINER_OUTPUT_DIR/memory-bank.md` (along with `mind-graph.md` and `references.bib`).
- **Deep companion artifacts**: For papers worth deeply mastering (a handful — not the full memory bank), invoke the **paper-companion** skill on the slug. It consumes `scratchpad.md` (and `code-snapshot.md` when present) written by the explainer and produces a long-form distill.pub-style companion (700–1200 lines, custom SVGs, lineage continuity). When surfacing papers from this topic, **call out which ones already have companion artifacts** — those are the deeply-internalized core of the topic.
- **Summaries (short markdown)**: Save a 1-page markdown summary to `summaries/<short-id>.md` inside the topic folder. Only when the user explicitly asks — don't auto-summarize.
- **Comparisons**: Read existing summaries first (create if missing via paper-explainer), save discussion to `discussions/<descriptive-name>.md` inside the topic folder.
- **References to known papers**: Search the global `$PAPER_EXPLAINER_OUTPUT_DIR/memory-bank.md` first (cross-paper), then this topic folder's `memory-bank.md` (topic-scoped). Only re-read the original paper if the user explicitly asks.

### Scopes: topic-folder KB vs global KB

Paper-finder writes to the **topic folder** (`<topic-name>/memory-bank.md` etc.) when the user invokes it for a focused literature search. Paper-explainer writes to the **global** `$PAPER_EXPLAINER_OUTPUT_DIR/memory-bank.md` (and friends), accumulating across every paper that ever gets a one-pager. The two scopes coexist — the topic-folder KB is the per-topic working set; the global KB is the union of everything you've ever read.

## PDF Management

Do NOT download PDFs unless the user explicitly asks. When asked:

1. **Read `references.bib`** to extract the arXiv eprint ID or URL for each paper. This is the canonical source — do NOT read memory-bank.md or other files just to find download URLs.
2. Construct the PDF URL from the arXiv ID: `https://arxiv.org/pdf/<eprint-id>`
3. Download via curl/WebFetch and save to `pdfs/<short-id>.pdf`
4. Only fall back to memory-bank.md or web search if a paper has no entry in references.bib.

## Interaction Flow

1. **Search**: Run parallel web searches, present ranked list (title, venue, year, citations, one-line description)
2. **Record**: Add papers to memory-bank.md, update mind-graph.md, write references.bib
3. **Ask**: Whether user wants deeper analysis of any specific papers
