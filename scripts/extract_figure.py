#!/usr/bin/env python3
"""Auto-extract a figure (default Fig. 1) + its caption from a paper PDF.

Workflow:
  1. Render the requested PDF page to PNG (cross-platform via PyMuPDF; macOS
     has a fast `qlmanage` shortcut for page 1; `pdftoppm` is also accepted if
     present).
  2. Scan rows of the rendered page to find content density.
  3. Identify the largest contiguous "content block" — this is the figure.
  4. Merge any small adjacent block above OR below the figure that fits the
     "caption" profile (short, close to the figure).
  5. Add small top/bottom margins, crop, and write to <out>.png.

The heuristic is content-density-based: a row is "content" if it has enough
non-white pixels in some column band. The figure+caption is the largest such
block (or the first one if --first is passed).

Usage:
    python3 extract_figure.py <pdf-path> <out-png>
    python3 extract_figure.py <pdf-path> <out-png> --x-band 100 1750  # column range
    python3 extract_figure.py <pdf-path> <out-png> --first             # first block
    python3 extract_figure.py <pdf-path> <out-png> --margin 24         # top/bottom margin
    python3 extract_figure.py <pdf-path> <out-png> --page 2            # render page N

Dependencies:
    pillow            (always required)
    pymupdf           (preferred; cross-platform; install with `pip install pymupdf` or `uv sync`)
    qlmanage          (optional; macOS shortcut for page 1)
    pdftoppm          (optional; from `brew install poppler`)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _check_dependencies() -> None:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        sys.exit("error: Pillow not installed. Run: uv sync  (or: pip install pillow)")


def _render_page(pdf: Path, page: int, size: int, prefer: str = "auto") -> Path:
    """Render a single page of the PDF to PNG. Returns path.

    Backend selection (in order):
      1. PyMuPDF (fitz) — cross-platform, works for any page, no system deps.
      2. qlmanage      — macOS-only shortcut for page 1 (very fast).
      3. pdftoppm      — from poppler, works for any page.

    `prefer` may be "auto" (default), "pymupdf", "qlmanage", or "pdftoppm".
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="extract_figure_"))

    backends = []
    if prefer == "pymupdf":
        backends = ["pymupdf"]
    elif prefer == "qlmanage":
        backends = ["qlmanage", "pymupdf", "pdftoppm"]
    elif prefer == "pdftoppm":
        backends = ["pdftoppm", "pymupdf"]
    else:  # auto: PyMuPDF first (cross-platform), then macOS shortcut for page 1, then poppler.
        backends = ["pymupdf", "qlmanage", "pdftoppm"]

    last_err = None
    for backend in backends:
        if backend == "qlmanage" and (page != 1 or shutil.which("qlmanage") is None):
            continue
        if backend == "pdftoppm" and shutil.which("pdftoppm") is None:
            continue
        try:
            if backend == "pymupdf":
                import fitz  # type: ignore
                doc = fitz.open(str(pdf))
                if page > doc.page_count:
                    sys.exit(f"page {page} > total pages {doc.page_count}")
                pdf_page = doc[page - 1]
                # 11-inch tall page * 72 dpi = 792px at zoom=1; aim for `size` px tall.
                zoom = (size / 11) / 72.0
                import fitz as _fitz  # type: ignore
                mat = _fitz.Matrix(zoom, zoom)
                pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
                out = tmpdir / f"page-{page}.png"
                pix.save(out)
                doc.close()
                return out
            if backend == "qlmanage":
                subprocess.run(
                    ["qlmanage", "-t", "-s", str(size), "-o", str(tmpdir), str(pdf)],
                    capture_output=True, check=True,
                )
                pngs = list(tmpdir.glob("*.png"))
                if not pngs:
                    raise RuntimeError("qlmanage produced no PNG")
                return pngs[0]
            if backend == "pdftoppm":
                dpi = max(120, min(300, size // 11))
                out_prefix = tmpdir / "page"
                subprocess.run(
                    ["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi),
                     "-png", str(pdf), str(out_prefix)],
                    capture_output=True, check=True,
                )
                pngs = list(tmpdir.glob("page-*.png"))
                if not pngs:
                    raise RuntimeError("pdftoppm produced no PNG")
                return pngs[0]
        except (ImportError, RuntimeError, subprocess.CalledProcessError) as e:
            last_err = e
            continue

    sys.exit(
        "error: no PDF render backend available. "
        "Install PyMuPDF (`uv sync` in this repo, or `pip install pymupdf`), "
        f"or `brew install poppler`. Last error: {last_err}"
    )


def _row_density(img, x0: int, x1: int, y: int, h: int, threshold: int = 240) -> int:
    """Count non-white pixels in a horizontal strip [y..y+h], columns [x0..x1]."""
    strip = img.crop((x0, y, x1, y + h)).convert("L")
    return sum(1 for p in strip.getdata() if p < threshold)


def _find_blocks(
    img, x0: int, x1: int,
    step: int = 8, blank_run: int = 40, blank_threshold: int = 100,
) -> list[tuple[int, int, int]]:
    """Find content blocks separated by blank vertical runs.

    Returns list of (top, bottom, total_density) tuples.
    A row is "blank" if its non-white pixel count is below `blank_threshold`.
    A "block" is a contiguous region of non-blank rows, separated from the
    next block by at least `blank_run` px of blank rows.
    """
    H = img.height
    samples = []
    for y in range(0, H - step, step):
        d = _row_density(img, x0, x1, y, step)
        samples.append((y, d))

    blocks = []
    in_block = False
    block_top = 0
    block_density = 0
    blank = 0

    for y, d in samples:
        is_blank = d < blank_threshold
        if not is_blank:
            if not in_block:
                block_top = y
                in_block = True
                block_density = 0
            block_density += d
            blank = 0
        else:
            if in_block:
                blank += step
                if blank >= blank_run:
                    blocks.append((block_top, y - blank, block_density))
                    in_block = False
    if in_block:
        blocks.append((block_top, H, block_density))

    return blocks


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--x-band", nargs=2, type=int, default=[100, 1750],
                   help="Column range to scan for content (default 100..1750).")
    p.add_argument("--first", action="store_true",
                   help="Take the first content block (default: largest by total density).")
    p.add_argument("--margin", type=int, default=24, help="Top/bottom padding to add (px).")
    p.add_argument("--size", type=int, default=2400, help="Render target height (px).")
    p.add_argument("--blank-run", type=int, default=24,
                   help="Blank-row run length to separate blocks (px). Lower = more granular.")
    p.add_argument("--min-height", type=int, default=80,
                   help="Ignore blocks shorter than this many px when choosing.")
    p.add_argument("--blank-threshold", type=int, default=100,
                   help="A row with non-white pixel count below this is considered 'blank'.")
    p.add_argument("--skip-top", type=int, default=380,
                   help="Pixels at top of page to skip (title/authors area). Default 380.")
    p.add_argument("--y-band", nargs=2, type=int, default=None,
                   help="Optional explicit y-range (y0 y1) overriding auto-detection.")
    p.add_argument("--caption-gap", type=int, default=80,
                   help="Max gap (px) between figure block and a caption block to merge.")
    p.add_argument("--caption-max-height", type=int, default=300,
                   help="Max height (px) of a block to be considered a caption.")
    p.add_argument("--page", type=int, default=1,
                   help="PDF page to render (1-indexed).")
    p.add_argument("--backend", choices=["auto", "pymupdf", "qlmanage", "pdftoppm"],
                   default=os.environ.get("PAPER_EXPLAINER_BACKEND", "auto"),
                   help="PDF rendering backend (default: auto, prefers PyMuPDF).")
    args = p.parse_args(argv[1:])

    _check_dependencies()
    from PIL import Image

    if not args.pdf.is_file():
        sys.exit(f"not a file: {args.pdf}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    page_png = _render_page(args.pdf, args.page, args.size, prefer=args.backend)
    img = Image.open(page_png)
    W, H = img.size
    print(f"rendered page: {W}x{H}", file=sys.stderr)

    x0, x1 = args.x_band
    x0 = max(0, x0)
    x1 = min(W, x1)

    if args.y_band:
        y0, y1 = args.y_band
    else:
        scan_img = img.crop((0, args.skip_top, W, H))
        blocks = _find_blocks(
            scan_img, x0, x1,
            blank_run=args.blank_run,
            blank_threshold=args.blank_threshold,
        )
        blocks = [(t + args.skip_top, b + args.skip_top, d) for (t, b, d) in blocks]
        if not blocks:
            sys.exit("no content blocks found")
        big_blocks = [b for b in blocks if (b[1] - b[0]) >= args.min_height]
        if not big_blocks:
            big_blocks = blocks
        if args.first:
            chosen = big_blocks[0]
        else:
            chosen = max(big_blocks, key=lambda b: b[2])
        chosen_idx = blocks.index(chosen)

        # Caption-merge heuristic, both directions:
        # 1) Block AFTER the figure that's short and close = below-figure caption.
        # 2) Block BEFORE the figure that's short and close = above-figure caption
        #    (some papers, e.g. ICML/CVPR, sometimes place the title/caption above the panel).
        if chosen_idx + 1 < len(blocks):
            nxt = blocks[chosen_idx + 1]
            gap = nxt[0] - chosen[1]
            next_h = nxt[1] - nxt[0]
            if gap < args.caption_gap and next_h < args.caption_max_height:
                print(f"  merging caption block (below) y={nxt[0]}..{nxt[1]} (gap={gap}, h={next_h})",
                      file=sys.stderr)
                chosen = (chosen[0], nxt[1], chosen[2] + nxt[2])

        if chosen_idx - 1 >= 0:
            prv = blocks[chosen_idx - 1]
            gap = chosen[0] - prv[1]
            prv_h = prv[1] - prv[0]
            if gap < args.caption_gap and prv_h < args.caption_max_height:
                print(f"  merging caption block (above) y={prv[0]}..{prv[1]} (gap={gap}, h={prv_h})",
                      file=sys.stderr)
                chosen = (prv[0], chosen[1], chosen[2] + prv[2])

        y0, y1 = chosen[0], chosen[1]
        print(f"detected blocks: {[(t,b,d) for t,b,d in blocks]}", file=sys.stderr)
        print(f"chose block: y={y0}..{y1} (density={chosen[2]})", file=sys.stderr)

    y0 = max(0, y0 - args.margin)
    y1 = min(H, y1 + args.margin)

    crop = img.crop((x0, y0, x1, y1))
    crop.save(args.out, optimize=True)
    print(f"wrote {args.out} ({crop.size[0]}x{crop.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
