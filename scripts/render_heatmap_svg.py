#!/usr/bin/env python3
"""Render data/contributions.json as the classic 53-week x 7-day calendar SVG.

Rounded boxes slide in diagonally once (CSS keyframes, play on load, then freeze).
Legend (Less -> More) + a stats footer. No looping glow.

Usage: python scripts/render_heatmap_svg.py [data/contributions.json] [contrib-heatmap.svg]
Env:   STATIC=1 -> frozen frame for local previews
"""
import json
import os
import sys
from datetime import date, timedelta
from xml.sax.saxutils import escape

STATIC = os.environ.get("STATIC") == "1"
# none -> brightest (level 5 is a neon top end for your busiest days)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
PANEL, STROKE, DIM = "#0d1117", "#30363d", "#8b949e"
CELL, GAP = 12, 3
P = CELL + GAP
LEFT, TOP = 44, 58
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "data/contributions.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    days = data["days"]
    first = date.fromisoformat(days[0]["date"])
    first_col_start = first - timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday

    # level 5 = the busiest slice of level-4 days
    top = sorted(d["count"] for d in days if d["level"] == 4)
    neon_from = top[int(len(top) * 0.75)] if top else 10**9

    cells, month_marks, last_month, last_mark_col = [], [], None, -9
    ncols = 0
    for d in days:
        dt = date.fromisoformat(d["date"])
        col = (dt - first_col_start).days // 7
        row = (dt.weekday() + 1) % 7
        ncols = max(ncols, col + 1)
        level = d["level"]
        if level == 4 and d["count"] >= neon_from and d["count"] > 0:
            level = 5
        cells.append((col, row, level))
        if dt.day <= 7 and dt.month != last_month and col - last_mark_col >= 3:
            month_marks.append((col, MONTHS[dt.month - 1]))
            last_month, last_mark_col = dt.month, col
        elif last_month is None:
            last_month = dt.month

    W = LEFT + ncols * P + 18
    H = TOP + 7 * P + 52
    css = "" if STATIC else (
        ".c{opacity:0;animation:pop .45s ease-out forwards}"
        "@keyframes pop{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}"
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub contribution heatmap">',
        f"<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;font-size:11px;fill:{DIM}}}{css}</style>",
        f'<rect width="{W}" height="{H}" rx="10" fill="{PANEL}" stroke="{STROKE}"/>',
        f'<path d="M0 10a10 10 0 0 1 10-10h{W - 20}a10 10 0 0 1 10 10v16H0z" fill="#161b22"/>',
        f'<line x1="0" y1="26" x2="{W}" y2="26" stroke="{STROKE}"/>',
        '<circle cx="16" cy="13" r="4.5" fill="#ff5f56"/><circle cx="32" cy="13" r="4.5" fill="#ffbd2e"/><circle cx="48" cy="13" r="4.5" fill="#27c93f"/>',
        f'<text x="{W / 2}" y="17" text-anchor="middle">contributions.sh</text>',
    ]
    for col, name in month_marks:
        svg.append(f'<text x="{LEFT + col * P}" y="{TOP - 10}">{name}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        svg.append(f'<text x="10" y="{TOP + row * P + 10}">{name}</text>')

    for col, row, level in cells:
        style = "" if STATIC else f' style="animation-delay:{0.25 + col * 0.018 + row * 0.05:.3f}s"'
        cls = "" if STATIC else ' class="c"'
        svg.append(
            f'<rect{cls} x="{LEFT + col * P}" y="{TOP + row * P}" width="{CELL}" height="{CELL}" rx="3" fill="{PALETTE[level]}"{style}/>'
        )

    fy = TOP + 7 * P + 24
    stats = (f"{data['total']:,} contributions in the last year  ·  "
             f"streak {data['current_streak']}d  ·  longest {data['longest_streak']}d  ·  "
             f"best day {data['best_day']['count']}")
    svg.append(f'<text x="{LEFT}" y="{fy}">{escape(stats)}</text>')

    lx = W - 18 - (len(PALETTE) * 15 + 70)
    ly = fy + 20
    svg.append(f'<text x="{lx}" y="{ly}">Less</text>')
    for i, color in enumerate(PALETTE):
        svg.append(f'<rect x="{lx + 32 + i * 15}" y="{ly - 10}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"/>')
    svg.append(f'<text x="{lx + 32 + len(PALETTE) * 15 + 4}" y="{ly}">More</text>')
    svg.append("</svg>")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"wrote {out} ({W}x{H}, {len(cells)} cells)")


if __name__ == "__main__":
    main()
