#!/usr/bin/env python3
"""Validate that every <text> in an inline SVG fits inside a containing <rect>.

Heuristic: estimated text width = char_count * font_size * 0.55.
A <text> at coordinates (tx, ty) is considered "inside" a <rect> if its center
(after accounting for text-anchor) sits within the rect, and its estimated
width does not exceed (rect.width - margin).

Usage:
    python3 validate_svg.py <html-or-svg-file>      # single file
    python3 validate_svg.py <dir>                   # all .html under dir
    python3 validate_svg.py                         # all .html under
                                                    # $PAPER_EXPLAINER_OUTPUT_DIR
                                                    # (default: ~/papers/)

Exit code 0 if no overflows found, 1 otherwise. Prints overflowing labels with
their predicted width vs. container width so the model can shorten or widen.
"""
from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"svg": "http://www.w3.org/2000/svg"}
MARGIN = 8


def _resolve_html_entities(text: str) -> str:
    """Inline SVGs inside HTML often use HTML named entities (&middot;, &nbsp;, etc.)
    which aren't valid XML entities. Resolve them to their Unicode characters
    so xml.etree can parse the SVG.
    """
    return html.unescape(text)


def _to_float(v: str | None, default: float = 0.0) -> float:
    if not v:
        return default
    m = re.match(r"-?\d+(\.\d+)?", v)
    return float(m.group()) if m else default


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def find_svgs(html_text: str) -> list[str]:
    return re.findall(r"<svg[\s\S]*?</svg>", html_text, flags=re.IGNORECASE)


def collect_rects_and_texts(svg_text: str) -> tuple[list[dict], list[dict]]:
    svg_text = _resolve_html_entities(svg_text)
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        return [], [{"_parse_error": str(e)}]
    rects, texts = [], []
    for el in root.iter():
        tag = _strip_ns(el.tag)
        if tag == "rect":
            x = _to_float(el.get("x"))
            y = _to_float(el.get("y"))
            w = _to_float(el.get("width"))
            h = _to_float(el.get("height"))
            rects.append({"x": x, "y": y, "w": w, "h": h})
        elif tag == "text":
            tx = _to_float(el.get("x"))
            ty = _to_float(el.get("y"))
            anchor = (el.get("text-anchor") or "start").lower()
            font_size = _to_float(el.get("font-size"), 12.0)
            content = "".join(el.itertext()).strip()
            est_w = len(content) * font_size * 0.55
            if anchor == "middle":
                left = tx - est_w / 2
            elif anchor == "end":
                left = tx - est_w
            else:
                left = tx
            right = left + est_w
            texts.append(
                {
                    "x": tx,
                    "y": ty,
                    "left": left,
                    "right": right,
                    "est_w": est_w,
                    "content": content,
                    "font_size": font_size,
                }
            )
    return rects, texts


def find_container(t: dict, rects: list[dict]) -> dict | None:
    cx = (t["left"] + t["right"]) / 2
    cy = t["y"]
    candidates = [
        r for r in rects if r["x"] <= cx <= r["x"] + r["w"] and r["y"] <= cy <= r["y"] + r["h"]
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: r["w"] * r["h"])
    return candidates[0]


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    issues: list[str] = []
    for i, svg in enumerate(find_svgs(text)):
        rects, texts = collect_rects_and_texts(svg)
        if texts and "_parse_error" in texts[0]:
            issues.append(f"{path}: svg #{i} parse error: {texts[0]['_parse_error']}")
            continue
        for t in texts:
            container = find_container(t, rects)
            if container is None:
                continue
            allowed = container["w"] - MARGIN
            if t["est_w"] > allowed:
                issues.append(
                    f"{path}: \"{t['content']}\" "
                    f"est_w={t['est_w']:.0f} > rect_w={container['w']:.0f}-{MARGIN} "
                    f"(font={t['font_size']:.0f}, chars={len(t['content'])})"
                )
    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        default = os.environ.get("PAPER_EXPLAINER_OUTPUT_DIR") or str(Path.home() / "papers")
        target = Path(default).expanduser()
        if not target.exists():
            print("usage: validate_svg.py <file-or-dir>", file=sys.stderr)
            print(f"(or set $PAPER_EXPLAINER_OUTPUT_DIR; tried {target})", file=sys.stderr)
            return 2
    else:
        target = Path(argv[1]).expanduser()
        if not target.exists():
            print(f"not found: {target}", file=sys.stderr)
            return 2
    if target.is_file():
        files = [target]
    else:
        # Skip hidden dirs (e.g. .cache/, .git/) when scanning a directory —
        # those contain raw arXiv HTML/SVG that isn't ours to validate.
        def _not_hidden(p: Path) -> bool:
            return not any(part.startswith(".") for part in p.relative_to(target).parts)
        files = sorted(p for p in target.rglob("*.html") if _not_hidden(p))
    all_issues: list[str] = []
    for f in files:
        all_issues.extend(validate_file(f))
    if all_issues:
        print("\n".join(all_issues))
        print(f"\n{len(all_issues)} overflow(s) found.", file=sys.stderr)
        return 1
    print("OK — no SVG text overflows.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
