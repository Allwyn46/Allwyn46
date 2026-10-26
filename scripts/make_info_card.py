#!/usr/bin/env python3
"""Hand-author a neofetch-style info card SVG from profile.json.

Title bar, a coloured user@host line, then key/value rows that fade in line by line.
Keep the story here (role, stack, highlights) - the heatmap already covers GitHub stats.

Usage: python scripts/make_info_card.py [profile.json] [out.svg]
Env:   STATIC=1 -> frozen frame for local previews
"""
import json
import os
import sys
import textwrap
from xml.sax.saxutils import escape

STATIC = os.environ.get("STATIC") == "1"
W = 490
PAD = 22
LH = 22
BAR = 36
KEY_X, VAL_X = PAD, PAD + 112
WRAP = 42                      # value characters per line
STAGGER = 0.12

PANEL, STROKE = "#0d1117", "#30363d"
C_TITLE, C_KEY, C_VAL, C_DIM = "#39d353", "#58a6ff", "#c9d1d9", "#8b949e"
KEY_COLORS = ["#58a6ff", "#d2a8ff", "#ffa657", "#7ee787", "#ff7b72", "#79c0ff"]


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "profile.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "info-card.svg"
    with open(cfg_path, encoding="utf-8") as f:
        card = json.load(f)["info_card"]

    title, rows = card["title"], card["rows"]

    body = []   # (kind, x, text, colour, extra)
    y = BAR + PAD + 8
    items = []
    items.append((y, [("text", KEY_X, title, C_TITLE, True)]))
    y += LH
    items.append((y, [("text", KEY_X, "─" * len(title), C_DIM, False)]))
    y += LH
    for i, (key, value) in enumerate(rows):
        color = KEY_COLORS[i % len(KEY_COLORS)]
        wrapped = textwrap.wrap(value, WRAP) or [""]
        for j, seg in enumerate(wrapped):
            line = []
            if j == 0:
                line.append(("text", KEY_X, key, color, True))
            line.append(("text", VAL_X, seg, C_VAL, False))
            items.append((y, line))
            y += LH
    H = y + PAD - 6

    css = "" if STATIC else (
        ".l{opacity:0;animation:in .5s ease-out forwards}"
        "@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Profile info card">',
        f"<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;font-size:14px;white-space:pre}}{css}</style>",
        f'<rect width="{W}" height="{H}" rx="10" fill="{PANEL}" stroke="{STROKE}"/>',
        f'<path d="M0 10a10 10 0 0 1 10-10h{W - 20}a10 10 0 0 1 10 10v{BAR - 10}H0z" fill="#161b22"/>',
        f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="{STROKE}"/>',
        '<circle cx="20" cy="18" r="5.5" fill="#ff5f56"/><circle cx="40" cy="18" r="5.5" fill="#ffbd2e"/><circle cx="60" cy="18" r="5.5" fill="#27c93f"/>',
        f'<text x="{W / 2}" y="23" text-anchor="middle" fill="{C_DIM}" style="font-size:12px">neofetch</text>',
    ]
    for n, (ly, parts) in enumerate(items):
        style = "" if STATIC else f' style="animation-delay:{0.3 + n * STAGGER:.2f}s"'
        cls = "" if STATIC else ' class="l"'
        svg.append(f"<g{cls}{style}>")
        for _, x, text, color, bold in parts:
            weight = ' font-weight="700"' if bold else ""
            svg.append(f'<text x="{x}" y="{ly}" fill="{color}"{weight}>{escape(text)}</text>')
        svg.append("</g>")
    svg.append("</svg>")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"wrote {out} ({W}x{H})")


if __name__ == "__main__":
    main()
