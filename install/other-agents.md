# Setting up paper-skills for other agents

The skills are **plain markdown specs** plus **standalone Python scripts**. Any agent that supports custom system prompts / project rules / skills, and can run shell commands, can use them.

This guide covers Cursor in detail and a generic recipe for everything else.

---

## Prerequisites (all agents)

```bash
git clone https://github.com/<you>/paper-skills.git
cd paper-skills
uv sync                                                # Pillow + PyMuPDF
export PAPER_EXPLAINER_OUTPUT_DIR="$HOME/papers"       # or anywhere you like
```

Add `export PAPER_EXPLAINER_OUTPUT_DIR=…` to your shell rc so it persists.

---

## Cursor

Cursor reads skills from `~/.cursor/skills/<skill-name>/SKILL.md`. The YAML frontmatter at the top of each skill is what Cursor uses for auto-discovery.

```bash
mkdir -p ~/.cursor/skills/paper-finder ~/.cursor/skills/paper-explainer ~/.cursor/skills/paper-companion
ln -sf "$(pwd)/skills/paper-finder.md"    ~/.cursor/skills/paper-finder/SKILL.md
ln -sf "$(pwd)/skills/paper-explainer.md" ~/.cursor/skills/paper-explainer/SKILL.md
ln -sf "$(pwd)/skills/paper-companion.md" ~/.cursor/skills/paper-companion/SKILL.md
```

Verify:

```bash
ls -la ~/.cursor/skills/paper-*/SKILL.md
```

Restart Cursor. In any chat, paste an arXiv URL with a phrase like "explain this paper" — Cursor should auto-suggest the `paper-explainer` skill from the YAML frontmatter description. Say "build me a companion for X" or "I want to deeply understand Y" and Cursor will pick `paper-companion` (which then reads the scratchpad written by the explainer).

---

## Generic recipe (Aider, Cline, Continue, Codex CLI, Goose, …)

If your agent doesn't have a skills system, just provide the skill markdown as a **system prompt** or **project rule** the agent always follows. The skill is self-contained.

### 1. Provide the spec to the agent

Pick whichever your agent supports. Provide *all three* skills (`paper-finder.md`, `paper-explainer.md`, `paper-companion.md`) so the discover → orient → master pipeline is intact:

- **System prompt**: paste the full content of each skill (drop the YAML frontmatter — it's only meaningful to Cursor).
- **Project rule / convention file**: e.g. `.aider.conf.yml`'s `read:` field, Cline's `.clinerules/`, Continue's `~/.continue/config.json` `systemMessage`, Codex CLI's `~/.codex/instructions.md`. Same rule: paste the markdown body.
- **Manual paste**: if all else fails, paste the spec into your first message of the chat ("Use the following skill to handle paper requests …") followed by the arXiv URL. Less convenient but it works.

### 2. Make the scripts callable

The spec asks the agent to invoke `scripts/extract_figure.py` and `scripts/validate_svg.py` via shell. As long as your agent can run shell commands, you're done. Test it:

```bash
uv run python scripts/extract_figure.py --help
uv run python scripts/validate_svg.py --help
```

### 3. Verify env var visibility

The spec writes outputs to `$PAPER_EXPLAINER_OUTPUT_DIR`. Your agent should inherit env vars from the parent shell — confirm with:

```
Run: echo "$PAPER_EXPLAINER_OUTPUT_DIR"
```

If it prints empty, your agent is launched outside your shell. Set the env var in the agent's launch config (e.g. an `env` block in your launcher), or hardcode the path in the spec for that agent only.

### 4. First request

In any chat:

> Use the paper-explainer skill on https://arxiv.org/abs/2502.08321

The agent should follow the spec end-to-end and produce a folder under `$PAPER_EXPLAINER_OUTPUT_DIR/` containing the one-pager HTML, `scratchpad.md`, and KB files.

Then, when you want a deep companion artifact for the same paper:

> Use the paper-companion skill on screener-pathology-segmentation

The companion reads `scratchpad.md` written by the explainer and skips all web-fetching.

---

## Per-agent notes

All three skill specs (`paper-finder.md`, `paper-explainer.md`, `paper-companion.md`) follow the same install pattern. Pick one, then repeat for the others.

**Aider** — The skill spec is large (each ≈ 0.5–1k lines). Use `--read skills/paper-explainer.md skills/paper-companion.md skills/paper-finder.md` so they're project files the agent can refer to without burning a system-prompt slot. Ask Aider to "follow the instructions in `skills/<skill-name>.md`" when you want to use one.

**Cline / Continue** — Both have a "rules" / "system message" concept. Paste each spec there. Cline's `.clinerules/paper-explainer.md` (and `paper-companion.md`, `paper-finder.md`) work. Continue uses `~/.continue/config.json` → `systemMessage`.

**Codex CLI** — Drop the specs into `~/.codex/instructions.md` (or invoke via inline `@skills/paper-companion.md`).

**Goose** — Use a recipe per skill (`~/.config/goose/recipes/paper-explainer.yaml` etc.) that loads the spec as instructions.

**Anything else** — As long as the agent can (a) follow a markdown spec and (b) run shell commands, it works. The specs don't depend on any agent-specific tool — only generic operations like "fetch a URL", "write a file", "run a shell command".

---

## Troubleshooting

- **Agent doesn't run the scripts**: confirm shell access is enabled and the agent's working directory is the repo root (so relative paths to `scripts/` resolve).
- **Output goes to the wrong directory**: the spec uses `$PAPER_EXPLAINER_OUTPUT_DIR`. If your agent doesn't inherit env vars, edit your local copy of `skills/paper-explainer.md` and replace the env-var resolution at the top with a hardcoded path.
- **Figure / SVG / API issues**: see the Troubleshooting section of the top-level [README.md](../README.md). They are agent-agnostic.
- **Skill is too long for the agent's context**: this is a known limitation for small-context models. Break the spec into two halves and ask the agent to follow them sequentially, or use a larger-context model.
