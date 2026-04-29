# Setting up paper-skills for Claude Code

paper-skills is the most polished on Claude Code because Claude Code natively supports markdown skills as **slash commands** out of `~/.claude/commands/`.

## Prerequisites

```bash
git clone https://github.com/<you>/paper-skills.git
cd paper-skills
uv sync                                                # Pillow + PyMuPDF
```

Add to your `~/.zshrc` / `~/.bashrc`:

```bash
export PAPER_EXPLAINER_OUTPUT_DIR="$HOME/papers"       # change to whatever you like
```

(If you skip this, papers default to `~/papers/`.)

## Wire up the skills

Symlink the two skill files into Claude's commands directory:

```bash
mkdir -p ~/.claude/commands
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.claude/commands/paper-explainer.md
ln -sf "$(pwd)/skills/paper-finder.md"    ~/.claude/commands/paper-finder.md
```

Verify:

```bash
ls -la ~/.claude/commands/paper-*.md
```

You should see two symlinks pointing into `…/paper-skills/skills/`.

## Usage

Open Claude Code (`claude` CLI or the desktop app) in any directory and type:

```
/paper-explainer https://arxiv.org/abs/2502.08321
```

Claude will:

1. Resolve the arXiv ID to `2502.08321`.
2. Check `$PAPER_EXPLAINER_OUTPUT_DIR/screener-pathology-segmentation/screener-pathology-segmentation.html` — if present, ask whether to regenerate.
3. Otherwise: fetch metadata, body, references, GitHub repo, project page (all in parallel; cached after first run).
4. Read the paper carefully (Method / Experiments / Ablations / Limitations / Appendix), source code, and the project page.
5. Run `scripts/extract_figure.py` from this repo on the downloaded PDF.
6. Generate the HTML, validate the SVG, write the knowledge base, append to the global index, and `open` the page.

You can also pass:

- a bare arXiv ID: `/paper-explainer 2502.08321`
- a local PDF path: `/paper-explainer ~/Downloads/screener.pdf`

## Discovery / lit-review

For multi-paper discovery (without the full HTML), use the partner skill:

```
/paper-finder Find papers on self-supervised pathology segmentation in CT
```

This builds up `memory-bank.md` / `mind-graph.md` / `references.bib` in a topic folder you can keep growing over time.

## Tips

- **Run order matters when chaining**: `/paper-finder` first to build a topic memory bank, then `/paper-explainer` on the most-cited paper. The explainer reuses the same `references.bib` format so the two stay coherent.
- **The cache is your friend**: re-running `/paper-explainer` on the same paper is essentially free. Use it to iterate on a one-pager without re-fetching anything.
- **Override figure extraction**: if the auto-detected figure looks wrong, ask Claude in chat: "use Fig. 2 from page 3 instead, with `--x-band 80 1000`". The skill spec teaches it the relevant flags.
- **Update the skills**: changes to `skills/*.md` in this repo are live immediately because the symlinks point at the working tree. `git pull` is enough to update.

## Troubleshooting

- **`/paper-explainer` doesn't appear**: confirm `~/.claude/commands/paper-explainer.md` exists and is a symlink to your clone (`ls -la`). Restart Claude Code.
- **`PAPER_EXPLAINER_OUTPUT_DIR` isn't picked up**: Claude Code launches with the env from the parent shell. Reopen the app/terminal after editing your shell rc.
- **`uv: command not found`**: install uv (`brew install uv` or see [astral.sh/uv](https://docs.astral.sh/uv/)). The scripts work with vanilla `pip` too — `pip install pillow pymupdf` and run `python3 scripts/...` instead of `uv run python scripts/...`.
- **Figure crops are wrong**: see the Troubleshooting section of the top-level [README.md](../README.md).
