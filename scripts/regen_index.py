#!/usr/bin/env python3
"""Regenerate the global index page at $PAPER_EXPLAINER_OUTPUT_DIR/index.html.

Walks one level under $PAPER_EXPLAINER_OUTPUT_DIR. For each folder containing
<slug>.html, parses a small set of fields from the HTML (title, authors, date)
and notes whether an adjacent companion.html exists. Emits a fresh index.html
listing every paper with depth badges and a filter toggle.

Usage:
    uv run python scripts/regen_index.py            # uses $PAPER_EXPLAINER_OUTPUT_DIR
    uv run python scripts/regen_index.py <dir>      # explicit root

Both `paper-explainer` and `paper-companion` call this at the end of their
runs. Design tokens match the distill.pub-style palette shared across the
explainer one-pager and companion HTML.
"""
from __future__ import annotations

import html
import os
import re
import sys
from datetime import date
from pathlib import Path

INDEX_FILENAME = "index.html"

TITLE_RE = re.compile(r"<title>([^<]+?)\s*—\s*Paper", re.IGNORECASE)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
AUTHORS_META_RE = re.compile(
    r'<meta\s+name="authors"\s+content="([^"]+)"', re.IGNORECASE
)
DATE_META_RE = re.compile(r'<meta\s+name="date"\s+content="([^"]+)"', re.IGNORECASE)
DATE_FOOTER_RE = re.compile(r"Generated\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def resolve_root(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).expanduser()
    env = os.environ.get("PAPER_EXPLAINER_OUTPUT_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "papers"


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def parse_paper(folder: Path) -> dict | None:
    slug = folder.name
    if slug.startswith("."):
        return None
    html_path = folder / f"{slug}.html"
    if not html_path.is_file():
        return None

    try:
        body = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    title = ""
    m = TITLE_RE.search(body)
    if m:
        title = html.unescape(m.group(1)).strip()
    if not title:
        m = H1_RE.search(body)
        if m:
            title = html.unescape(strip_tags(m.group(1)))

    authors = ""
    m = AUTHORS_META_RE.search(body)
    if m:
        authors = html.unescape(m.group(1)).strip()

    paper_date = ""
    m = DATE_META_RE.search(body)
    if m:
        paper_date = m.group(1).strip()
    if not paper_date:
        m = DATE_FOOTER_RE.search(body)
        if m:
            paper_date = m.group(1)
    if not paper_date:
        paper_date = date.fromtimestamp(html_path.stat().st_mtime).isoformat()

    return {
        "slug": slug,
        "title": title or slug,
        "authors": authors,
        "date": paper_date,
        "has_companion": (folder / "companion.html").is_file(),
        "has_scratchpad": (folder / "scratchpad.md").is_file(),
        "folder": folder,
    }


def collect(root: Path) -> list[dict]:
    if not root.is_dir():
        return []
    papers = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        info = parse_paper(entry)
        if info is not None:
            papers.append(info)
    papers.sort(key=lambda p: p["date"], reverse=True)
    return papers


PAGE_CSS = """\
:root {
  --serif: 'Crimson Pro', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
  --sans:  'Karla', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
  --mono:  'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  --ink: #1a1a1a; --ink-soft: #444; --ink-mute: #7a7a7a;
  --paper: #fdfdfb; --rule: #e8e6e1; --rule-soft: #f5f3ee;
  --accent: #8b3a1f; --teal: #1d6a6a; --purple: #534ab7;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--paper); color: var(--ink);
  font-family: var(--serif); line-height: 1.55;
  padding: 48px 24px 96px;
}
.page { max-width: 960px; margin: 0 auto; }
h1 {
  font-family: var(--sans); font-size: 28px; font-weight: 700;
  margin-bottom: 8px; color: var(--ink);
}
.subtitle {
  font-family: var(--sans); font-size: 14px; color: var(--ink-mute);
  margin-bottom: 32px;
}
.filter-row {
  display: flex; gap: 8px; align-items: center;
  margin-bottom: 24px; padding-bottom: 16px;
  border-bottom: 1px solid var(--rule);
}
.filter-label {
  font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--ink-mute); margin-right: 4px;
}
.filter-pill {
  font-family: var(--sans); font-size: 13px;
  padding: 5px 14px; border: 1px solid var(--rule);
  border-radius: 18px; color: var(--ink-soft); cursor: pointer;
  background: transparent; transition: border-color 0.15s, color 0.15s;
}
.filter-pill:hover { border-color: var(--accent); color: var(--ink); }
.filter-pill.active {
  border-color: var(--accent); color: var(--accent); font-weight: 600;
}
.row {
  display: grid; grid-template-columns: 1fr auto;
  gap: 16px; align-items: baseline;
  padding: 16px 0; border-bottom: 1px solid var(--rule);
}
.row.hidden { display: none; }
.row-main .title {
  font-family: var(--sans); font-weight: 600; font-size: 16px;
  color: var(--ink); text-decoration: none;
}
.row-main .title:hover { color: var(--accent); }
.row-main .meta {
  font-family: var(--sans); font-size: 13px; color: var(--ink-mute);
  margin-top: 4px;
}
.row-badges { display: flex; gap: 8px; flex-shrink: 0; }
.badge {
  display: inline-flex; align-items: center;
  font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 10px; border: 1px solid var(--rule);
  border-radius: 16px; color: var(--ink-mute); text-decoration: none;
  transition: border-color 0.15s, color 0.15s;
}
.badge:hover { border-color: var(--accent); color: var(--accent); }
.badge.companion {
  border-color: var(--accent); color: var(--accent);
}
.empty {
  font-family: var(--sans); color: var(--ink-mute);
  padding: 32px 0; text-align: center;
}
@media (max-width: 640px) {
  .row { grid-template-columns: 1fr; }
  .row-badges { margin-top: 4px; }
}
"""


FILTER_JS = """\
(function () {
  var KEY = 'paper-skills:index-filter';
  var pills = document.querySelectorAll('.filter-pill');
  var rows = document.querySelectorAll('.row');
  function applyFilter(mode) {
    rows.forEach(function (r) {
      if (mode === 'companion' && r.dataset.companion !== '1') {
        r.classList.add('hidden');
      } else {
        r.classList.remove('hidden');
      }
    });
    pills.forEach(function (p) {
      p.classList.toggle('active', p.dataset.mode === mode);
    });
  }
  var saved = 'all';
  try { saved = window.localStorage.getItem(KEY) || 'all'; } catch (e) {}
  applyFilter(saved);
  pills.forEach(function (p) {
    p.addEventListener('click', function () {
      var mode = p.dataset.mode;
      applyFilter(mode);
      try { window.localStorage.setItem(KEY, mode); } catch (e) {}
    });
  });
})();
"""


def render(papers: list[dict]) -> str:
    total = len(papers)
    companion_count = sum(1 for p in papers if p["has_companion"])

    rows_html = []
    if not papers:
        rows_html.append('<div class="empty">No papers yet. Run /paper-explainer on an arXiv URL to populate.</div>')
    else:
        for p in papers:
            slug = html.escape(p["slug"])
            title = html.escape(p["title"])
            authors = html.escape(p["authors"]) if p["authors"] else ""
            paper_date = html.escape(p["date"])
            meta_parts = []
            if authors:
                meta_parts.append(authors)
            if paper_date:
                meta_parts.append(paper_date)
            meta = " · ".join(meta_parts)
            badges = [
                f'<a class="badge" href="{slug}/{slug}.html">one-pager</a>'
            ]
            if p["has_companion"]:
                badges.append(
                    f'<a class="badge companion" href="{slug}/companion.html">deep companion</a>'
                )
            rows_html.append(
                f'<div class="row" data-companion="{1 if p["has_companion"] else 0}">'
                f'<div class="row-main">'
                f'<a class="title" href="{slug}/{slug}.html">{title}</a>'
                f'<div class="meta">{meta}</div>'
                f'</div>'
                f'<div class="row-badges">{"".join(badges)}</div>'
                f'</div>'
            )

    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>paper-skills · index</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
</head>
<body>
<main class="page">
<h1>paper-skills</h1>
<div class="subtitle">{total} paper{"" if total == 1 else "s"} oriented · {companion_count} with deep companion · regenerated {today}</div>
<div class="filter-row">
  <span class="filter-label">depth</span>
  <button class="filter-pill" data-mode="all">All papers ({total})</button>
  <button class="filter-pill" data-mode="companion">With companion ({companion_count})</button>
</div>
<div class="rows">
{chr(10).join(rows_html)}
</div>
</main>
<script>{FILTER_JS}</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    root = resolve_root(argv)
    if not root.is_dir():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 1
    papers = collect(root)
    out = root / INDEX_FILENAME
    out.write_text(render(papers), encoding="utf-8")
    print(f"wrote {out} ({len(papers)} paper{'' if len(papers) == 1 else 's'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
