#!/usr/bin/env python3
"""Prune the paper-skills cache and per-paper folders to the lean canonical layout.

What this removes (with `--yes`; dry-run otherwise):

1. **Orphan files at `$PAPERS_DIR/.cache/` root** — anything not under a per-arxiv-id
   subdir is a straggler from older conventions (e.g., `drifting.pdf`).
2. **Repo clones inside cache subdirs** — any dir with a `.git` child, *provided*
   the linked paper folder already has a `code-snapshot.md`. (The snapshot is the
   canonical artifact; the clone is transient.)
3. **`source.tar` and `source/`** — the arxiv LaTeX source bundle. Removed once
   the linked paper folder has `figure.png` (the only artifact we extract from it).
4. **`<arxiv-id>.pdf`** — removed once `body.txt` exists in the cache *and* the
   linked paper folder has `figure.png`. (Both extractions are durable.)
5. **Redundant body-fetch fallbacks** — `body.html`, `abs.html`, `ar5iv.html`,
   `arxiv_html.html`, `body_raw.html`. Removed if `body.txt` exists.
6. **Redundant project-page fetches** — `project_page_raw.html` etc. Removed if
   `project-page.md` exists.
7. **Empty cache subdirs.**

What this also handles:

- `--older-than <days>` — additionally remove whole `.cache/<arxiv-id>/` subdirs
  that haven't been touched in N days. Off by default.

Usage:
    uv run python scripts/prune_cache.py                  # dry-run on $PAPERS_DIR
    uv run python scripts/prune_cache.py --yes            # actually delete
    uv run python scripts/prune_cache.py <papers-dir>     # explicit root
    uv run python scripts/prune_cache.py --older-than 30  # also evict old cache subdirs
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Body-fetch fallback filenames produced by the older convention. These can
# always be dropped once `body.txt` exists.
BODY_FALLBACKS = {
    "body.html", "body_raw.html",
    "abs.html", "ar5iv.html", "arxiv_html.html", "arxiv.html",
}
PROJECT_PAGE_FALLBACKS = {
    "project_page_raw.html", "project-page_raw.html",
    "projectpage.html", "project-page.html",
}


def resolve_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("PAPER_EXPLAINER_OUTPUT_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "papers"


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


@dataclass
class Removal:
    path: Path
    reason: str
    size: int = 0

    def label(self) -> str:
        suffix = "/" if self.path.is_dir() else ""
        return f"{self.path}{suffix}"


# ----- arxiv-id ↔ paper-slug mapping ------------------------------------------------

ARXIV_ID_RE = re.compile(r"\*\*arXiv\s*ID\*\*\s*:\s*(\d{4}\.\d{4,5}|[A-Za-z\-]+/\d+)")
# Match "arXiv 2605.00809", "arXiv:2605.00809", or "arxiv.org/abs/2605.00809".
ARXIV_BADGE_RE = re.compile(
    r"(?:arXiv[\s:]+|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}|[A-Za-z\-]+/\d+)",
    re.IGNORECASE,
)


def build_arxiv_slug_map(root: Path) -> dict[str, str]:
    """For each paper folder under root, find its arXiv ID (best-effort)."""
    mapping: dict[str, str] = {}
    if not root.is_dir():
        return mapping
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        # Try scratchpad.md first
        scratchpad = folder / "scratchpad.md"
        if scratchpad.is_file():
            try:
                text = scratchpad.read_text(encoding="utf-8", errors="replace")
                m = ARXIV_ID_RE.search(text)
                if m:
                    mapping[m.group(1)] = folder.name
                    continue
            except OSError:
                pass
        # Fall back to scanning one-pager.html / <slug>.html for the arXiv badge
        html_candidates = [
            folder / "one-pager.html",
            folder / f"{folder.name}.html",
        ]
        for html_path in html_candidates:
            if not html_path.is_file():
                continue
            try:
                text = html_path.read_text(encoding="utf-8", errors="replace")
                m = ARXIV_BADGE_RE.search(text)
                if m:
                    mapping[m.group(1)] = folder.name
                    break
            except OSError:
                pass
    return mapping


# ----- prune logic ------------------------------------------------------------------


def find_repo_dirs(cache_dir: Path) -> list[Path]:
    """A repo clone is any direct subdir of cache_dir that contains a `.git`."""
    out = []
    for child in cache_dir.iterdir():
        if child.is_dir() and (child / ".git").exists():
            out.append(child)
    return out


def audit(
    papers_dir: Path,
    older_than_days: int | None,
) -> list[Removal]:
    cache_dir = papers_dir / ".cache"
    removals: list[Removal] = []

    if not cache_dir.is_dir():
        return removals

    arxiv_to_slug = build_arxiv_slug_map(papers_dir)

    # (1) Orphans at cache root
    for entry in sorted(cache_dir.iterdir()):
        if entry.is_file():
            removals.append(Removal(
                path=entry,
                reason="orphan at cache root (not under <arxiv-id>/)",
                size=entry.stat().st_size,
            ))

    # Per-arxiv-id cleanups
    now = time.time()
    for sub in sorted(cache_dir.iterdir()):
        if not sub.is_dir():
            continue
        arxiv_id = sub.name
        slug = arxiv_to_slug.get(arxiv_id)
        paper_folder = papers_dir / slug if slug else None

        # (older-than) whole-folder eviction takes precedence
        if older_than_days is not None:
            try:
                mtime = max(p.stat().st_mtime for p in sub.rglob("*"))
            except (OSError, ValueError):
                mtime = sub.stat().st_mtime
            if (now - mtime) > (older_than_days * 86400):
                removals.append(Removal(
                    path=sub,
                    reason=f"cache subdir untouched > {older_than_days} days",
                    size=dir_size(sub),
                ))
                continue  # whole-dir eviction; don't enumerate children

        body_txt_exists = (sub / "body.txt").is_file()
        project_page_md_exists = (sub / "project-page.md").is_file()
        paper_has_figure = bool(
            paper_folder and (
                (paper_folder / "figure.png").is_file()
                or (paper_folder / "figure-1.png").is_file()
            )
        )
        paper_has_snapshot = bool(
            paper_folder and (paper_folder / "code-snapshot.md").is_file()
        )

        # (2) repo clones — only if the paper has a code-snapshot already
        if paper_has_snapshot:
            for repo_dir in find_repo_dirs(sub):
                removals.append(Removal(
                    path=repo_dir,
                    reason=f"repo clone; ../{slug}/code-snapshot.md present",
                    size=dir_size(repo_dir),
                ))

        # (3) source bundle — only if a figure was extracted
        if paper_has_figure:
            for name in ("source.tar", "source"):
                p = sub / name
                if p.exists():
                    removals.append(Removal(
                        path=p,
                        reason=f"arxiv source bundle; ../{slug}/figure.png present",
                        size=dir_size(p),
                    ))

        # (4) cached PDF — only if body.txt + figure both durable
        if body_txt_exists and paper_has_figure:
            pdf = sub / f"{arxiv_id}.pdf"
            if pdf.is_file():
                removals.append(Removal(
                    path=pdf,
                    reason=f"PDF; body.txt + ../{slug}/figure.png present",
                    size=pdf.stat().st_size,
                ))

        # (5) redundant body HTML fallbacks
        if body_txt_exists:
            for name in BODY_FALLBACKS:
                p = sub / name
                if p.is_file():
                    removals.append(Removal(
                        path=p,
                        reason="redundant body fetch; body.txt is canonical",
                        size=p.stat().st_size,
                    ))

        # (6) redundant project page fallbacks
        if project_page_md_exists:
            for name in PROJECT_PAGE_FALLBACKS:
                p = sub / name
                if p.is_file():
                    removals.append(Removal(
                        path=p,
                        reason="redundant project-page fetch; project-page.md is canonical",
                        size=p.stat().st_size,
                    ))

        # (7) empty cache subdir — check at the end (after all enumeration)
        # We'll handle empty-dir cleanup at the very end of the dry-run

    return removals


# ----- output and commit ------------------------------------------------------------


def render_report(removals: list[Removal], commit: bool, papers_dir: Path) -> None:
    if not removals:
        print(f"✓ Cache at {papers_dir / '.cache'} is already lean — nothing to prune.")
        return

    # Group by parent (cache root / arxiv-id subdir)
    cache_root = papers_dir / ".cache"
    grouped: dict[str, list[Removal]] = {}
    for r in removals:
        try:
            rel = r.path.relative_to(cache_root)
        except ValueError:
            rel = r.path
        parts = rel.parts
        key = parts[0] if len(parts) > 1 else "<cache root>"
        grouped.setdefault(key, []).append(r)

    total_bytes = sum(r.size for r in removals)
    verb = "Removed" if commit else "Would remove"

    print(f"Auditing {cache_root}\n")
    for key in sorted(grouped):
        items = grouped[key]
        section_bytes = sum(r.size for r in items)
        if key == "<cache root>":
            print(f"Orphan files at cache root  ({len(items)} items · {human_size(section_bytes)})")
        else:
            print(f"{key}/  ({len(items)} items · {human_size(section_bytes)})")
        for r in items:
            try:
                rel = r.path.relative_to(cache_root)
            except ValueError:
                rel = r.path
            print(f"  - {rel}{'/' if r.path.is_dir() else ''}    {human_size(r.size)}   ({r.reason})")
        print()

    print(f"{verb}: {len(removals)} items · {human_size(total_bytes)}")
    if not commit:
        print("\n(Dry-run. Re-run with `--yes` to commit the deletions.)")


def commit_removals(removals: list[Removal]) -> None:
    for r in removals:
        try:
            if r.path.is_dir() and not r.path.is_symlink():
                shutil.rmtree(r.path)
            else:
                r.path.unlink(missing_ok=True)
        except OSError as e:
            print(f"  ! failed to remove {r.path}: {e}", file=sys.stderr)

    # Sweep empty cache subdirs after deletion
    # (only the ones that became empty; preserved otherwise)
    if not removals:
        return
    cache_root = removals[0].path.parents[-1]  # rough; replaced below
    # Better: derive cache root from any removal
    for r in removals:
        parts = r.path.parts
        if ".cache" in parts:
            idx = parts.index(".cache")
            cache_root = Path(*parts[: idx + 1])
            break
    if cache_root.exists() and cache_root.is_dir():
        for sub in sorted(cache_root.iterdir()):
            if sub.is_dir():
                try:
                    if not any(sub.iterdir()):
                        sub.rmdir()
                        print(f"  · removed empty cache subdir: {sub.name}/")
                except OSError:
                    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("papers_dir", nargs="?", default=None,
                    help="root papers dir (default: $PAPER_EXPLAINER_OUTPUT_DIR or ~/papers)")
    ap.add_argument("--yes", action="store_true",
                    help="commit deletions (default is dry-run)")
    ap.add_argument("--older-than", type=int, default=None, metavar="DAYS",
                    help="also remove cache subdirs untouched for >N days")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    papers_dir = resolve_root(args.papers_dir)
    if not papers_dir.is_dir():
        print(f"error: {papers_dir} does not exist", file=sys.stderr)
        return 1
    removals = audit(papers_dir, older_than_days=args.older_than)
    render_report(removals, commit=args.yes, papers_dir=papers_dir)
    if args.yes and removals:
        commit_removals(removals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
