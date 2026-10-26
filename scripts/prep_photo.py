#!/usr/bin/env python3
"""Prep a photo for ASCII conversion (run once per photo, locally).

1. remove the background (rembg)
2. boost local contrast (OpenCV CLAHE) so a flatly-lit face gets real highlights/shadows
3. composite onto pure white so the background becomes "blank" in the ASCII step

Usage: python scripts/prep_photo.py my-photo.jpg [source-prepped.png]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/prep_photo.py <photo> [out.png]")
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("source-prepped.png")

    cut = np.array(remove(Image.open(src).convert("RGB")).convert("RGBA"))

    # crop tightly around the subject so it fills the character grid
    ys, xs = np.where(cut[..., 3] > 16)
    if len(xs) == 0:
        sys.exit("No subject found - try a clearer photo.")
    pad = int(0.04 * max(cut.shape[:2]))
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, cut.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, cut.shape[1])
    cut = cut[y0:y1, x0:x1]

    alpha = cut[..., 3:4].astype(np.float32) / 255.0
    gray = cv2.cvtColor(cut[..., :3], cv2.COLOR_RGB2GRAY)
    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    # keep the subject strictly below pure white so 255 always means "background"
    gray = np.minimum(gray, 250).astype(np.float32)

    flat = gray * alpha + 255.0 * (1.0 - alpha)
    Image.fromarray(flat.astype(np.uint8), "L").save(out)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
