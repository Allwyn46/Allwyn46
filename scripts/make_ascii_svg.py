#!/usr/bin/env python3
"""Turn source-prepped.png into a self-typing, monochrome ASCII portrait SVG.

Each row is revealed by a left-to-right clip wipe (a block cursor rides the edge),
staggered top to bottom. It plays once and freezes. Pure SMIL, so GitHub plays it.

Usage: python scripts/make_ascii_svg.py [source-prepped.png] [out.svg]
Env:   STATIC=1 -> fully drawn frame (for local previews)
"""
import os
import sys
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

COLS = 100            # characters per row
CW, LH = 4.2, 7.0     # char cell width / line height (px) -> 0.6 aspect, like a monospace font
FONT_SIZE = 7
PAD = 14
FILL = "#c9d1d9"      # one light-gray colour: monochrome looks clean, rainbow looks like static
PANEL, STROKE = "#0d1117", "#30363d"
# sparse -> dense. On a dark panel, bright pixels should print dense glyphs.
RAMP = " .`:-=+*cs#%@"
BG_LEVEL = 252        # prep_photo.py keeps the subject <= 250, so >= 252 means background
ROW_STAGGER, ROW_DUR = 0.045, 0.45
STATIC = os.environ.get("STATIC") == "1"


def resize_f(a: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize(size, Image.LANCZOS))


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "avi-ascii.svg"

    img = np.asarray(Image.open(src).convert("L"), dtype=np.float32)
    h, w = img.shape
    rows = max(1, round(COLS * (h / w) * (CW / LH)))

    # resize subject and background separately so the edge doesn't grow a dense halo
    subject = (img < BG_LEVEL).astype(np.float32)
    cov = resize_f(subject, (COLS, rows))
    gray = resize_f(img * subject, (COLS, rows)) / np.maximum(cov, 1e-3)

    live = cov > 0.5
    if live.any():
        lo, hi = np.percentile(gray[live], [2, 98])
        gray = np.clip((gray - lo) / max(hi - lo, 1.0), 0, 1)
    idx = np.clip((gray * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)

    lines = ["".join(RAMP[idx[r, c]] if live[r, c] else " " for c in range(COLS)) for r in range(rows)]

    W, H = COLS * CW, rows * LH
    total_w, total_h = W + 2 * PAD, H + 2 * PAD
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.1f} {total_h:.1f}" '
        f'width="{total_w:.0f}" height="{total_h:.0f}" role="img" aria-label="ASCII portrait">',
        f'<rect width="{total_w:.1f}" height="{total_h:.1f}" rx="10" fill="{PANEL}" stroke="{STROKE}"/>',
        "<defs>",
    ]
    delay = 0.4
    timings = []
    for i, line in enumerate(lines):
        if not line.strip():
            timings.append(None)
            continue
        y = PAD + i * LH
        d = delay + i * ROW_STAGGER
        timings.append(d)
        width_attr = f'width="{W:.1f}"' if STATIC else 'width="0"'
        anim = "" if STATIC else (
            f'<animate attributeName="width" from="0" to="{W:.1f}" begin="{d:.3f}s" '
            f'dur="{ROW_DUR}s" fill="freeze"/>'
        )
        parts.append(f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" {width_attr} height="{LH}">{anim}</rect></clipPath>')
    parts.append("</defs>")

    parts.append(f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
                 f'font-size="{FONT_SIZE}" fill="{FILL}" xml:space="preserve">')
    for i, line in enumerate(lines):
        if timings[i] is None:
            continue
        y = PAD + i * LH
        parts.append(
            f'<text x="{PAD}" y="{y + LH - 1.5:.1f}" textLength="{W:.1f}" lengthAdjust="spacing" '
            f'clip-path="url(#r{i})">{escape(line)}</text>'
        )
        if not STATIC:
            d = timings[i]
            parts.append(
                f'<rect x="{PAD}" y="{y:.1f}" width="{CW}" height="{LH}" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{d:.3f}s"/>'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + W:.1f}" begin="{d:.3f}s" dur="{ROW_DUR}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{d + ROW_DUR:.3f}s"/></rect>'
            )
    parts.append("</g></svg>")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"wrote {out}: {COLS}x{rows} chars")


if __name__ == "__main__":
    main()
