"""Media the Superhive store page needs because its sanitizer strips the CSS that made them (README in
docs/store/superhive/). Writes, all web-optimised:

  docs/assets/media/store/gif-live-mode.mp4, gif-ring-menu.mp4   the two drawn GIFs as H.264 loops (<video> plays
                                                                   them; the -still.png posters already exist)
  docs/assets/img/store/hero-color-tilt.png, hero-brushes-tilt.png the hero accents with the rotation and drop shadow
                                                                   that transform / filter used to draw
  docs/assets/img/store/grid-bg.png                                the faint blueprint grid behind some sections
                                                                   (background-size is stripped, so no CSS grid)

    py -3.10 docs/_design/make_superhive_media.py [--ffmpeg C:/ffmpeg/bin/ffmpeg]

Needs Pillow and ffmpeg. Prints the hero placement for page.src.html (the tilted art keeps the original's centre).
"""
from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
IMG = DOCS / "assets" / "img" / "store"
MEDIA = DOCS / "assets" / "media" / "store"

# the hero stage from 560 px (the store column is 832): box in % of the stage width (left/width) and height (top)
STAGE_W, STAGE_RATIO = 768, 880 / 1000          # stage width at the 832 column; height / width
TILTS = {
    # name: (css rotate in deg, left %, top %, width %, drop-shadow y px, blur px, alpha)
    "hero-color": (-4, 2.0, 66.0, 17.0, 12, 18, 0.6),
    "hero-brushes": (3, 17.0, 80.0, 19.0, 12, 18, 0.6),
}


def mp4(ffmpeg: str, src: Path, dst: Path) -> None:
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(src),
                    "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2,fps=30,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-movflags", "+faststart", "-an", str(dst)],
                   check=True)


def tilt(name: str, rot: float, left: float, top: float, width: float, dy: float, blur: float, alpha: float) -> None:
    src = Image.open(IMG / f"{name}.png").convert("RGBA")
    ow, oh = src.size
    shown = width / 100 * STAGE_W                    # CSS px the box is drawn at
    k = ow / shown                                   # source px per CSS px
    big = src.rotate(-rot, resample=Image.Resampling.BICUBIC, expand=True)    # CSS rotate() is clockwise
    pad = int(math.ceil((dy + blur * 1.5) * k))
    canvas = Image.new("RGBA", (big.width + 2 * pad, big.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", canvas.size, 0)
    a.paste(big.getchannel("A"), (pad, pad + int(round(dy * k))))
    a = a.filter(ImageFilter.GaussianBlur(blur / 2 * k)).point(lambda v: int(v * alpha))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(a)
    canvas = Image.alpha_composite(canvas, shadow)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(big, (pad, pad))
    canvas = Image.alpha_composite(canvas, layer)
    nw, nh = canvas.size
    # 2x the size it's shown at in the 832 column
    target = int(round(shown * nw / ow * 2))
    out = canvas.resize((target, int(round(target * nh / nw))), Image.Resampling.LANCZOS)
    dst = IMG / f"{name}-tilt.png"
    out.save(dst, optimize=True)
    # placement: same centre as the untransformed box
    wn = width * nw / ow
    h_pct = width * (oh / ow) / STAGE_RATIO          # box height in % of the stage height
    hn_pct = wn * (nh / nw) / STAGE_RATIO
    cx, cy = left + width / 2, top + h_pct / 2
    print(f"{dst.name}: {out.size[0]}x{out.size[1]}, {dst.stat().st_size:,} B -> "
          f"left:{cx - wn / 2:.2f}%;top:{cy - hn_pct / 2:.2f}%;width:{wn:.2f}%")


def grid() -> None:
    """Major lines every 120 px (4.5 % white), minor every 24 px (1.8 %), faded by an ellipse 70 % x 60 % at
    50 % 40 % (opaque to 30 %, gone at 75 %): the site's .fs-gridbg."""
    w, h = 1600, 1100
    lines = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(lines)
    ox = (w // 2) % 120                              # a major line through the centre
    for x in range(ox % 24, w, 24):
        d.line([(x, 0), (x, h)], fill=5 if (x - ox) % 120 else 11)
    for y in range(0, h, 24):
        d.line([(0, y), (w, y)], fill=5 if y % 120 else 11)
    # redraw majors on top so crossings keep the major alpha
    for x in range(ox, w, 120):
        d.line([(x, 0), (x, h)], fill=11)
    for x in range(ox - 120, -1, -120):
        d.line([(x, 0), (x, h)], fill=11)
    for y in range(0, h, 120):
        d.line([(0, y), (w, y)], fill=11)
    mask = Image.new("L", (w, h), 0)
    px = mask.load()
    rx, ry, cx, cy = 0.7 * w, 0.6 * h, 0.5 * w, 0.4 * h
    for y in range(h):
        for x in range(w):
            r = math.hypot((x - cx) / rx, (y - cy) / ry)
            t = 1.0 if r <= 0.3 else 0.0 if r >= 0.75 else 1 - (r - 0.3) / 0.45
            px[x, y] = int(255 * t)
    a = ImageChops.multiply(lines, mask)
    img = Image.merge("LA", (Image.new("L", (w, h), 255), a))      # white, grey + alpha PNG
    dst = IMG / "grid-bg.png"
    img.save(dst, optimize=True)
    print(f"{dst.name}: {w}x{h}, {dst.stat().st_size:,} B")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ffmpeg", default="C:/ffmpeg/bin/ffmpeg")
    args = ap.parse_args()
    for name in ("gif-live-mode", "gif-ring-menu"):
        dst = MEDIA / f"{name}.mp4"
        mp4(args.ffmpeg, IMG / f"{name}.gif", dst)
        print(f"{dst.name}: {dst.stat().st_size:,} B")
    for name, spec in TILTS.items():
        tilt(name, *spec)
    grid()


if __name__ == "__main__":
    main()
