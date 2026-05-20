#!/usr/bin/env python3
"""One-shot migration: consolidate per-paper KB files into a single global KB.

Pre-0.2.x layout had per-paper KB files: `<slug>/memory-bank.md`,
`<slug>/mind-graph.md`, `<slug>/references.bib`. After 0.2.x there is a single
global KB at `$PAPERS_DIR/{memory-bank,mind-graph,references.bib}`.

This script:

1. Walks every paper folder under `$PAPERS_DIR/`
2. Parses any per-paper KB files it finds
3. Merges into the global KB at the root, deduping by short-id / topic name /
   citation key
4. Backs up the per-paper KB files to `$PAPERS_DIR/.legacy-kb/<slug>/` (or
   deletes them with `--purge`)

Idempotent: re-running is a no-op once migration is done.

Usage:
    uv run python scripts/migrate_kb.py                # dry-run
    uv run python scripts/migrate_kb.py --yes          # actually migrate
    uv run python scripts/migrate_kb.py --yes --purge  # delete instead of backing up
    uv run python scripts/migrate_kb.py <papers-dir>   # explicit root
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# ----- resolution ------------------------------------------------------------------


def resolve_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("PAPER_EXPLAINER_OUTPUT_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "papers"


# ----- memory-bank.md merge --------------------------------------------------------

ENTRY_START_RE = re.compile(r"^### \[(?P<sid>[^\]]+)\]\s*(?P<title>.*)$", re.MULTILINE)


@dataclass
class MemEntry:
    short_id: str
    title: str
    body: str  # everything after the `### [sid] Title` line, up to next entry / `---`
    discovered_via: set[str] = field(default_factory=set)
    status: str = "discovered"

    def render(self) -> str:
        lines = [f"### [{self.short_id}] {self.title}".rstrip()]
        body = self.body.rstrip()

        # If a "Discovered via" line already exists in body, augment its value.
        # Otherwise insert a new line.
        if self.discovered_via:
            disc_str = ", ".join(sorted(self.discovered_via))
            m = re.search(r"(?m)^- \*\*Discovered via\*\*:\s*(.+)$", body)
            if m:
                existing = {s.strip() for s in m.group(1).split(",") if s.strip()}
                merged = sorted(existing | self.discovered_via)
                body = body[: m.start()] + f"- **Discovered via**: {', '.join(merged)}" + body[m.end():]
            else:
                # Insert after the URL or Citations line if present, else at the end of fields
                insert_at = None
                for marker in (r"^- \*\*URL\*\*:.*$", r"^- \*\*Citations\*\*:.*$"):
                    last = list(re.finditer(marker, body, re.MULTILINE))
                    if last:
                        insert_at = last[-1].end()
                        break
                line = f"\n- **Discovered via**: {disc_str}"
                if insert_at is not None:
                    body = body[:insert_at] + line + body[insert_at:]
                else:
                    body = body.rstrip() + line

        lines.append(body)
        return "\n".join(lines).rstrip() + "\n---\n"


def parse_memory_bank(text: str) -> list[MemEntry]:
    """Split into entries by `### [sid] Title` headers."""
    entries: list[MemEntry] = []
    matches = list(ENTRY_START_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.end():end]
        # Trim leading newline and trailing `---` if present
        chunk = chunk.lstrip("\n")
        chunk = re.sub(r"\n---\s*$", "", chunk).rstrip() + "\n"
        # Detect status
        sm = re.search(r"(?m)^- \*\*Status\*\*:\s*(\w+)", chunk)
        status = sm.group(1).strip() if sm else "discovered"
        entries.append(MemEntry(
            short_id=m.group("sid").strip(),
            title=m.group("title").strip(),
            body=chunk,
            status=status,
        ))
    return entries


def merge_memory_entries(per_paper: dict[str, list[MemEntry]]) -> list[MemEntry]:
    """Merge entries from many sources into a single list, deduped by short-id.

    Args:
        per_paper: map of slug -> list of entries from that paper's memory-bank.md

    Returns:
        Deduped list. Multiple discoveries of the same short-id merge their
        `discovered_via` sets; status escalates `discovered → analyzed`.
        For the body itself, the first non-empty richer body wins (heuristic:
        the one with more lines).
    """
    merged: dict[str, MemEntry] = {}
    for slug, entries in per_paper.items():
        for e in entries:
            sid = e.short_id
            if sid in merged:
                existing = merged[sid]
                existing.discovered_via.add(slug)
                # Status escalation
                if e.status == "analyzed":
                    existing.status = "analyzed"
                    # Prefer the analyzed body over a discovered one
                    if len(e.body) > len(existing.body):
                        existing.body = e.body
                else:
                    # Both discovered — keep the longer body
                    if len(e.body) > len(existing.body):
                        existing.body = e.body
            else:
                # Defensive copy
                merged[sid] = MemEntry(
                    short_id=sid,
                    title=e.title,
                    body=e.body,
                    discovered_via={slug},
                    status=e.status,
                )
    # Order: analyzed entries first, then alphabetically by short-id
    analyzed = sorted([e for e in merged.values() if e.status == "analyzed"], key=lambda e: e.short_id)
    discovered = sorted([e for e in merged.values() if e.status != "analyzed"], key=lambda e: e.short_id)
    return analyzed + discovered


# ----- mind-graph.md merge ---------------------------------------------------------

TOPIC_HEADER_RE = re.compile(r"^### (?P<topic>.+?)\s*$", re.MULTILINE)


@dataclass
class TopicEntry:
    name: str
    body: str
    source_slugs: set[str] = field(default_factory=set)

    def render(self) -> str:
        body = self.body.rstrip()
        return f"### {self.name}\n{body}\n\n---\n"


def parse_mind_graph(text: str) -> list[TopicEntry]:
    matches = list(TOPIC_HEADER_RE.finditer(text))
    entries: list[TopicEntry] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.end():end]
        chunk = chunk.lstrip("\n")
        chunk = re.sub(r"\n---\s*$", "", chunk).rstrip() + "\n"
        entries.append(TopicEntry(
            name=m.group("topic").strip(),
            body=chunk,
        ))
    return entries


def merge_mind_graphs(per_paper: dict[str, list[TopicEntry]]) -> list[TopicEntry]:
    """Dedupe by topic name (case-insensitive). First non-empty body wins;
    paper-bullet lines from later occurrences merge in if unique by short-id."""
    merged: dict[str, TopicEntry] = {}
    for slug, entries in per_paper.items():
        for e in entries:
            key = e.name.lower()
            if key in merged:
                existing = merged[key]
                existing.source_slugs.add(slug)
                # Find unique paper bullets from `e.body` not already in `existing.body`
                # A paper bullet is `  - [sid] ...` under one of the sub-lists.
                new_bullets = re.findall(r"(?m)^(  - \[[^\]]+\][^\n]*)$", e.body)
                for b in new_bullets:
                    if b not in existing.body:
                        # Append to the last sub-list section ("Other relevant papers"
                        # by convention) if it exists, else at the end of the body.
                        marker = "- **Other relevant papers**:"
                        if marker in existing.body:
                            existing.body = existing.body.replace(
                                marker,
                                marker + "\n" + b,
                                1,
                            )
                        else:
                            existing.body = existing.body.rstrip() + "\n" + b + "\n"
            else:
                merged[key] = TopicEntry(
                    name=e.name,
                    body=e.body,
                    source_slugs={slug},
                )
    return list(merged.values())


# ----- references.bib merge --------------------------------------------------------

BIB_KEY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)


def parse_bib_entries(text: str) -> dict[str, str]:
    """Split a .bib file into {key: full-entry-text}, deduped by key (first wins)."""
    entries: dict[str, str] = {}
    pos = 0
    while True:
        m = BIB_KEY_RE.search(text, pos)
        if not m:
            break
        # Walk matching braces from after the `{` after the comma — actually,
        # we matched `@type{key,`. Walk from m.end() searching for the matching
        # closing brace.
        depth = 1
        i = m.end()
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        entry_text = text[m.start():i].rstrip() + "\n"
        key = m.group(2)
        if key not in entries:
            entries[key] = entry_text
        pos = i
    return entries


def merge_bib(per_paper: dict[str, dict[str, str]]) -> dict[str, str]:
    """Merge per-paper bib dicts, first wins per key."""
    merged: dict[str, str] = {}
    for slug, entries in per_paper.items():
        for key, body in entries.items():
            if key not in merged:
                merged[key] = body
    return merged


# ----- driver ----------------------------------------------------------------------


def render_memory_bank(entries: list[MemEntry]) -> str:
    header = f"# Paper Memory Bank\nLast updated: {date.today().isoformat()}\n\n"
    return header + "\n".join(e.render() for e in entries)


def render_mind_graph(entries: list[TopicEntry]) -> str:
    header = f"# Mind Graph\nLast updated: {date.today().isoformat()}\n\n"
    return header + "\n".join(e.render() for e in entries)


def render_bib(entries: dict[str, str]) -> str:
    return "\n".join(entries[k] for k in sorted(entries))


@dataclass
class MigrationPlan:
    paper_folders: list[Path] = field(default_factory=list)
    mem_entries: list[MemEntry] = field(default_factory=list)
    topic_entries: list[TopicEntry] = field(default_factory=list)
    bib_entries: dict[str, str] = field(default_factory=dict)
    files_to_move: list[Path] = field(default_factory=list)


def build_plan(papers_dir: Path) -> MigrationPlan:
    plan = MigrationPlan()
    if not papers_dir.is_dir():
        return plan

    per_paper_mem: dict[str, list[MemEntry]] = {}
    per_paper_graph: dict[str, list[TopicEntry]] = {}
    per_paper_bib: dict[str, dict[str, str]] = {}

    for folder in sorted(papers_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        slug = folder.name
        plan.paper_folders.append(folder)

        mb = folder / "memory-bank.md"
        mg = folder / "mind-graph.md"
        rb = folder / "references.bib"

        if mb.is_file():
            try:
                per_paper_mem[slug] = parse_memory_bank(mb.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                print(f"  ! failed to parse {mb}: {e}", file=sys.stderr)
                per_paper_mem[slug] = []
            plan.files_to_move.append(mb)
        if mg.is_file():
            try:
                per_paper_graph[slug] = parse_mind_graph(mg.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                print(f"  ! failed to parse {mg}: {e}", file=sys.stderr)
                per_paper_graph[slug] = []
            plan.files_to_move.append(mg)
        if rb.is_file():
            try:
                per_paper_bib[slug] = parse_bib_entries(rb.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                print(f"  ! failed to parse {rb}: {e}", file=sys.stderr)
                per_paper_bib[slug] = {}
            plan.files_to_move.append(rb)

    plan.mem_entries = merge_memory_entries(per_paper_mem)
    plan.topic_entries = merge_mind_graphs(per_paper_graph)
    plan.bib_entries = merge_bib(per_paper_bib)
    return plan


def commit_migration(
    papers_dir: Path,
    plan: MigrationPlan,
    purge: bool,
) -> None:
    # Merge with any existing global KB files (rare but possible if user has
    # done partial migration before).
    global_mb = papers_dir / "memory-bank.md"
    global_mg = papers_dir / "mind-graph.md"
    global_rb = papers_dir / "references.bib"

    existing_mem: dict[str, list[MemEntry]] = {}
    existing_graph: dict[str, list[TopicEntry]] = {}
    existing_bib: dict[str, dict[str, str]] = {}

    if global_mb.is_file():
        existing_mem["__global__"] = parse_memory_bank(global_mb.read_text(encoding="utf-8", errors="replace"))
    if global_mg.is_file():
        existing_graph["__global__"] = parse_mind_graph(global_mg.read_text(encoding="utf-8", errors="replace"))
    if global_rb.is_file():
        existing_bib["__global__"] = parse_bib_entries(global_rb.read_text(encoding="utf-8", errors="replace"))

    # Combine the plan's merged entries with any existing global KB content,
    # using the same per-source dict shape so merge_* funcs handle dedup uniformly.
    combined_mem: dict[str, list[MemEntry]] = dict(existing_mem)
    combined_mem["__plan__"] = plan.mem_entries
    full_mem = merge_memory_entries(combined_mem)

    combined_graph: dict[str, list[TopicEntry]] = dict(existing_graph)
    combined_graph["__plan__"] = plan.topic_entries
    full_graph = merge_mind_graphs(combined_graph)

    combined_bib: dict[str, dict[str, str]] = dict(existing_bib)
    combined_bib["__plan__"] = plan.bib_entries
    full_bib = merge_bib(combined_bib)

    global_mb.write_text(render_memory_bank(full_mem), encoding="utf-8")
    global_mg.write_text(render_mind_graph(full_graph), encoding="utf-8")
    if full_bib:
        global_rb.write_text(render_bib(full_bib), encoding="utf-8")

    # Move or delete per-paper files
    if purge:
        for p in plan.files_to_move:
            p.unlink(missing_ok=True)
    else:
        backup_root = papers_dir / ".legacy-kb"
        backup_root.mkdir(exist_ok=True)
        for p in plan.files_to_move:
            slug = p.parent.name
            dest_dir = backup_root / slug
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(p), str(dest_dir / p.name))


def render_plan(plan: MigrationPlan, papers_dir: Path, commit: bool, purge: bool) -> None:
    if not plan.files_to_move:
        print(f"✓ No per-paper KB files found under {papers_dir}/<slug>/. Nothing to migrate.")
        return

    print(f"Scanning {papers_dir}\n")
    print(f"Found per-paper KB files in {len({p.parent.name for p in plan.files_to_move})} paper folders:")
    by_slug: dict[str, list[Path]] = {}
    for p in plan.files_to_move:
        by_slug.setdefault(p.parent.name, []).append(p)
    for slug in sorted(by_slug):
        files = ", ".join(p.name for p in by_slug[slug])
        print(f"  - {slug}/  →  {files}")

    print(f"\nMerged global KB will contain:")
    print(f"  memory-bank.md: {len(plan.mem_entries)} unique short-ids")
    print(f"  mind-graph.md:  {len(plan.topic_entries)} unique topics")
    print(f"  references.bib: {len(plan.bib_entries)} unique citation keys")

    if commit:
        print(f"\n✓ Written: {papers_dir}/memory-bank.md, mind-graph.md, references.bib")
        if purge:
            print(f"✓ Deleted: {len(plan.files_to_move)} per-paper KB files")
        else:
            print(f"✓ Moved: {len(plan.files_to_move)} per-paper KB files → {papers_dir}/.legacy-kb/<slug>/")
    else:
        print(f"\n(Dry-run.)")
        print("  Re-run with `--yes` to write the global KB and move per-paper files to .legacy-kb/")
        print("  Add `--purge` to delete per-paper files instead of backing them up.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("papers_dir", nargs="?", default=None,
                    help="root papers dir (default: $PAPER_EXPLAINER_OUTPUT_DIR or ~/papers)")
    ap.add_argument("--yes", action="store_true",
                    help="commit the migration (default is dry-run)")
    ap.add_argument("--purge", action="store_true",
                    help="delete per-paper KB files instead of moving to .legacy-kb/")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    papers_dir = resolve_root(args.papers_dir)
    if not papers_dir.is_dir():
        print(f"error: {papers_dir} does not exist", file=sys.stderr)
        return 1

    plan = build_plan(papers_dir)
    render_plan(plan, papers_dir, commit=args.yes, purge=args.purge)
    if args.yes and plan.files_to_move:
        commit_migration(papers_dir, plan, purge=args.purge)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
