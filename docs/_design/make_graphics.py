"""Regenerate the FlexSpace marketing graphics in docs/assets/img/.

    py -3.10 docs/_design/make_graphics.py            # everything
    py -3.10 docs/_design/make_graphics.py hero cards # only some groups

Groups: hero, cards, gallery, widgets, frames, focus, icons, brand (scenes are drawn on demand).

frame-<name>: a whole scene in a window (docs pages, lightbox). focus-<name>: a tight crop of the part that tells
the story, sized so its UI text reads at the width the site shows it (feature rows, bento, store rows).

The product UI is redrawn with Pillow + numpy as illustrations from the curated screenshots
(B3D-MySpace/marketing/flexspace), which are the reference for those. The exception is the Armature Picker: its
character-art pages are real captures of the redesigned picker (picker_layer_*.png, picker_hero.png), cropped and
composed into the scenes (real()). The only brand asset used as-is is the wordmark
(docs/_design/brand/FlexSpace.svg, parsed here).

Every image placed inside another is cover-cropped to its box and scaled uniformly (cover()); Image.resize is
guarded for the whole run, and the run fails if any resize or placement changes an image's aspect (check_aspect()).

Outputs (see graphics.json for the full list with alt text):
  assets/img/<name>.webp          for GitHub Pages
  assets/img/store/<name>.jpg|png for Superhive (no WebP there)
  assets/img/icons/...            favicon set and the F mark

Picker art: real captures of the redesigned picker, alternating the Adult Male and Adult Female charts
(picker_page(), picker_figure()). Set FLEXSPACE_MEDIA_SRC to the marketing/flexspace folder if it is not next to
this repo.
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

RS = getattr(Image, "Resampling", Image)
HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
OUT = DOCS / "assets" / "img"
STORE = OUT / "store"
ICONS = OUT / "icons"
BRAND_SVG = HERE / "brand" / "FlexSpace.svg"
SITE = "https://jfranmatheu.github.io/flexspace/"
REAL_SRC = Path(os.environ.get("FLEXSPACE_MEDIA_SRC") or DOCS.parent.parent / "B3D-MySpace" / "marketing" / "flexspace")

# ---- aspect guard: nothing in a composed graphic may be squashed or stretched
_resize = Image.Image.resize
ASPECT = {"resizes": 0, "bad": [], "placed": []}


def _guarded_resize(self, size, *a, **kw):
    (w0, h0), (w1, h1) = self.size, tuple(size)
    if w0 and h0 and w1 and h1:
        ASPECT["resizes"] += 1
        sx, sy = w1 / w0, h1 / h0
        tol = 1 / min(w1, h1) + 1 / min(w0, h0) + .002     # rounding to whole pixels, nothing more
        if abs(sx - sy) / max(sx, sy) > tol:
            import traceback
            fr = [f for f in traceback.extract_stack()[:-1] if f.filename.endswith("make_graphics.py")]
            where = f"line {fr[-1].lineno} ({fr[-1].name})" if fr else "?"
            ASPECT["bad"].append(f"resize {w0}x{h0} -> {w1}x{h1} at {where}")
    return _resize(self, size, *a, **kw)


Image.Image.resize = _guarded_resize


def cover(im, w, h, focus=(.5, .5), what=""):
    """im scaled uniformly to cover a w x h box, the overflow cropped around focus (0..1 of the spare room).
    The only way an image is fitted into a box here: it never squashes."""
    W, Hh = im.size
    if W / Hh > w / h:
        cw, ch = Hh * w / h, Hh
    else:
        cw, ch = W, W * h / w
    x0 = (W - cw) * min(max(focus[0], 0), 1)
    y0 = (Hh - ch) * min(max(focus[1], 0), 1)
    box = (round(x0), round(y0), round(x0 + cw), round(y0 + ch))
    out = im.crop(box).resize((w, h), RS.LANCZOS)
    ASPECT["placed"].append((what or "image", (W, Hh), box, (w, h)))
    return out


def check_aspect():
    """Fail the run if any resize or placement changed an image's aspect (the presets thumbnails once did)."""
    bad = list(ASPECT["bad"])
    for what, src, (x0, y0, x1, y1), (w, h) in ASPECT["placed"]:
        a_crop, a_box = (x1 - x0) / (y1 - y0), w / h
        if abs(a_crop / a_box - 1) > 1 / min(w, h) + 1 / min(x1 - x0, y1 - y0) + .002:
            bad.append(f"{what}: crop {x1 - x0}x{y1 - y0} of {src[0]}x{src[1]} placed in {w}x{h}")
    print(f"aspect check: {ASPECT['resizes']} resizes, {len(ASPECT['placed'])} placed images, {len(bad)} distorted")
    for what, src, box, size in ASPECT["placed"]:
        print(f"  placed {what}: {box[2] - box[0]}x{box[3] - box[1]} of {src[0]}x{src[1]} -> {size[0]}x{size[1]}")
    for b in bad:
        print("  DISTORTED", b)
    if bad:
        raise SystemExit("aspect check failed")


_REAL: dict = {}


def real(rel):
    """A real capture from the marketing folder (RGB)."""
    if rel not in _REAL:
        p = REAL_SRC / rel
        if not p.is_file():
            raise SystemExit(f"missing real capture {p} (set FLEXSPACE_MEDIA_SRC to marketing/flexspace)")
        with Image.open(p) as im:
            _REAL[rel] = im.convert("RGB")
    return _REAL[rel]


def picker_page(gender="female", page="body"):
    """A whole page of the Humanoid Body chart in Live Mode (Adult Male / Adult Female), a 1x capture."""
    return real(f"shots/picker_layer_{gender}_{page}.png")


# the body figure on each Body page (source px): head to the root bar, both IK hands, their pucks and the bone name
PICKER_FIGURE = {"female": (365, 40, 945, 985), "male": (278, 60, 998, 985)}
# bone pickers at a glance (female Body page): the selected hips, arm and thigh bars, both IK diamonds and pucks
PICKER_BONES_BOX = (425, 360, 945, 649)
# the Rigify Character Picker demo's picker editor in picker_hero.png (male art, panels, tabs)
PICKER_HERO_EDITOR = (818, 56, 1920, 1056)


def picker_figure(gender):
    return picker_page(gender).crop(PICKER_FIGURE[gender])
REGISTRY: list[dict] = []


# ------------------------------------------------------------------------------------------------ colour
def H(h: str, a: int | None = None):
    h = h.lstrip("#")
    c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return c + (a,) if a is not None else c


def A(c, a):
    """Colour c with alpha a (0-255)."""
    return tuple(c[:3]) + (int(a),)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


GOLD = H("#F0B557")
GOLD_HOT = H("#D18A2E")
SAND = H("#DCCEB8")
MIST = H("#D5D6D8")
BLUE = H("#2F6FFF")
BLUE_400 = H("#5B8CFF")
INK = H("#0A0A0C")
TEXT1 = H("#F4F2EE")
TEXT2 = H("#B6B3AD")
TEXT3 = H("#85827C")
BRAND_STOPS = [(0, H("#F0B557")), (.18, H("#EDB967")), (.40, H("#E6C187")), (.62, H("#DFCAA8")),
               (.82, H("#D8D2C8")), (1, H("#D5D6D8"))]
# Picker sides (DESIGN.md): left blue, right red, centre yellow, root purple.
SIDE_L, SIDE_R, SIDE_C, SIDE_ROOT = H("#4C8DFF"), H("#FF5A5F"), H("#F2C94C"), H("#A77BFF")

# The add-on's own widget themes, as the reference shots show them.
DARK = dict(canvas=H("#1c1c1d"), dot=H("#303033"), panel=H("#212123"), panel_line=H("#353538"),
            text=H("#e8e8ea"), dim=H("#9c9ca2"), field=H("#2b2b2e"), field_line=H("#3d3d41"),
            btn=H("#2e2e31"), btn_line=H("#46464b"), seg=H("#262629"), seg_on=H("#424247"),
            track=H("#3d3d42"), off=H("#4a4a50"), knob=H("#f6f6f7"), accent=H("#3478F6"),
            on_text=H("#ffffff"), guide=H("#ff4fa3"))
SUNSET = dict(DARK, accent=H("#F2751F"))
VIOLET = dict(DARK, accent=H("#8B5CF6"))
LIGHT = dict(canvas=H("#d4d4d7"), dot=H("#bdbdc2"), panel=H("#f4f4f5"), panel_line=H("#c6c6cb"),
             text=H("#1d1d20"), dim=H("#6c6c73"), field=H("#e7e7ea"), field_line=H("#c4c4ca"),
             btn=H("#ececee"), btn_line=H("#c0c0c6"), seg=H("#e1e1e5"), seg_on=H("#ffffff"),
             track=H("#c6c6cc"), off=H("#b9b9c0"), knob=H("#ffffff"), accent=H("#3478F6"),
             on_text=H("#ffffff"), guide=H("#ff4fa3"))


# ------------------------------------------------------------------------------------------------ fonts
FONT_DIRS = [HERE / "fonts", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
             Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path.home() / ".local/share/fonts",
             Path("/usr/share/fonts/truetype/inter"), Path("/Library/Fonts")]


def _find_font(*names):
    for d in FONT_DIRS:
        for n in names:
            if (d / n).exists():
                return d / n
    return None


INTER = _find_font("Inter-VariableFont_slnt,wght.ttf", "InterVariable.ttf")
MONO = _find_font("RobotoMono-VariableFont_wght.ttf", "JetBrainsMono-Medium.ttf", "consola.ttf")
SEGOE = {300: "segoeuil.ttf", 400: "segoeui.ttf", 600: "seguisb.ttf", 700: "segoeuib.ttf", 900: "seguibl.ttf"}
_FC: dict = {}


def font(px, w=400, mono=False):
    px = max(1, int(round(px)))
    key = (px, w, mono)
    if key in _FC:
        return _FC[key]
    path = MONO if mono else INTER
    if path is None:
        best = min(SEGOE, key=lambda k: abs(k - w))
        path = _find_font(SEGOE[best]) or _find_font("DejaVuSans.ttf")
    f = ImageFont.truetype(str(path), px)
    try:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([w] + [ax["default"] for ax in axes[1:]])
    except Exception:
        pass
    _FC[key] = f
    return f


# ------------------------------------------------------------------------------------------------ drawing
class Pic:
    """An opaque surface in logical units (UI pixels), supersampled for clean edges.

    Logical (x, y) -> pixels (x * scale * ss). out() gives the image at scale."""

    def __init__(self, w, h, scale=1.0, bg=DARK["canvas"], ss=3):
        self.w, self.h, self.scale, self.ss = w, h, scale, ss
        self.k = scale * ss
        self.im = Image.new("RGB", (round(w * self.k), round(h * self.k)), bg[:3])
        self.d = ImageDraw.Draw(self.im, "RGBA")

    # geometry -------------------------------------------------------------------------------------
    def box(self, x, y, w, h):
        k = self.k
        return [x * k, y * k, (x + w) * k - 1, (y + h) * k - 1]

    def rrect(self, x, y, w, h, r=6, fill=None, line=None, lw=1.0):
        r = max(0, min(r, w / 2, h / 2))
        self.d.rounded_rectangle(self.box(x, y, w, h), radius=r * self.k, fill=fill, outline=line,
                                 width=max(1, round(lw * self.k)) if line else 0)

    def circle(self, cx, cy, r, fill=None, line=None, lw=1.0):
        k = self.k
        self.d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=fill, outline=line,
                       width=max(1, round(lw * k)) if line else 0)

    def ellipse(self, cx, cy, rx, ry, fill=None, line=None, lw=1.0):
        k = self.k
        self.d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=fill, outline=line,
                       width=max(1, round(lw * k)) if line else 0)

    def soft_shadow(self, x, y, w, h, r=8, blur=14, dy=8, alpha=120):
        """A blurred drop shadow under a rounded box (for menus and tooltips)."""
        k = self.k
        pad = int(blur * k * 2.5)
        m = Image.new("L", (int(w * k) + 2 * pad, int(h * k) + 2 * pad), 0)
        ImageDraw.Draw(m).rounded_rectangle([pad, pad, pad + w * k, pad + h * k], radius=r * k, fill=alpha)
        m = m.filter(ImageFilter.GaussianBlur(blur * k / 2))
        self.im.paste((0, 0, 0), (int(x * k) - pad, int((y + dy) * k) - pad), m)

    def line(self, pts, fill, lw=1.0, caps=True):
        k = self.k
        P = [(x * k, y * k) for x, y in pts]
        self.d.line(P, fill=fill, width=max(1, round(lw * k)), joint="curve")
        if caps and lw * k > 2:
            for x, y in (P[0], P[-1]):
                r = lw * k / 2
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def poly(self, pts, fill=None, line=None, lw=1.0):
        k = self.k
        P = [(x * k, y * k) for x, y in pts]
        self.d.polygon(P, fill=fill)
        if line:
            self.line(list(pts) + [pts[0]], line, lw, caps=False)

    def arc(self, cx, cy, r, a0, a1, fill, lw=2.0):
        """Arc in degrees, 0 = east, clockwise (Pillow's convention)."""
        k = self.k
        self.d.arc([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], a0, a1, fill=fill,
                   width=max(1, round(lw * k)))

    def soft_poly(self, pts, fill, round_r=4.0, line=None, lw=1.0):
        """A polygon with rounded corners (blur + threshold of its mask)."""
        k = self.k
        P = [(x * k, y * k) for x, y in pts]
        pad = int(round_r * k * 3 + lw * k * 2 + 4)
        x0, y0 = int(min(p[0] for p in P)) - pad, int(min(p[1] for p in P)) - pad
        x1, y1 = int(max(p[0] for p in P)) + pad, int(max(p[1] for p in P)) + pad
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in P], fill=255)
        if round_r > 0:
            m = m.filter(ImageFilter.GaussianBlur(round_r * k)).point(lambda v: 255 if v > 127 else 0)
        if line:
            n = max(3, int(round(lw * k)) * 2 + 1)
            g = m.filter(ImageFilter.MaxFilter(n))
            self._fill_mask(g, (x0, y0), line)
        self._fill_mask(m, (x0, y0), fill)

    def _fill_mask(self, m, at, color):
        a = color[3] if len(color) > 3 else 255
        if a < 255:
            m = m.point(lambda v: v * a // 255)
        self.im.paste(color[:3], (at[0], at[1], at[0] + m.width, at[1] + m.height), m)

    def text(self, x, y, s, size=12, w=400, fill=(230, 230, 230), anchor="lm", track=0.0, mono=False):
        k = self.k
        f = font(size * k, w, mono)
        if not track:
            self.d.text((x * k, y * k), s, font=f, fill=fill, anchor=anchor)
            return
        widths = [f.getlength(ch) + track * size * k for ch in s]
        total = sum(widths) - track * size * k
        X = x * k - (total / 2 if anchor[0] == "m" else total if anchor[0] == "r" else 0)
        for ch, cw in zip(s, widths):
            self.d.text((X, y * k), ch, font=f, fill=fill, anchor="l" + anchor[1])
            X += cw

    def tw(self, s, size=12, w=400):
        return font(size * self.k, w).getlength(s) / self.k

    def paste(self, img, x, y, w=None, h=None):
        k = self.k
        w = w or img.width / k
        h = h or img.height * w / img.width
        im = img.resize((max(1, round(w * k)), max(1, round(h * k))), RS.LANCZOS)
        if im.mode == "RGBA":
            self.im.paste(im.convert("RGB"), (round(x * k), round(y * k)), im)
        else:
            self.im.paste(im, (round(x * k), round(y * k)))

    def grad(self, x, y, w, h, c1, c2, r=0, vertical=True):
        k = self.k
        W, Hh = max(1, round(w * k)), max(1, round(h * k))
        t = np.linspace(0, 1, Hh if vertical else W, dtype=np.float32)
        c = np.array(c1, np.float32)[:3] + (np.array(c2, np.float32)[:3] - np.array(c1, np.float32)[:3]) * t[:, None]
        arr = np.broadcast_to(c[:, None, :], (Hh, W, 3)) if vertical else np.broadcast_to(c[None, :, :], (Hh, W, 3))
        im = Image.fromarray(np.ascontiguousarray(arr).astype(np.uint8), "RGB")
        mask = None
        if r:
            mask = Image.new("L", (W, Hh), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, Hh - 1], radius=r * k, fill=255)
        self.im.paste(im, (round(x * k), round(y * k)), mask)

    def dots(self, color, step=24, r=1.1, x0=0, y0=0, w=None, h=None):
        w = w or self.w
        h = h or self.h
        y = y0 + step / 2
        while y < y0 + h:
            x = x0 + step / 2
            while x < x0 + w:
                self.circle(x, y, r, fill=color)
                x += step
            y += step

    def out(self):
        return self.im.resize((round(self.w * self.scale), round(self.h * self.scale)), RS.LANCZOS)


# ------------------------------------------------------------------------------------------------ icons
def chev(p, cx, cy, s, d, col, lw=1.3):
    if d == "l":
        pts = [(cx + s / 2, cy - s), (cx - s / 2, cy), (cx + s / 2, cy + s)]
    elif d == "r":
        pts = [(cx - s / 2, cy - s), (cx + s / 2, cy), (cx - s / 2, cy + s)]
    else:
        pts = [(cx - s, cy - s / 2), (cx, cy + s / 2), (cx + s, cy - s / 2)]
    p.line(pts, col, lw)


def icon(p, name, cx, cy, s, col, lw=None):
    """Line icons in the spirit of Phosphor (the add-on's icon set), drawn in a box of side s."""
    lw = lw or max(1.0, s * 0.085)
    h = s / 2
    L = lambda pts: p.line([(cx + x * h, cy + y * h) for x, y in pts], col, lw)
    if name == "bolt":
        L([(.15, -1), (-.55, .1), (-.02, .1), (-.2, 1), (.55, -.15), (.02, -.15), (.15, -1)])
    elif name == "code":
        L([(-.35, -.6), (-.9, 0), (-.35, .6)]); L([(.35, -.6), (.9, 0), (.35, .6)]); L([(.15, -.85), (-.15, .85)])
    elif name == "grid":
        for ox, oy in ((-1, -1), (.12, -1), (-1, .12), (.12, .12)):
            p.rrect(cx + ox * h * .9, cy + oy * h * .9, h * .78, h * .78, h * .12, line=col, lw=lw)
    elif name == "eraser":
        L([(-.9, .55), (-.1, -.55), (.35, -.95), (.95, -.35), (.1, .65), (-.45, .65), (-.9, .55)])
        L([(-.45, -.1), (.35, .55)]); L([(.15, .85), (.95, .85)])
    elif name == "mirror":
        p.poly([(cx - .12 * h, cy - .85 * h), (cx - .12 * h, cy + .75 * h), (cx - .8 * h, cy + .75 * h)], line=col, lw=lw)
        p.poly([(cx + .12 * h, cy - .85 * h), (cx + .12 * h, cy + .75 * h), (cx + .8 * h, cy + .75 * h)], line=col, lw=lw)
    elif name == "topology":
        pts = [(-.7, .2), (-.15, -.7), (.6, -.45), (.75, .45), (-.05, .75)]
        L(pts + [pts[0]])
        for x, y in pts:
            p.circle(cx + x * h, cy + y * h, h * .17, fill=(30, 30, 32), line=col, lw=lw)
    elif name == "circles":
        p.circle(cx - .25 * h, cy - .2 * h, .55 * h, line=col, lw=lw)
        p.circle(cx + .25 * h, cy + .2 * h, .55 * h, line=col, lw=lw)
    elif name == "dashed":
        n = 4
        for i in range(n):
            a, b = -.85 + i * 1.7 / n + .08, -.85 + (i + 1) * 1.7 / n - .08
            L([(a, -.85), (b, -.85)]); L([(a, .85), (b, .85)]); L([(-.85, a), (-.85, b)]); L([(.85, a), (.85, b)])
    elif name == "halfcircle":
        p.circle(cx, cy, .85 * h, line=col, lw=lw)
        L([(0, -.85), (0, .85)])
        L([(.35, -.75), (.35, .75)])
    elif name == "panel":
        p.rrect(cx - .8 * h, cy - .85 * h, 1.6 * h, 1.7 * h, h * .12, line=col, lw=lw)
        L([(0, -.85), (0, .85)])
        for yy in (-.45, -.1, .25, .6):
            L([(.2, yy), (.6, yy)])
    elif name == "search":
        p.circle(cx - .15 * h, cy - .15 * h, .6 * h, line=col, lw=lw); L([(.3, .3), (.85, .85)])
    elif name == "plus":
        L([(-.7, 0), (.7, 0)]); L([(0, -.7), (0, .7)])
    elif name == "plus_circle":
        p.circle(cx, cy, .9 * h, line=col, lw=lw); L([(-.45, 0), (.45, 0)]); L([(0, -.45), (0, .45)])
    elif name == "minus":
        L([(-.7, 0), (.7, 0)])
    elif name == "close":
        L([(-.6, -.6), (.6, .6)]); L([(-.6, .6), (.6, -.6)])
    elif name == "link":
        p.rrect(cx - .95 * h, cy - .38 * h, 1.15 * h, .76 * h, .38 * h, line=col, lw=lw)
        p.rrect(cx - .2 * h, cy - .38 * h, 1.15 * h, .76 * h, .38 * h, line=col, lw=lw)
    elif name == "eyedropper":
        L([(-.85, .85), (-.6, .25), (.15, -.5)]); L([(-.85, .85), (-.25, .6), (.5, -.15)])
        L([(.05, -.6), (.6, -.05)]); p.circle(cx + .55 * h, cy - .55 * h, .3 * h, fill=col)
    elif name == "folder":
        L([(-.9, -.6), (-.35, -.6), (-.2, -.4), (.9, -.4), (.9, .7), (-.9, .7), (-.9, -.6)])
    elif name == "network":
        p.rrect(cx - .85 * h, cy - .8 * h, 1.7 * h, .9 * h, h * .15, line=col, lw=lw)
        L([(0, .1), (0, .55)]); L([(-.8, .75), (.8, .75)]); p.circle(cx, cy + .75 * h, .14 * h, fill=col)
    elif name == "file":
        L([(-.6, -.9), (.2, -.9), (.65, -.45), (.65, .9), (-.6, .9), (-.6, -.9)]); L([(.2, -.9), (.2, -.45), (.65, -.45)])
    elif name == "check":
        L([(-.6, 0), (-.15, .45), (.65, -.45)])
    elif name == "cursor_click":
        L([(-.7, -.7), (.75, -.1), (.1, .1), (-.1, .75), (-.7, -.7)])
    elif name == "database":
        p.ellipse(cx, cy - .55 * h, .75 * h, .3 * h, line=col, lw=lw)
        L([(-.75, -.55), (-.75, .55)]); L([(.75, -.55), (.75, .55)])
        p.arc(cx, cy + .55 * h - .0, .75 * h, 0, 180, col, lw)
        p.arc(cx, cy, .75 * h, 10, 170, col, lw)
    elif name == "toolbox":
        p.rrect(cx - .9 * h, cy - .45 * h, 1.8 * h, 1.25 * h, h * .12, line=col, lw=lw)
        L([(-.35, -.45), (-.35, -.8), (.35, -.8), (.35, -.45)]); L([(-.9, .1), (.9, .1)])
    elif name == "shapes":
        p.circle(cx - .3 * h, cy - .35 * h, .45 * h, line=col, lw=lw)
        p.rrect(cx + .05 * h, cy + .05 * h, .8 * h, .8 * h, h * .1, line=col, lw=lw)
        L([(-.9, .85), (-.4, .05), (.0, .85), (-.9, .85)])
    elif name == "layout":
        p.rrect(cx - .85 * h, cy - .8 * h, 1.7 * h, 1.6 * h, h * .12, line=col, lw=lw)
        L([(-.85, -.3), (.85, -.3)]); L([(-.2, -.3), (-.2, .8)])
    elif name == "radio":
        p.circle(cx, cy, .85 * h, line=col, lw=lw); p.circle(cx, cy, .45 * h, line=col, lw=lw)
    elif name == "switch":
        p.rrect(cx - .95 * h, cy - .5 * h, 1.9 * h, h, .5 * h, line=col, lw=lw)
        p.circle(cx + .45 * h, cy, .25 * h, line=col, lw=lw)
    elif name == "checkbox":
        p.rrect(cx - .8 * h, cy - .8 * h, 1.6 * h, 1.6 * h, h * .1, line=col, lw=lw); L([(-.35, 0), (-.05, .3), (.4, -.3)])
    elif name == "invert":
        L([(-.8, -.35), (.7, -.35)]); L([(.35, -.7), (.75, -.35), (.35, 0)])
        L([(.8, .35), (-.7, .35)]); L([(-.35, 0), (-.75, .35), (-.35, .7)])
    elif name == "warning":
        p.poly([(cx, cy - .85 * h), (cx + .9 * h, cy + .75 * h), (cx - .9 * h, cy + .75 * h)], line=col, lw=lw)
        L([(0, -.3), (0, .25)]); p.circle(cx, cy + .5 * h, lw * .7, fill=col)
    elif name == "magnet":
        p.arc(cx, cy, .6 * h, 0, 180, col, lw * 2.0)
        L([(-.6, 0), (-.6, -.7)]); L([(.6, 0), (.6, -.7)])
    elif name == "cube":
        L([(0, -.9), (.8, -.45), (.8, .45), (0, .9), (-.8, .45), (-.8, -.45), (0, -.9)])
        L([(-.8, -.45), (0, 0), (.8, -.45)]); L([(0, 0), (0, .9)])
    elif name == "brush":
        L([(.85, -.85), (-.1, .15)]); p.ellipse(cx - .4 * h, cy + .45 * h, .32 * h, .32 * h, fill=col)
    elif name == "sculpt":
        p.circle(cx, cy - .1 * h, .6 * h, line=col, lw=lw); L([(-.5, .75), (.5, .75)])
    elif name == "paint":
        L([(-.8, .8), (-.2, .2)]); L([(-.2, .2), (.55, -.55), (.85, -.25), (.1, .5), (-.2, .2)])
    elif name == "weight":
        for i, yy in enumerate((-.55, 0, .55)):
            L([(-.8, yy), (.8, yy)])
    elif name == "pencil":
        L([(-.8, .8), (-.65, .25), (.45, -.85), (.85, -.45), (-.25, .65), (-.8, .8)])
    elif name == "shader":
        p.circle(cx, cy, .82 * h, line=col, lw=lw); p.arc(cx, cy, .45 * h, 200, 300, col, lw)
    elif name == "home":
        L([(-.85, -.05), (0, -.85), (.85, -.05)]); L([(-.6, -.25), (-.6, .8), (.6, .8), (.6, -.25)])
    elif name == "bone":
        L([(-.5, .5), (.5, -.5)])
        for sx, sy in ((-.55, .55), (.55, -.55)):
            p.circle(cx + (sx - .15 * np.sign(sx)) * h, cy + (sy + .15 * np.sign(sx)) * h, .2 * h, fill=col)
            p.circle(cx + (sx + .15 * np.sign(sx)) * h, cy + (sy - .15 * np.sign(sx)) * h, .2 * h, fill=col)
    elif name == "tooltip":
        p.rrect(cx - .9 * h, cy - .75 * h, 1.8 * h, 1.2 * h, h * .2, line=col, lw=lw)
        L([(-.2, .45), (0, .8), (.2, .45)])
    elif name == "palette":
        p.circle(cx, cy, .85 * h, line=col, lw=lw)
        for a in (200, 250, 300, 345):
            r = math.radians(a)
            p.circle(cx + math.cos(r) * .48 * h, cy + math.sin(r) * .48 * h, .13 * h, fill=col)
    elif name == "layers":
        for dy in (.35, 0, -.35):
            p.poly([(cx, cy + (dy - .4) * h), (cx + .9 * h, cy + dy * h), (cx, cy + (dy + .4) * h),
                    (cx - .9 * h, cy + dy * h)], fill=(30, 30, 33), line=col, lw=lw)


# ------------------------------------------------------------------------------------------------ widgets
def w_frame(p, t, x, y, w, h, title=None, r=8, size=12.5):
    p.rrect(x, y, w, h, r, fill=t["panel"], line=t["panel_line"])
    if title:
        p.text(x + 11, y + 14, title, size, 500, t["text"])


def w_switch(p, t, x, y, on=True, label=None, size=11.5, scale=1.0):
    W, Hh = 30 * scale, 17 * scale
    p.rrect(x, y, W, Hh, Hh / 2, fill=t["accent"] if on else t["off"])
    kx = x + W - Hh / 2 if on else x + Hh / 2
    p.circle(kx, y + Hh / 2, Hh / 2 - 2.3 * scale, fill=t["knob"])
    if label:
        p.text(x + W + 7 * scale, y + Hh / 2, label, size, 400, t["text"])


def w_slider(p, t, x, y, w, v, label=None, knob=10, size=10, th=7):
    if label:
        p.text(x, y - 18, label, size, 400, t["dim"])
    p.rrect(x, y - th / 2, w, th, th / 2, fill=t["track"])
    kx = x + knob + (w - 2 * knob) * v
    if v > 0:
        p.rrect(x, y - th / 2, kx - x, th, th / 2, fill=t["accent"])
    p.circle(kx, y + .8, knob + .6, fill=(0, 0, 0, 70))
    p.circle(kx, y, knob, fill=t["knob"])


def w_num(p, t, x, y, w, label, value, h=19, size=10):
    p.rrect(x, y, w, h, 5, fill=t["field"], line=t["field_line"])
    chev(p, x + 9, y + h / 2, 3.0, "l", t["dim"], 1.1)
    chev(p, x + w - 9, y + h / 2, 3.0, "r", t["dim"], 1.1)
    p.text(x + 19, y + h / 2, label, size, 400, t["dim"])
    p.text(x + w - 19, y + h / 2, value, size, 450, t["text"], anchor="rm")


def w_enum(p, t, x, y, w, items, active=0, h=19, size=9.5):
    p.rrect(x, y, w, h, 5, fill=t["seg"], line=t["field_line"])
    sw = w / len(items)
    for i, s in enumerate(items):
        if i == active:
            p.rrect(x + i * sw + 2, y + 2, sw - 4, h - 4, 4, fill=t["seg_on"])
        p.text(x + i * sw + sw / 2, y + h / 2, s, size, 500 if i == active else 400,
               t["text"] if i == active else t["dim"], "mm")


def w_button(p, t, x, y, w, h, label, primary=False, size=11, r=5, active=None):
    on = primary if active is None else active
    p.rrect(x, y, w, h, r, fill=t["accent"] if on else t["btn"], line=None if on else t["btn_line"])
    p.text(x + w / 2, y + h / 2, label, size, 500 if on else 400, t["on_text"] if on else t["text"], "mm")


def w_radio(p, t, x, y, on, label, size=10.5):
    p.circle(x + 7, y, 7, fill=t["accent"] if on else None, line=None if on else t["dim"], lw=1.1)
    if on:
        p.circle(x + 7, y, 3, fill=(255, 255, 255))
    p.text(x + 19, y, label, size, 400, t["text"])


def w_check(p, t, x, y, on, label, size=10.5):
    p.rrect(x, y - 7, 14, 14, 3, fill=t["accent"] if on else None, line=None if on else t["dim"], lw=1.1)
    if on:
        p.line([(x + 3.6, y + .2), (x + 6.2, y + 2.8), (x + 10.6, y - 2.6)], (255, 255, 255), 1.6)
    p.text(x + 21, y, label, size, 400, t["text"])


def w_swatch(p, t, x, y, w, h, color, r=5):
    p.rrect(x, y, w, h, r, fill=color, line=A(t["text"], 50))


def w_brush(p, t, x, y, w, h, name, seed, active=False, size=11):
    p.rrect(x, y, w, h, 6, fill=A(t["accent"], 55) if active else t["btn"],
            line=t["accent"] if active else t["btn_line"], lw=1.6 if active else 1)
    ic = clay_icon(int(h * p.k), seed, disc=False)
    p.paste(ic, x + 3, y + 3, h - 6, h - 6)
    p.text(x + h + 4, y + h / 2, name, size, 500 if active else 400, t["text"])


def w_knob(p, t, cx, cy, r, v, label=None, size=11):
    p.arc(cx, cy, r, 135, 405, t["track"], 3.2)
    if v > 0:
        p.arc(cx, cy, r, 135, 135 + 270 * v, t["accent"], 3.2)
    a = math.radians(135 + 270 * v)
    p.circle(cx + math.cos(a) * r, cy + math.sin(a) * r, 4.2, fill=t["knob"], line=t["accent"], lw=1.2)
    p.text(cx, cy, f"{v:.1f}" if v * 10 == int(v * 10) else f"{v:.2f}", size, 450, t["text"], "mm")
    if label:
        p.text(cx, cy + r + 15, label, size * .95, 400, t["text"], "mm")


def cursor_free_selection(p, t, x, y, w, h, color=None, rot=True):
    """Edit Mode selection: a thin outline, square handles and the rotate knob."""
    c = color or t["accent"]
    p.rrect(x - 3, y - 3, w + 6, h + 6, 3, line=c, lw=1.2)
    for hx, hy in ((x - 3, y - 3), (x + w + 3, y - 3), (x - 3, y + h + 3), (x + w + 3, y + h + 3),
                   (x + w / 2, y - 3), (x + w / 2, y + h + 3), (x - 3, y + h / 2), (x + w + 3, y + h / 2)):
        p.rrect(hx - 3.2, hy - 3.2, 6.4, 6.4, 1.2, fill=(255, 255, 255), line=c, lw=1)
    if rot:
        p.line([(x + w / 2, y - 6), (x + w / 2, y - 20)], c, 1.1)
        p.circle(x + w / 2, y - 23, 3.4, fill=(255, 255, 255), line=c, lw=1)


# ------------------------------------------------------------------------------------------------ brush art
def clay_icon(px, seed, disc=True):
    """A round brush preview: a clay-like blob lit from the top left, on a dark disc. RGBA, px square."""
    S = max(24, px) * 3
    rng = random.Random(seed * 7919 + 13)
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    kind = seed % 8
    rot = rng.uniform(-35, 35)

    def stroke(pts, wd):
        P = [(x * S, y * S) for x, y in pts]
        d.line(P, fill=255, width=int(wd * S), joint="curve")
        for x, y in (P[0], P[-1]):
            r = wd * S / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def bez(p0, p1, p2, p3, n=24):
        return [((1 - u) ** 3 * p0[0] + 3 * (1 - u) ** 2 * u * p1[0] + 3 * (1 - u) * u * u * p2[0] + u ** 3 * p3[0],
                 (1 - u) ** 3 * p0[1] + 3 * (1 - u) ** 2 * u * p1[1] + 3 * (1 - u) * u * u * p2[1] + u ** 3 * p3[1])
                for u in np.linspace(0, 1, n)]

    if kind == 0:   # S stroke (Draw)
        stroke(bez((.28, .72), (.1, .35), (.85, .62), (.68, .28)), .16)
    elif kind == 1:  # blob (Inflate / Blob)
        d.ellipse([.24 * S, .2 * S, .76 * S, .82 * S], fill=255)
    elif kind == 2:  # cluster of spheres
        for cx, cy, r in ((.38, .58, .17), (.62, .58, .17), (.5, .38, .17)):
            d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=255)
    elif kind == 3:  # clay strips
        for ox in (-.1, .1):
            stroke(bez((.5 + ox, .78), (.35 + ox, .5), (.6 + ox, .4), (.48 + ox, .22)), .13)
    elif kind == 4:  # flattened half sphere (Flatten / Scrape)
        d.pieslice([.2 * S, .26 * S, .8 * S, .86 * S], 180, 360, fill=255)
        d.ellipse([.2 * S, .44 * S, .8 * S, .68 * S], fill=255)
    elif kind == 5:  # wave (Smooth)
        stroke(bez((.25, .7), (.45, .2), (.55, .9), (.75, .3)), .2)
    elif kind == 6:  # crease drop
        d.polygon([(.5 * S, .18 * S), (.72 * S, .7 * S), (.28 * S, .7 * S)], fill=255)
        d.ellipse([.28 * S, .5 * S, .72 * S, .82 * S], fill=255)
    else:            # hook (Snake Hook)
        stroke(bez((.3, .78), (.25, .3), (.7, .2), (.68, .5)), .17)
    m = m.rotate(rot, resample=RS.BICUBIC, center=(S / 2, S / 2))
    hgt = np.asarray(m.filter(ImageFilter.GaussianBlur(S * .045)), np.float32) / 255.0
    gy, gx = np.gradient(hgt)
    K = S * .055
    nx, ny, nz = -gx * K, -gy * K, np.ones_like(hgt)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    L = np.array([-.55, -.65, .55]); L /= np.linalg.norm(L)
    lam = np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / n, 0, 1)
    spec = np.clip(lam, 0, 1) ** 24 * .6
    shade = .22 + .78 * lam + spec
    col = np.clip(np.stack([shade * 222, shade * 222, shade * 226], -1), 0, 255)
    alpha = np.asarray(m, np.float32)
    blob = Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA")
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if disc:
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
        rr = np.sqrt((xx - .42) ** 2 + (yy - .38) ** 2)
        g = np.clip(84 - rr * 70, 30, 90)
        dm = Image.new("L", (S, S), 0)
        ImageDraw.Draw(dm).ellipse([S * .02, S * .02, S * .98, S * .98], fill=255)
        disc_im = Image.fromarray(np.dstack([g, g, g * 1.02, np.asarray(dm, np.float32)]).clip(0, 255).astype(np.uint8), "RGBA")
        base.alpha_composite(disc_im)
        shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sm = m.filter(ImageFilter.GaussianBlur(S * .03)).point(lambda v: v * 120 // 255)
        shadow.paste((0, 0, 0), (int(S * .02), int(S * .03)), sm)
        base.alpha_composite(Image.composite(shadow, Image.new("RGBA", (S, S), (0, 0, 0, 0)), dm))
        blob = Image.composite(blob, Image.new("RGBA", (S, S), (0, 0, 0, 0)), dm)
        ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([S * .02, S * .02, S * .98, S * .98], outline=(95, 95, 100, 255), width=max(1, S // 60))
        base.alpha_composite(blob)
        base.alpha_composite(ring)
    else:
        base.alpha_composite(blob)
    return base.resize((px, px), RS.LANCZOS)


# ------------------------------------------------------------------------------------------------ scenes
def mini_render(p, x, y, w, h, r=4):
    """An abstract camera preview: a cube, a monkey-ish head and a chrome ball on a floor."""
    s = Pic(w, h, p.k / 1, bg=(120, 128, 136), ss=1)
    s.grad(0, 0, w, h * .55, (112, 121, 131), (146, 152, 160))
    s.grad(0, h * .55, w, h * .45, (150, 156, 162), (112, 118, 125))
    for i in range(1, 9):
        yy = h * .55 + (h * .45) * (i / 9) ** 1.6
        s.line([(0, yy), (w, yy)], (255, 255, 255, 18), .6, caps=False)
    for i in range(-8, 9):
        s.line([(w / 2 + i * w * .04, h * .55), (w / 2 + i * w * .16, h)], (255, 255, 255, 14), .6, caps=False)
    # soft shadows
    for cx, cy, rx, ry in ((w * .26, h * .86, w * .12, h * .05), (w * .52, h * .84, w * .13, h * .05), (w * .76, h * .78, w * .08, h * .035)):
        s.ellipse(cx, cy, rx, ry, fill=(40, 46, 52, 70))
    # cube
    cx, cy, sz = w * .26, h * .62, w * .14
    s.poly([(cx - sz * .55, cy), (cx + sz * .25, cy - sz * .12), (cx + sz * .25, cy + sz * .78), (cx - sz * .55, cy + sz * .9)], fill=(86, 176, 182))
    s.poly([(cx + sz * .25, cy - sz * .12), (cx + sz * .6, cy + sz * .05), (cx + sz * .6, cy + sz * .85), (cx + sz * .25, cy + sz * .78)], fill=(58, 140, 148))
    s.poly([(cx - sz * .55, cy), (cx - sz * .15, cy - sz * .22), (cx + sz * .6, cy + sz * .05), (cx + sz * .25, cy - sz * .12)], fill=(130, 206, 210))
    # head
    hx, hy = w * .52, h * .52
    s.ellipse(hx - w * .085, hy - h * .07, w * .05, h * .07, fill=(222, 156, 128))
    s.ellipse(hx + w * .085, hy - h * .07, w * .05, h * .07, fill=(222, 156, 128))
    s.ellipse(hx, hy, w * .09, h * .2, fill=(236, 172, 142))
    s.ellipse(hx, hy + h * .12, w * .075, h * .1, fill=(244, 190, 160))
    s.ellipse(hx - w * .035, hy - h * .04, w * .028, h * .045, fill=(150, 92, 74))
    s.ellipse(hx + w * .035, hy - h * .04, w * .028, h * .045, fill=(150, 92, 74))
    s.ellipse(hx - w * .02, hy - h * .12, w * .04, h * .04, fill=(250, 214, 196, 120))
    # chrome ball
    bx, by, br = w * .77, h * .6, w * .075
    s.circle(bx, by, br, fill=(70, 74, 80))
    s.ellipse(bx, by + br * .35, br * .95, br * .55, fill=(150, 156, 162))
    s.ellipse(bx, by - br * .25, br * .9, br * .5, fill=(205, 212, 220))
    s.circle(bx - br * .35, by - br * .4, br * .2, fill=(255, 255, 255))
    p.paste(s.out(), x, y, w, h)
    return s


def scene_control_panel(t=DARK, scale=2.0, height=550, parts=None):
    """The Studio Control Panel canvas (Live Mode), redrawn. Logical 904 x 550.

    parts: None (everything) or a set of "lighting", "render", "playback", "playback_compact", "objects",
    "preview" (the focus crops draw only some frames)."""
    full = {"lighting", "render", "playback", "objects", "preview"}
    has = (lambda k: k in (full if parts is None else parts))
    p = Pic(904, height, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1)
    # title with logo
    p.rrect(42, 22, 37, 37, 9, fill=(47, 104, 240))
    p.rrect(51, 31, 19, 19, 3, line=(255, 255, 255), lw=1.6)
    p.circle(60.5, 40.5, 4.2, line=(255, 255, 255), lw=1.6)
    p.text(120, 30, "Studio Control", 19, 400, t["text"])
    p.text(123, 51, "Lights, render and playback for this shot", 9.5, 400, t["dim"])
    # Lighting
    if has("lighting"):
        _cp_lighting(p, t)
    if has("render"):
        _cp_render(p, t)
    if has("playback"):
        _cp_playback(p, t)
    if has("playback_compact"):
        w_frame(p, t, 343, 312, 235, 112, "Playback")
        p.text(570, 326, "Frame 1", 12.5, 400, t["dim"], "rm")
        for i, lab in enumerate(("Start", "Prev", "Play", "Next")):
            w_button(p, t, 352 + i * 54.5, 346, 51, 26, lab, lab == "Play", 10.5)
        w_slider(p, t, 352, 404, 216, .3, "Scrub", size=9.5)
    if has("objects"):
        _cp_objects(p, t)
    if has("preview"):
        w_frame(p, t, 668, 362, 218, 172, "Preview")
        mini_render(p, 677, 391, 200, 112)
        p.text(777, 516, "Camera preview", 9.5, 400, t["text"], "mm")
    return p


def _cp_lighting(p, t):
    w_frame(p, t, 18, 68, 256, 356, "Lighting")
    rows = [("Key Light", 108, "600", (255, 239, 226), .48, "Size"), ("Fill Light", 237, "150", (222, 233, 255), .78, "Size"),
            ("Rim Light", 339, "900", (250, 250, 250), 0.0, "Radius")]
    for name, yy, pw, col, v, sl in rows:
        p.text(102, yy, name, 12.5, 400, t["text"], "mm")
        w_switch(p, t, 194, yy - 8.5, True, "Shadow", 10.5)
        w_num(p, t, 34, yy + 20, 134, "Power", pw)
        w_swatch(p, t, 182, yy + 20, 82, 19, col)
        if name == "Key Light":
            w_slider(p, t, 28, yy + 68, 232, v, sl, size=9.5)
            w_enum(p, t, 28, yy + 86, 232, ["Square", "Rectangle", "Disk", "Ellipse"], 0, 18, 9)
        elif name == "Fill Light":
            w_slider(p, t, 28, yy + 67, 232, v, sl, size=9.5)
        else:
            w_slider(p, t, 28, yy + 66, 232, v, sl, size=9.5)


def _cp_render(p, t):
    w_frame(p, t, 343, 56, 235, 237, "Render")
    w_enum(p, t, 352, 88, 216, ["EEVEE", "Workbench", "Cycles"], 0, 18, 9)
    p.text(368, 124, "Scale", 10.5, 400, t["text"])
    for xx, lab, on in ((420, "25%", False), (474, "50%", True), (529, "100%", False)):
        w_radio(p, t, xx, 124, on, lab, 10)
    w_num(p, t, 352, 144, 106, "X", "1280", 18)
    w_num(p, t, 462, 144, 106, "Y", "720", 18)
    for i, lab in enumerate(("Transparent Film", "Motion Blur", "Simplify")):
        w_switch(p, t, 359, 174 + i * 25, False, lab, 10.5)
    w_button(p, t, 352, 257, 216, 26, "Render Image", True, 10.5)


def _cp_playback(p, t):
    w_frame(p, t, 343, 312, 235, 203, "Playback")
    p.text(460, 357, "Frame 1", 21, 400, t["text"], "mm")
    for i, lab in enumerate(("Start", "Prev", "Play", "Next")):
        w_button(p, t, 361 + i * 50, 387, 48, 25, lab, lab == "Play", 10.5)
    w_num(p, t, 352, 424, 106, "Start", "1", 18)
    w_num(p, t, 462, 424, 106, "End", "120", 18)
    w_slider(p, t, 352, 469, 216, 0, "Scrub", size=9.5)
    p.text(460, 495, "24 fps", 10.5, 400, t["text"], "mm")


def _cp_objects(p, t):
    w_frame(p, t, 668, 18, 218, 338, "Objects")
    p.text(777, 59, "Modifiers", 10.5, 400, t["text"], "mm")
    for i, (lab, on) in enumerate((("Suzanne Subdivision", True), ("Cube Bevel", True), ("Sphere Wireframe", False))):
        w_switch(p, t, 690, 74 + i * 23.5, on, lab, 10)
    w_num(p, t, 678, 149, 198, "Subdivision Levels", "2", 18)
    p.text(777, 186, "Materials", 10.5, 400, t["text"], "mm")
    for i, (lab, col) in enumerate((("Suzanne", (236, 170, 128)), ("Cube", (80, 182, 190)), ("Sphere", (242, 242, 242)))):
        p.text(770, 209 + i * 23.5, lab, 10, 400, t["text"], "rm")
        w_swatch(p, t, 780, 200 + i * 23.5, 96, 18, col)
    p.text(777, 284, "Visible in Render", 10.5, 400, t["text"], "mm")
    for xx, lab in ((680, "Suzanne"), (752, "Cube"), (811, "Sphere")):
        w_check(p, t, xx, 307, True, lab, 9.5)
    w_button(p, t, 679, 328, 96, 24, "Add Monkey", False, 10)
    w_button(p, t, 779, 328, 96, 24, "Shade Smooth", False, 10)


def scene_ring_menu(scale=2.0, active_seg=0, active_slot=2, core="Clay Strips", title="Default Set", bg=DARK["canvas"],
                    with_dots=True):
    """A Ring Menu: brush slots in the outer ring, toggles in the inner ring, the name in the core. 740 x 810."""
    t = DARK
    p = Pic(740, 810, scale, bg=bg)
    if with_dots:
        p.dots(t["dot"], 40, 1.1)
    cx, cy = 369, 412
    p.text(cx, 46, title, 17, 400, t["text"], "mm")
    p.circle(cx, cy, 312, fill=(28, 28, 30), line=(58, 58, 62), lw=1.5)
    # inner segments
    icons = ["mirror", "topology", "circles", "dashed", "panel", "halfcircle", "eraser", "grid"]
    n = len(icons)
    r0, r1 = 118, 196
    for i, ic in enumerate(icons):
        a_mid = -90 + i * 360 / n
        a0, a1 = math.radians(a_mid - 180 / n + 1.6), math.radians(a_mid + 180 / n - 1.6)
        pts = [(cx + r1 * math.cos(a), cy + r1 * math.sin(a)) for a in np.linspace(a0, a1, 32)]
        pts += [(cx + r0 * math.cos(a), cy + r0 * math.sin(a)) for a in np.linspace(a1, a0, 32)]
        on = i == active_seg
        p.soft_poly(pts, (44, 92, 196) if on else (40, 40, 43), 3.0, line=(80, 132, 236) if on else (52, 52, 56), lw=1.2)
        am = math.radians(a_mid)
        icon(p, ic, cx + 157 * math.cos(am), cy + 157 * math.sin(am), 30, (240, 240, 242), 2.0)
    # core
    p.circle(cx, cy, 114, fill=(15, 15, 16), line=(50, 50, 54), lw=1.2)
    p.text(cx, cy, core, 18, 400, t["text"], "mm")
    # outer slots
    m = 16
    for i in range(m):
        a = math.radians(-90 + i * 360 / m)
        sx, sy = cx + 267 * math.cos(a), cy + 267 * math.sin(a)
        sel = i == active_slot
        if sel:
            p.circle(sx, sy, 43, fill=(15, 15, 16), line=(255, 255, 255), lw=2.4)
            p.circle(sx, sy, 39, line=t["accent"], lw=3.4)
        ic = clay_icon(int(72 * p.k), i)
        p.paste(ic, sx - 36, sy - 36, 72, 72)
    # page tab
    p.rrect(cx - 114, 714, 228, 62, 31, fill=(20, 20, 22), line=(58, 58, 62), lw=1.3)
    chev(p, cx - 64, 745, 7, "l", t["text"], 1.8)
    chev(p, cx + 64, 745, 7, "r", t["text"], 1.8)
    p.text(cx, 745, "1 / 5", 18, 400, t["text"], "mm")
    return p


def scene_add_widget(scale=2.0, query=None):
    """The Add Widget browser. Logical 907 x 628."""
    t = DARK
    p = Pic(907, 628, scale, bg=(22, 22, 24))
    p.rrect(14, 14, 879, 600, 12, fill=(26, 26, 28), line=(58, 58, 64), lw=1.2)
    icon(p, "plus_circle", 43, 45, 18, (70, 130, 255), 1.6)
    p.text(64, 45, "Add Widget", 16, 500, t["text"])
    p.rrect(252, 28, 420, 34, 8, fill=(30, 30, 34), line=(64, 120, 245), lw=1.4)
    icon(p, "search", 273, 45, 16, (190, 190, 196), 1.5)
    if query:
        p.text(293, 45, query, 13, 400, t["text"])
        qx = 293 + p.tw(query, 13)
        p.line([(qx + 2, 36), (qx + 2, 54)], (120, 160, 255), 1.2, caps=False)
    else:
        p.text(293, 45, "Search widgets", 13, 400, (130, 130, 136))
    p.rrect(685, 28, 150, 34, 8, fill=(26, 40, 66), line=(64, 110, 210), lw=1.2)
    icon(p, "link", 704, 45, 14, (120, 165, 255), 1.4)
    p.text(718, 45, "From Property", 12, 500, (220, 228, 255))
    icon(p, "close", 860, 45, 14, (200, 200, 205), 1.5)
    p.line([(15, 78), (892, 78)], (52, 52, 58), 1, caps=False)
    p.line([(197, 79), (197, 548)], (52, 52, 58), 1, caps=False)
    cats = [("grid", "All", 21), ("cursor_click", "Buttons", 2), ("database", "Data", 13), ("toolbox", "Tools", 2),
            ("shapes", "Graphics", 1), ("layout", "Layout", 3)]
    for i, (ic, name, n) in enumerate(cats):
        yy = 108 + i * 34
        if i == 0:
            p.rrect(24, yy - 15, 164, 30, 6, fill=(38, 48, 70))
        icon(p, ic, 41, yy, 13, (110, 155, 255) if i == 0 else (190, 190, 196), 1.3)
        p.text(58, yy, name, 12, 500 if i == 0 else 400, t["text"])
        p.text(178, yy, str(n), 11, 400, t["dim"], "rm")
    def section(y, label):
        p.text(218, y, label, 10, 600, t["dim"], track=.08)
        p.line([(218 + p.tw(label, 10, 600) * 1.1 + 10, y), (874, y)], (50, 50, 56), 1, caps=False)
    def card(x, y, ic, name, desc, sel=False):
        p.rrect(x, y, 211, 166, 9, fill=(32, 32, 35), line=(70, 120, 245) if sel else (62, 62, 68), lw=1.6 if sel else 1)
        p.rrect(x + 6, y + 6, 199, 82, 6, fill=(36, 42, 56) if sel else (34, 38, 48))
        icon(p, ic, x + 105, y + 47, 34, (70, 132, 255), 2.2)
        p.text(x + 12, y + 104, name, 12.5, 500, t["text"])
        words, line, ly = desc.split(), "", y + 124
        for wd in words:
            if p.tw(line + " " + wd, 10) > 186:
                p.text(x + 12, ly, line.strip(), 10, 400, t["dim"]); line, ly = "", ly + 14
            line += " " + wd
        p.text(x + 12, ly, line.strip(), 10, 400, t["dim"])
    section(100, "BUTTONS")
    card(216, 114, "bolt", "Operator", "A button that runs an operator, with its options", True)
    card(440, 114, "code", "Custom Script", "A button that runs a Python script from a text block")
    section(316, "DATA  \u00b7  TOGGLES")
    card(216, 330, "radio", "Radial", "A round on / off button for a property")
    card(440, 330, "switch", "Switch", "A sliding switch for an on / off property")
    card(664, 330, "checkbox", "Checkbox", "A checkbox and its label for an on / off property")
    p.rrect(216, 512, 211, 36, 9, fill=(32, 32, 35), line=(62, 62, 68))
    p.rrect(217, 518, 209, 30, 0, fill=(26, 26, 28))
    p.rrect(222, 517, 199, 31, 6, fill=(34, 38, 48))
    p.line([(15, 548), (892, 548)], (52, 52, 58), 1, caps=False)
    p.rrect(880, 80, 5, 92, 2.5, fill=(80, 80, 86))
    p.text(32, 572, "Operator  \u00b7  Buttons", 12.5, 500, t["text"])
    p.text(32, 592, "A button that runs an operator, with its options  \u2014  Enter adds it, then a click places it", 10, 400, t["dim"])
    w_button(p, t, 755, 564, 120, 36, "Add", True, 12, 7)
    return p


def scene_edit_mode(scale=2.0):
    """Edit Mode on the control panel: a frame moved, magenta snapping guides, the position badge."""
    t = DARK
    p = scene_control_panel(t, scale, 610)
    # cover the Preview frame (it is being moved) and draw its ghost where it was
    p.rrect(640, 360, 264, 190, 0, fill=t["canvas"])
    p.dots(t["dot"], 40, 1.1, 640, 360, 264, 190)
    for (x, y, w, h) in ((668, 362, 218, 172),):
        n = 0
        xx = x
        while xx < x + w:
            p.line([(xx, y), (min(xx + 6, x + w), y)], (110, 110, 118), 1, caps=False)
            p.line([(xx, y + h), (min(xx + 6, x + w), y + h)], (110, 110, 118), 1, caps=False)
            xx += 11
        yy = y
        while yy < y + h:
            p.line([(x, yy), (x, min(yy + 6, y + h))], (110, 110, 118), 1, caps=False)
            p.line([(x + w, yy), (x + w, min(yy + 6, y + h))], (110, 110, 118), 1, caps=False)
            yy += 11
    # the moved frame, under Lighting, edges snapped
    fx, fy, fw, fh = 18, 446, 218, 122
    w_frame(p, t, fx, fy, fw, fh, "Preview")
    mini_render(p, fx + 9, fy + 27, fw - 18, fh - 36)
    g = t["guide"]
    p.line([(18, 62), (18, 600)], g, 1.1, caps=False)
    p.line([(146, 424), (146, 446)], g, 1.1, caps=False)
    for yy in (424, 446):
        p.line([(140, yy), (152, yy)], g, 1.1, caps=False)
    p.rrect(154, 427, 24, 15, 4, fill=g)
    p.text(166, 434.5, "22", 9, 600, (255, 255, 255), "mm")
    cursor_free_selection(p, t, fx, fy, fw, fh, t["accent"], rot=False)
    p.rrect(70, 580, 112, 20, 10, fill=t["accent"])
    p.text(126, 590, "X -510  Y -270", 10, 600, (255, 255, 255), "mm")
    return p


def scene_layers(scale=2.0, compact=False):
    """One canvas with a layer per mode: the tab row and the Sculpt layer. Logical 900 x 560.

    compact: 600 x 372, five tabs and two panels (Basic brushes, Stroke): the focus crop."""
    t = DARK
    W = 600 if compact else 900
    p = Pic(W, 372 if compact else 560, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1)
    tabs = [("home", "Home", None), ("cube", "Object", None), ("shader", "Look Dev", None), ("sculpt", "Sculpt", True),
            ("paint", "Texture Paint", None), ("weight", "Weight Paint", None), ("pencil", "Draw", None)]
    if compact:
        tabs = [tb for tb in tabs if tb[1] not in ("Look Dev", "Weight Paint")]
    x = 16
    p.rrect(10, 10, W - 20, 36, 10, fill=(30, 30, 33), line=(56, 56, 60))
    for ic, lab, on in tabs:
        w = p.tw(lab, 11.5, 500) + 40
        if on:
            p.rrect(x, 15, w, 26, 7, fill=(44, 56, 84))
        colr = {"Sculpt": (120, 170, 255), "Texture Paint": (220, 120, 200), "Weight Paint": (110, 200, 120),
                "Draw": (220, 120, 200), "Object": (190, 190, 196), "Look Dev": (190, 190, 196), "Home": (190, 190, 196)}[lab]
        icon(p, ic, x + 15, 28, 12, colr if on or lab not in ("Object", "Look Dev", "Home") else (170, 170, 176), 1.3)
        p.text(x + 27, 28, lab, 11.5, 500 if on else 400, t["text"] if on else t["dim"])
        x += w + 8
    p.text(26, 82, "Sculpt", 26, 400, t["text"])
    p.text(28, 108, "This layer shows in Sculpt Mode", 11, 400, t["dim"])
    # brushes in titled blocks
    w_frame(p, t, 22, 130, 300, 152, "Basic")
    names = [("Draw", 0), ("Clay Strips", 3), ("Inflate", 1), ("Grab", 7)]
    for i, (n, s) in enumerate(names):
        w_brush(p, t, 32 + (i % 2) * 143, 156 + (i // 2) * 58, 136, 48, n, s, active=(n == "Clay Strips"), size=11)
    if compact:
        w_frame(p, t, 340, 130, 238, 220, "Stroke")
        w_slider(p, t, 352, 186, 214, .42, "Radius", size=10.5)
        w_slider(p, t, 352, 232, 214, .66, "Strength", size=10.5)
        w_enum(p, t, 352, 256, 214, ["Add", "Subtract"], 0, 22, 10.5)
        p.text(352, 304, "Symmetry", 10.5, 400, t["dim"])
        for i, (lab, on) in enumerate((("X", True), ("Y", False), ("Z", False))):
            w_button(p, t, 352 + i * 73, 316, 68, 24, lab, False, 10.5, active=on)
        w_frame(p, t, 22, 296, 300, 64, None)
        w_button(p, t, 32, 314, 136, 28, "Invert Mask", False, 11)
        w_button(p, t, 175, 314, 136, 28, "Clear Mask", False, 11)
        return p
    w_frame(p, t, 22, 296, 300, 98, "Smooth & Flatten")
    for i, (n, s) in enumerate((("Smooth", 5), ("Flatten", 4))):
        w_brush(p, t, 32 + i * 143, 324, 136, 48, n, s, size=11)
    w_frame(p, t, 22, 408, 300, 132, "Masking")
    for i, (n, s) in enumerate((("Mask", 6), ("Box Mask", 2))):
        w_brush(p, t, 32 + i * 143, 436, 136, 48, n, s, size=11)
    w_button(p, t, 32, 496, 136, 26, "Invert Mask", False, 10.5)
    w_button(p, t, 175, 496, 136, 26, "Clear Mask", False, 10.5)
    # stroke
    w_frame(p, t, 340, 130, 260, 220, "Stroke")
    w_slider(p, t, 352, 186, 236, .42, "Radius", size=10)
    w_slider(p, t, 352, 232, 236, .66, "Strength", size=10)
    w_enum(p, t, 352, 256, 236, ["Add", "Subtract"], 0, 22, 10)
    p.text(352, 304, "Symmetry", 10, 400, t["dim"])
    for i, (lab, on) in enumerate((("X", True), ("Y", False), ("Z", False))):
        w_button(p, t, 352 + i * 80, 316, 76, 24, lab, False, 10.5, active=on)
    w_frame(p, t, 340, 364, 260, 176, "Remesh")
    w_slider(p, t, 352, 418, 236, .3, "Voxel Size", size=10)
    w_button(p, t, 352, 444, 236, 28, "Voxel Remesh", True, 11)
    w_button(p, t, 352, 480, 116, 26, "Symmetrize", False, 10.5)
    w_button(p, t, 472, 480, 116, 26, "Dyntopo", False, 10.5)
    # viewport
    w_frame(p, t, 618, 130, 262, 166, "Viewport")
    w_enum(p, t, 630, 162, 238, ["Solid", "Material"], 0, 22, 10)
    w_enum(p, t, 630, 194, 238, ["Matcap", "Studio"], 0, 22, 10)
    w_switch(p, t, 632, 232, True, "Wireframe", 10.5)
    w_switch(p, t, 632, 260, False, "X-Ray", 10.5)
    w_frame(p, t, 618, 310, 262, 230, "Face Sets")
    w_brush(p, t, 630, 338, 238, 48, "Draw Face Sets", 5, size=11)
    w_button(p, t, 630, 398, 116, 26, "Grow", False, 10.5)
    w_button(p, t, 752, 398, 116, 26, "Shrink", False, 10.5)
    w_button(p, t, 630, 432, 238, 26, "Face Set from Masked", False, 10.5)
    w_switch(p, t, 632, 474, True, "Show Face Sets", 10.5)
    w_switch(p, t, 632, 502, False, "Show Mask", 10.5)
    return p


def scene_binding(scale=2.0):
    """Binding with the eyedropper: Blender's Light properties on the left, the canvas on the right. 1000 x 560."""
    t = DARK
    p = Pic(1000, 560, scale, bg=t["canvas"])
    cx0 = 430
    p.dots(t["dot"], 40, 1.1, cx0, 40, 570, 520)
    # the Blender properties editor
    p.rrect(0, 0, cx0, 560, 0, fill=(43, 43, 43))
    p.line([(cx0, 0), (cx0, 560)], (22, 22, 22), 2, caps=False)
    p.rrect(14, 16, 402, 30, 4, fill=(50, 50, 50))
    chev(p, 28, 31, 4, "d", (200, 200, 200), 1.3)
    p.text(42, 31, "Light", 12, 500, (230, 230, 230))
    for i, (lab, on) in enumerate((("Point", False), ("Sun", False), ("Spot", False), ("Area", True))):
        p.rrect(24 + i * 96, 60, 94, 24, 4, fill=(71, 114, 179) if on else (84, 84, 84))
        p.text(71 + i * 96, 72, lab, 11, 400, (255, 255, 255) if on else (220, 220, 220), "mm")
    rows = [("Color", None), ("Power", "600 W"), ("Exposure", "0.000"), ("Normalize", "check"), ("Shape", "Square"),
            ("Size", "1 m"), ("Max Bounces", "1024")]
    for i, (lab, val) in enumerate(rows):
        yy = 116 + i * 36
        p.text(130, yy, lab, 11.5, 400, (205, 205, 205), "rm")
        if val is None:
            p.rrect(142, yy - 11, 260, 22, 4, fill=(255, 239, 226))
        elif val == "check":
            p.rrect(142, yy - 7, 14, 14, 3, fill=(71, 114, 179))
            p.line([(145.5, yy), (148.5, yy + 3), (153, yy - 3)], (255, 255, 255), 1.5)
            p.text(164, yy, "Normalize", 11, 400, (220, 220, 220))
        else:
            hi = lab == "Exposure"
            p.rrect(142, yy - 11, 260, 22, 4, fill=(104, 104, 104) if hi else (84, 84, 84))
            p.text(272, yy, val, 11, 400, (240, 240, 240), "mm")
            if hi:
                p.rrect(137, yy - 16, 270, 32, 6, line=(245, 160, 50), lw=2)
    # eyedropper hint
    p.soft_shadow(142, 392, 260, 58, 8)
    p.rrect(142, 392, 260, 58, 8, fill=(30, 30, 32), line=(74, 74, 80))
    icon(p, "eyedropper", 166, 421, 18, (245, 170, 70), 1.7)
    p.text(188, 412, "Right-click a property", 11.5, 500, (240, 240, 240))
    p.text(188, 430, "anywhere in Blender", 10.5, 400, (170, 170, 176))
    # canvas header strip
    p.rrect(cx0 + 1, 0, 1000 - cx0, 40, 0, fill=(36, 36, 39))
    p.line([(cx0, 40), (1000, 40)], (54, 54, 58), 1, caps=False)
    p.rrect(cx0 + 14, 9, 52, 22, 5, fill=(52, 98, 200))
    p.text(cx0 + 40, 20, "Edit", 11, 500, (255, 255, 255), "mm")
    p.text(cx0 + 80, 20, "Studio Control Panel", 10.5, 500, t["text"])
    p.rrect(1000 - 152, 9, 138, 22, 6, fill=(26, 40, 66), line=(64, 110, 210))
    icon(p, "link", 1000 - 135, 20, 11, (120, 165, 255), 1.2)
    p.text(1000 - 123, 20, "From Property", 10.5, 500, (220, 228, 255))
    # the frame with the widget being bound
    fx = cx0 + 70
    w_frame(p, t, fx, 96, 410, 300, "Key Light")
    w_switch(p, t, fx + 20, 136, True, "Shadow", 11)
    w_num(p, t, fx + 20, 172, 180, "Power", "600 W", 22, 10.5)
    w_swatch(p, t, fx + 214, 172, 176, 22, (255, 239, 226))
    p.text(fx + 20, 232, "Exposure", 10.5, 400, t["text"])
    w_slider(p, t, fx + 20, 256, 370, .5, None, knob=12, th=8)
    cursor_free_selection(p, t, fx + 10, 242, 390, 28)
    p.rrect(fx + 95, 286, 220, 22, 6, fill=(24, 24, 26), line=(70, 70, 76))
    p.text(fx + 205, 297, "370 \u00d7 28  \u00b7  Exposure", 10, 500, t["text"], "mm")
    w_slider(p, t, fx + 20, 352, 370, .78, "Size", knob=12, th=8)
    # the link from the property to the widget
    pts = [(407, 188), (440, 188), (fx - 40, 256), (fx + 4, 256)]
    bez = [((1 - u) ** 3 * pts[0][0] + 3 * (1 - u) ** 2 * u * pts[1][0] + 3 * (1 - u) * u * u * pts[2][0] + u ** 3 * pts[3][0],
            (1 - u) ** 3 * pts[0][1] + 3 * (1 - u) ** 2 * u * pts[1][1] + 3 * (1 - u) * u * u * pts[2][1] + u ** 3 * pts[3][1])
           for u in np.linspace(0, 1, 49)]
    for i in range(0, 46, 4):
        p.line(bez[i:i + 3], (245, 160, 50), 2)
    p.circle(*pts[0], 4.5, fill=(245, 160, 50))
    p.circle(*pts[3], 4.5, fill=(245, 160, 50))
    # data path read-out
    p.rrect(fx, 420, 410, 60, 8, fill=(30, 30, 32), line=(60, 60, 64))
    p.text(fx + 16, 439, "DATA PATH", 9.5, 600, t["dim"], track=.08)
    p.text(fx + 16, 461, "objects[\"Key\"].data.exposure", 11.5, 500, (150, 190, 255), mono=True)
    return p


def scene_themes(scale=1.6):
    """Four looks of the same panel: Default, Sunset, Violet and Light. Returns a list of (name, image)."""
    out = []
    for name, th in (("Default", DARK), ("Sunset", SUNSET), ("Violet", VIOLET), ("Light", LIGHT)):
        out.append((name, scene_control_panel(th, scale).out()))
    return out


def scene_presets(scale=2.0, thumbs=None, compact=False):
    """The presets menu with thumbnails, a .flexspace file and the shared folder. Logical 900 x 560."""
    t = DARK
    p = Pic(900, 560, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1)
    # top bar (Edit Mode) with the preset button
    p.rrect(0, 0, 900, 40, 0, fill=(36, 36, 39))
    p.line([(0, 40), (900, 40)], (54, 54, 58), 1, caps=False)
    p.rrect(12, 9, 150, 22, 5, fill=(48, 48, 52))
    p.text(22, 20, "Studio Control Panel", 10.5, 500, t["text"])
    chev(p, 152, 20, 3.5, "d", t["dim"], 1.2)
    p.rrect(170, 9, 76, 22, 11, fill=(26, 52, 36), line=(80, 170, 110))
    p.circle(183, 20, 3.2, fill=(110, 210, 140))
    p.text(192, 20, "Up to date", 10, 500, (190, 235, 205))
    p.rrect(256, 9, 128, 22, 5, fill=(48, 48, 52))
    p.text(320, 20, "Save as Global...", 10.5, 400, t["text"], "mm")
    # presets menu
    mx, my, mw, mh = 40, 54, 470, 480
    p.soft_shadow(mx, my, mw, mh, 10, 22, 12, 190)
    p.rrect(mx, my, mw, mh, 10, fill=(32, 32, 35), line=(64, 64, 70), lw=1.2)
    p.text(mx + 16, my + 22, "Global Presets", 12.5, 600, t["text"])
    items = [("Studio Control Panel", "Object Mode", False), ("Sculpt Wheel", "Sculpt Mode", False),
             ("Rigify Body Picker", "Pose Mode", True), ("FlexSpace Studio", "Every mode", False)]
    for i, (name, sub, shared) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = mx + 16 + col * 222, my + 44 + row * 172
        hover = i == 0
        p.rrect(x, y, 214, 160, 8, fill=(40, 44, 54) if hover else (38, 38, 42), line=(70, 120, 245) if hover else (56, 56, 62),
                lw=1.4 if hover else 1)
        if thumbs and i < len(thumbs):
            th, focus = thumbs[i] if isinstance(thumbs[i], tuple) else (thumbs[i], (.5, .5))
            tm = cover(th, round(202 * p.k), round(110 * p.k), focus, f"presets thumb {name}")
            mask = Image.new("L", tm.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, tm.width - 1, tm.height - 1], radius=5 * p.k, fill=255)
            p.im.paste(tm, (round((x + 6) * p.k), round((y + 6) * p.k)), mask)
        p.text(x + 10, y + 132, name + (" (Shared)" if shared else ""), 11.5, 500, t["text"])
        p.text(x + 10, y + 149, sub, 9.5, 400, t["dim"])
        if shared:
            icon(p, "network", x + 196, y + 136, 14, (170, 170, 176), 1.2)
    p.line([(mx + 12, my + 400), (mx + mw - 12, my + 400)], (56, 56, 62), 1, caps=False)
    for i, lab in enumerate(("Save as Global Preset...", "Manage")):
        yy = my + 424 + i * 28
        p.text(mx + 20, yy, lab, 11.5, 400, t["text"])
        if lab == "Manage":
            chev(p, mx + mw - 24, yy, 3.5, "r", t["dim"], 1.2)
    if compact:
        return p
    # Manage submenu
    sx, sy = mx + mw - 6, my + 430
    p.soft_shadow(sx, sy, 150, 70, 8, 16, 8, 170)
    p.rrect(sx, sy, 150, 70, 8, fill=(36, 36, 40), line=(64, 64, 70))
    p.rrect(sx + 5, sy + 6, 140, 26, 5, fill=(52, 92, 190))
    p.text(sx + 16, sy + 19, "Export", 11.5, 500, (255, 255, 255))
    p.text(sx + 16, sy + 49, "Import...", 11.5, 400, t["text"])
    # .flexspace file card
    fx, fy = 640, 120
    p.soft_shadow(fx, fy, 210, 150, 12, 22, 12, 170)
    p.rrect(fx, fy, 210, 150, 12, fill=(36, 36, 40), line=(70, 70, 78))
    p.soft_poly([(fx + 24, fy + 22), (fx + 70, fy + 22), (fx + 90, fy + 42), (fx + 90, fy + 108), (fx + 24, fy + 108)],
                (52, 58, 72), 2)
    p.soft_poly([(fx + 70, fy + 22), (fx + 90, fy + 42), (fx + 70, fy + 42)], (80, 92, 118), 1)
    p.text(fx + 57, fy + 80, "F", 26, 700, GOLD, "mm")
    p.text(fx + 104, fy + 56, "studio_panel", 12, 500, t["text"])
    p.text(fx + 104, fy + 74, ".flexspace", 12, 500, GOLD)
    p.text(fx + 24, fy + 130, "Preset + thumbnail, one file", 10, 400, t["dim"])
    # shared folder card
    fy2 = 300
    p.soft_shadow(fx, fy2, 210, 168, 12, 22, 12, 170)
    p.rrect(fx, fy2, 210, 168, 12, fill=(36, 36, 40), line=(70, 70, 78))
    icon(p, "network", fx + 34, fy2 + 32, 24, (130, 179, 160), 1.8)
    p.text(fx + 58, fy2 + 32, "Shared Presets Folder", 11.5, 600, t["text"])
    for i, n in enumerate(("Rigify Body Picker", "Sculpt Wheel", "Lookdev Panel")):
        yy = fy2 + 70 + i * 30
        p.rrect(fx + 14, yy - 12, 182, 24, 5, fill=(44, 44, 48))
        icon(p, "file", fx + 30, yy, 12, (190, 190, 196), 1.2)
        p.text(fx + 44, yy, n, 10.5, 400, t["text"])
    return p


def scene_demo_browser(scale=2.0, thumbs=None):
    """The demo browser. Logical 923 x 600."""
    t = DARK
    p = Pic(923, 600, scale, bg=(22, 22, 24))
    p.rrect(10, 10, 903, 580, 12, fill=(26, 26, 28), line=(58, 58, 64), lw=1.2)
    p.text(34, 40, "Demo Files", 16, 500, t["text"])
    p.rrect(250, 24, 380, 32, 8, fill=(30, 30, 34), line=(62, 62, 68))
    icon(p, "search", 270, 40, 15, (170, 170, 176), 1.4)
    p.text(288, 40, "Search demos", 12.5, 400, (130, 130, 136))
    icon(p, "close", 885, 40, 13, (200, 200, 205), 1.4)
    p.line([(11, 70), (912, 70)], (52, 52, 58), 1, caps=False)
    p.line([(200, 71), (200, 530)], (52, 52, 58), 1, caps=False)
    cats = [("All", 10), ("Control Panels", 3), ("Modes & Layers", 1), ("Brushes", 1), ("Armature Pickers", 5)]
    for i, (c, n) in enumerate(cats):
        yy = 98 + i * 34
        if i == 0:
            p.rrect(20, yy - 15, 170, 30, 6, fill=(38, 48, 70))
        p.text(34, yy, c, 12, 500 if i == 0 else 400, t["text"])
        p.text(180, yy, str(n), 11, 400, t["dim"], "rm")
    demos = [("Studio Control Panel", "Control Panels"), ("FlexSpace Studio", "Modes & Layers"),
             ("Sculpt Wheel", "Brushes"), ("Rigify Character Picker", "Armature Pickers"),
             ("Animation Controls", "Control Panels"), ("Viewport Shading Panel", "Control Panels")]
    for i, (name, cat) in enumerate(demos):
        col, row = i % 3, i // 3
        x, y = 218 + col * 230, 86 + row * 222
        sel = i == 1
        p.rrect(x, y, 218, 208, 10, fill=(32, 32, 35), line=(70, 120, 245) if sel else (60, 60, 66), lw=1.6 if sel else 1)
        if thumbs and thumbs.get(name) is not None:
            th, focus = thumbs[name] if isinstance(thumbs[name], tuple) else (thumbs[name], (.5, .5))
            im = cover(th, round(206 * p.k), round(132 * p.k), focus, f"demo thumb {name}")
            mask = Image.new("L", im.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=6 * p.k, fill=255)
            p.im.paste(im.convert("RGB"), (round((x + 6) * p.k), round((y + 6) * p.k)), mask)
        p.text(x + 12, y + 160, name, 12, 500, t["text"])
        p.text(x + 12, y + 180, cat, 10, 400, t["dim"])
    p.line([(11, 530), (912, 530)], (52, 52, 58), 1, caps=False)
    p.text(30, 552, "FlexSpace Studio  \u00b7  Modes & Layers", 12.5, 500, t["text"])
    p.text(30, 571, "One canvas that follows Blender's mode and the active object", 10, 400, t["dim"])
    w_button(p, t, 723, 544, 170, 34, "Open in New Window", True, 11.5, 7)
    return p



def scene_animation_controls(scale=2.0):
    """Thumbnail art for the Animation Controls demo: playback, frame, range, keying, a bouncing ball. 620 x 400."""
    t = DARK
    p = Pic(620, 400, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1)
    w_frame(p, t, 20, 20, 300, 360, "Playback")
    p.text(170, 74, "Frame 37", 24, 400, t["text"], "mm")
    labels = ["Start", "Prev", "Play", "Next", "End"]
    for i, lab in enumerate(labels):
        w_button(p, t, 34 + i * 55, 104, 52, 26, lab, lab == "Play", 10.5)
    w_num(p, t, 34, 148, 133, "Start", "1", 20)
    w_num(p, t, 173, 148, 133, "End", "120", 20)
    w_num(p, t, 34, 176, 133, "Preview", "10", 20)
    w_num(p, t, 173, 176, 133, "to", "90", 20)
    w_slider(p, t, 34, 236, 272, 37 / 120, "Frame", size=10)
    w_enum(p, t, 34, 262, 272, ["24 fps", "25 fps", "30 fps", "60 fps"], 0, 22, 10)
    p.text(34, 312, "Rate", 10, 400, t["dim"])
    w_frame(p, t, 334, 20, 266, 190, "Keying")
    w_switch(p, t, 350, 58, True, "Auto Keying", 11)
    w_enum(p, t, 348, 92, 238, ["Keyframe", "Breakdown", "Jitter"], 0, 22, 9.5)
    w_button(p, t, 348, 128, 116, 28, "Insert Keyframe", True, 10)
    w_button(p, t, 470, 128, 116, 28, "Delete Keyframe", False, 10)
    p.text(348, 182, "Keyframe type and Auto Keying", 9.5, 400, t["dim"])
    w_frame(p, t, 334, 224, 266, 156, "Ball")
    for i, (x, y) in enumerate([(360, 350), (392, 300), (424, 270), (456, 262), (488, 280), (520, 320), (552, 352)]):
        p.circle(x, y, 4 if i != 3 else 0, fill=A(t["accent"], 120))
    p.line([(350, 362), (586, 362)], (80, 80, 86), 1.2, caps=False)
    p.ellipse(456, 360, 16, 3, fill=(0, 0, 0, 90))
    p.circle(456, 262, 15, fill=(236, 170, 128))
    p.circle(451, 257, 5, fill=(250, 214, 190))
    return p


def scene_viewport_shading(scale=2.0):
    """Thumbnail art for the Viewport Shading Panel demo. 620 x 400."""
    t = DARK
    p = Pic(620, 400, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1)
    w_frame(p, t, 20, 20, 290, 200, "Viewport")
    w_enum(p, t, 34, 54, 262, ["Wireframe", "Solid", "Material", "Rendered"], 1, 24, 9.5)
    w_switch(p, t, 36, 94, False, "X-Ray", 11)
    w_switch(p, t, 36, 122, True, "Cavity", 11)
    w_slider(p, t, 34, 182, 262, .5, "Wireframe Opacity", size=10)
    w_frame(p, t, 20, 234, 290, 146, "World")
    p.text(34, 272, "Colour", 11, 400, t["text"])
    w_swatch(p, t, 120, 262, 176, 20, (52, 58, 70))
    w_slider(p, t, 34, 330, 262, .35, "Strength", size=10)
    w_frame(p, t, 324, 20, 276, 200, "Camera")
    w_slider(p, t, 338, 72, 248, .45, "Focal Length", size=10)
    w_switch(p, t, 340, 98, True, "Depth of Field", 11)
    w_num(p, t, 338, 134, 248, "F-Stop", "2.8", 20)
    w_num(p, t, 338, 162, 248, "Distance", "4.5 m", 20)
    w_frame(p, t, 324, 234, 276, 146, "Render")
    w_enum(p, t, 338, 268, 248, ["EEVEE", "Workbench", "Cycles"], 0, 22, 9.5)
    w_num(p, t, 338, 302, 120, "X", "1920", 20)
    w_num(p, t, 466, 302, 120, "Y", "1080", 20)
    w_num(p, t, 338, 330, 120, "Start", "1", 20)
    w_num(p, t, 466, 330, 120, "End", "250", 20)
    return p

def scene_conditions(scale=2.0):
    """Tooltips, Visible When / Disabled When, and the broken-binding count. Logical 900 x 560."""
    t = DARK
    p = Pic(900, 560, scale, bg=t["canvas"])
    p.dots(t["dot"], 40, 1.1, 0, 0, 560, 560)
    p.rrect(0, 0, 560, 40, 0, fill=(36, 36, 39))
    p.line([(0, 40), (560, 40)], (54, 54, 58), 1, caps=False)
    p.text(16, 20, "Render Panel", 11, 500, t["text"])
    p.rrect(440, 9, 108, 22, 11, fill=(64, 48, 18), line=(214, 160, 50))
    icon(p, "warning", 457, 20, 11, (240, 190, 70), 1.2)
    p.text(469, 20, "2 broken", 10.5, 600, (245, 210, 140))
    w_frame(p, t, 40, 80, 300, 300, "Simplify")
    w_switch(p, t, 58, 118, True, "Simplify", 11.5)
    w_slider(p, t, 58, 182, 262, .55, "Max Subdivision", knob=11, size=10.5, th=7)
    w_slider(p, t, 58, 236, 262, .3, "Max Child Particles", knob=11, size=10.5, th=7)
    w_num(p, t, 58, 268, 262, "Volume Resolution", "1.00", 22, 10.5)
    w_switch(p, t, 58, 312, False, "Use Camera Culling", 11.5)
    # tooltip over the slider
    tx, ty = 190, 196
    p.soft_shadow(tx, ty, 330, 82, 8, 16, 8, 170)
    p.rrect(tx, ty, 330, 82, 8, fill=(18, 18, 20), line=(74, 74, 80))
    p.text(tx + 14, ty + 20, "Max Subdivision", 12, 600, t["text"])
    p.text(tx + 14, ty + 40, "Global maximum subdivision level", 10.5, 400, (205, 205, 210))
    p.text(tx + 14, ty + 62, "scene.render.simplify_subdivision", 10, 400, (130, 130, 136), mono=True)
    # an Edit Mode widget with a broken binding
    w_frame(p, t, 40, 400, 300, 120, "Viewport")
    w_slider(p, t, 58, 464, 262, .4, "Lens", knob=11, size=10.5)
    x0, y0, x1, y1 = 50, 432, 328, 478
    xx = x0
    while xx < x1:
        p.line([(xx, y0), (min(xx + 6, x1), y0)], (240, 180, 60), 1.3, caps=False)
        p.line([(xx, y1), (min(xx + 6, x1), y1)], (240, 180, 60), 1.3, caps=False)
        xx += 10
    for xv in (x0, x1):
        yy = y0
        while yy < y1:
            p.line([(xv, yy), (xv, min(yy + 6, y1))], (240, 180, 60), 1.3, caps=False)
            yy += 10
    p.rrect(130, 487, 120, 22, 6, fill=(40, 32, 18), line=(200, 150, 60))
    p.text(190, 498, "Path not found", 10.5, 500, (245, 205, 130), "mm")
    # sidebar: Conditions panel
    bx = 560
    p.rrect(bx, 0, 340, 560, 0, fill=(40, 40, 42))
    p.line([(bx, 0), (bx, 560)], (24, 24, 24), 2, caps=False)
    p.rrect(bx + 14, 16, 312, 30, 5, fill=(48, 48, 50))
    chev(p, bx + 28, 31, 4, "d", (200, 200, 200), 1.3)
    p.text(bx + 42, 31, "Conditions", 12, 500, (232, 232, 232))
    def field(y, label, path, status, status_col, placeholder=False):
        p.text(bx + 24, y, label, 11, 500, (220, 220, 222))
        p.rrect(bx + 24, y + 14, 230, 26, 5, fill=(30, 30, 32), line=(70, 70, 74))
        p.text(bx + 34, y + 27, path, 10, 400, (130, 130, 136) if placeholder else (225, 225, 228), mono=not placeholder)
        p.rrect(bx + 260, y + 14, 28, 26, 5, fill=(62, 62, 66))
        icon(p, "eyedropper", bx + 274, y + 27, 13, (225, 225, 230), 1.3)
        p.rrect(bx + 292, y + 14, 28, 26, 5, fill=(62, 62, 66))
        icon(p, "invert", bx + 306, y + 27, 13, (225, 225, 230), 1.2)
        if status:
            p.circle(bx + 30, y + 56, 3.5, fill=status_col)
            p.text(bx + 40, y + 56, status, 10.5, 500, status_col)
    field(78, "Visible When", "scene.render.use_simplify", "Shown now", (130, 200, 160))
    field(166, "Disabled When", "", None, None, True)
    p.rrect(bx + 14, 252, 312, 30, 5, fill=(48, 48, 50))
    chev(p, bx + 28, 267, 4, "d", (200, 200, 200), 1.3)
    p.text(bx + 42, 267, "Tooltip", 12, 500, (232, 232, 232))
    p.rrect(bx + 24, 296, 296, 64, 5, fill=(30, 30, 32), line=(70, 70, 74))
    p.text(bx + 34, 314, "Keep it low while you block", 10.5, 400, (215, 215, 218))
    p.text(bx + 34, 332, "out the shot.", 10.5, 400, (215, 215, 218))
    for i, lab in enumerate(("Transform", "Style", "Label")):
        yy = 392 + i * 38
        p.rrect(bx + 14, yy - 15, 312, 30, 5, fill=(48, 48, 50))
        chev(p, bx + 28, yy, 4, "r", (200, 200, 200), 1.3)
        p.text(bx + 42, yy, lab, 12, 500, (232, 232, 232))
    return p


def scene_binding_focus(scale=2.0):
    """The binding story only, 560 x 330: Blender's Light panel (Exposure picked with the eyedropper), the dashed
    link, the bound Exposure slider on the canvas and its data path."""
    t = DARK
    W, Hh = 560, 330
    p = Pic(W, Hh, scale, bg=t["canvas"])
    cx0 = 232
    p.dots(t["dot"], 40, 1.1, cx0, 0, W - cx0, Hh)
    # Blender's properties editor
    p.rrect(0, 0, cx0, Hh, 0, fill=(43, 43, 43))
    p.line([(cx0, 0), (cx0, Hh)], (22, 22, 22), 2, caps=False)
    p.rrect(10, 12, cx0 - 20, 28, 4, fill=(50, 50, 50))
    chev(p, 23, 26, 4, "d", (200, 200, 200), 1.3)
    p.text(36, 26, "Light", 12, 500, (230, 230, 230))
    for i, (lab, val) in enumerate((("Power", "600 W"), ("Exposure", "0.000"), ("Size", "1 m"))):
        yy = 72 + i * 38
        p.text(84, yy, lab, 11.5, 400, (205, 205, 205), "rm")
        hi = lab == "Exposure"
        p.rrect(94, yy - 11, 126, 22, 4, fill=(104, 104, 104) if hi else (84, 84, 84))
        p.text(157, yy, val, 11.5, 400, (240, 240, 240), "mm")
        if hi:
            p.rrect(89, yy - 16, 136, 32, 6, line=(245, 160, 50), lw=2)
    hy = 196
    p.soft_shadow(12, hy, 208, 58, 8)
    p.rrect(12, hy, 208, 58, 8, fill=(30, 30, 32), line=(74, 74, 80))
    icon(p, "eyedropper", 34, hy + 29, 18, (245, 170, 70), 1.7)
    p.text(54, hy + 20, "Right-click a property", 11.5, 500, (240, 240, 240))
    p.text(54, hy + 39, "anywhere in Blender", 11, 400, (170, 170, 176))
    # the canvas: the frame with the slider being bound
    fx, fw = 266, 276
    w_frame(p, t, fx, 22, fw, 150, "Key Light")
    p.text(fx + 16, 66, "Exposure", 11.5, 400, t["text"])
    w_slider(p, t, fx + 16, 92, fw - 32, .5, None, knob=12, th=8)
    cursor_free_selection(p, t, fx + 8, 78, fw - 16, 28, rot=False)
    p.rrect(fx + 40, 120, fw - 80, 24, 6, fill=(24, 24, 26), line=(70, 70, 76))
    p.text(fx + fw / 2, 132, f"{fw - 16} × 28  ·  Exposure", 11, 500, t["text"], "mm")
    # the link from the property to the widget
    pts = [(225, 110), (250, 110), (fx - 22, 92), (fx + 4, 92)]
    bez = [((1 - u) ** 3 * pts[0][0] + 3 * (1 - u) ** 2 * u * pts[1][0] + 3 * (1 - u) * u * u * pts[2][0] + u ** 3 * pts[3][0],
            (1 - u) ** 3 * pts[0][1] + 3 * (1 - u) ** 2 * u * pts[1][1] + 3 * (1 - u) * u * u * pts[2][1] + u ** 3 * pts[3][1])
           for u in np.linspace(0, 1, 25)]
    for i in range(0, 22, 4):
        p.line(bez[i:i + 3], (245, 160, 50), 2)
    p.circle(*pts[0], 4.5, fill=(245, 160, 50))
    p.circle(*pts[3], 4.5, fill=(245, 160, 50))
    # data path read-out
    p.rrect(fx, 196, fw, 62, 8, fill=(30, 30, 32), line=(60, 60, 64))
    p.text(fx + 14, 215, "DATA PATH", 10.5, 600, t["dim"], track=.08)
    p.text(fx + 14, 238, 'objects["Key"].data.exposure', 11.5, 500, (150, 190, 255), mono=True)
    p.text(fx, 290, "Shift A > From Property does the same,", 11, 400, t["dim"])
    p.text(fx, 308, "and picks the right widget.", 11, 400, t["dim"])
    return p


def gaze_eyes(p, t, cx, cy, w, h, gaze=(.45, .15), label="Gaze"):
    """The Lineal 2D pad with Look: Eyes (wg_ui.frag pad_eye, redrawn): two almond eyes on the pad, whites in the
    handle colour, accent irises (darker at the top, a dark rim), pupils, two highlights, a tapered upper lash line
    with a flick at the outer corner, a faint light rim on a dark pad and a thin lower lid. gaze: -1..1 per axis."""
    H1, H2, TILT, IRX, IRY, RANGE_Y = .70, .46, .10, .44, .54, .30
    x0, y0 = cx - w / 2, cy - h / 2
    if label:
        p.text(cx, y0 - 14, label, 12.5, 400, t["text"], "mm")
    pad = (28, 28, 30)
    p.rrect(x0, y0, w, h, 8, fill=pad, line=t["panel_line"])
    hx, hy = w / 2, h / 2
    m = .1 * min(hx, hy)
    ix, iy = hx - m, hy - m
    ex = .5 * ix
    a = min(.80 * ex, iy / .70)
    ey = -.5 * (H1 - H2) * a
    gx, gy = gaze
    n = max(math.hypot(gx, gy), 1.0)
    gxo, gyo = gx / n * (a - .75 * IRX * a), gy / n * RANGE_Y * a
    k = p.k
    PW, PH = int(round(2 * ix * k)), int(round(2 * iy * k))
    upx = 1.0 / k
    xs = (np.arange(PW) + .5) / k - ix
    ys = iy - (np.arange(PH) + .5) / k          # y up, like the shader
    X, Y = np.meshgrid(xs, ys)
    state = {"rgb": np.zeros((PH, PW, 3), np.float32), "al": np.zeros((PH, PW), np.float32)}

    def cov(d):
        return np.clip(.5 - d / upx, 0, 1)

    def over(col, a_):
        c = np.asarray(col, np.float32)[..., :3] / 255
        state["rgb"] = c * a_[..., None] + state["rgb"] * (1 - a_[..., None])
        state["al"] = a_ + state["al"] * (1 - a_)

    acc = np.array(t["accent"][:3], np.float32)
    ink = np.array([22, 22, 26], np.float32) * .78 + acc * .22 * .85
    white = np.array((246, 246, 247), np.float32)
    ct, st = math.cos(TILT), math.sin(TILT)
    for s in (1.0, -1.0):
        qx0, qy0 = (X - s * ex) * s, Y - ey
        qx, qy = ct * qx0 + st * qy0, -st * qx0 + ct * qy0
        h1, h2 = H1 * a, H2 * a
        r1, r2 = (a * a + h1 * h1) / (2 * h1), (a * a + h2 * h2) / (2 * h2)
        du = np.hypot(qx, qy - (h1 - r1)) - r1
        dl = np.hypot(qx, qy - (r2 - h2)) - r2
        eye = cov(np.maximum(du, dl))
        over(white, eye)
        rix, riy = IRX * a, IRY * a
        qix, qiy = X - (s * ex + gxo), Y - gyo
        di = (np.hypot(qix / rix, qiy / riy) - 1) * min(rix, riy)
        tt = np.clip(qiy / riy * .5 + .5, 0, 1)
        low = acc + (255 - acc) * .30
        top = acc + (ink - acc) * .55
        w_ = np.clip((tt - .15) / .8, 0, 1)
        w_ = w_ * w_ * (3 - 2 * w_)
        irisc = low[None, None, :] * (1 - w_[..., None]) + top[None, None, :] * w_[..., None]
        over(irisc, cov(di) * eye)
        over(ink, np.clip(.5 - (np.abs(di) - .05 * rix) / upx, 0, 1) * eye * .9)
        dp = (np.hypot(qix / (rix * .40), qiy / (riy * .44)) - 1) * min(rix * .40, riy * .44)
        over(ink, cov(dp) * eye)
        shade = 1 - np.clip(-du / (.42 * a), 0, 1)
        over(ink, .28 * shade * eye)
        d1 = np.hypot(qix + .34 * rix, qiy - .36 * riy) - .30 * rix
        d2 = np.hypot(qix - .32 * rix, qiy + .40 * riy) - .12 * rix
        over((255, 255, 255), .95 * cov(d1) * eye)
        over((255, 255, 255), .75 * cov(d2) * eye)
        sm = np.clip((qx + a) / (1.8 * a), 0, 1)
        sm = sm * sm * (3 - 2 * sm)
        tw = np.maximum((.06 + (.20 - .06) * sm) * a, 1.0)
        dla = np.maximum(np.maximum(np.abs(du + .15 * tw) - .5 * tw, np.abs(qx) - a), -qy - .3 * a)
        fa, fb = np.array([.86 * a, .22 * a]), np.array([1.26 * a, .36 * a])
        fab = fb - fa
        ft = np.clip(((qx - fa[0]) * fab[0] + (qy - fa[1]) * fab[1]) / fab.dot(fab), 0, 1)
        dfl = np.hypot(qx - fa[0] - fab[0] * ft, qy - fa[1] - fab[1] * ft) - np.maximum(.08 * a + (.012 - .08) * a * ft, .5)
        dlash = np.minimum(dla, dfl)
        over(acc + (255 - acc) * .55, .55 * cov(dlash - 1.25))
        over(ink, cov(dlash))
        tl = max(.035 * a, .75)
        dlo = np.maximum(np.maximum(np.abs(dl - .25 * tl) - .5 * tl, np.abs(qx - .12 * a) - .80 * a), qy - .4 * a)
        over(ink, .6 * cov(dlo))
    base = np.array(pad, np.float32) / 255
    out = state["rgb"] + base * (1 - state["al"][..., None])
    img = Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), "RGB")
    p.im.paste(img, (int(round((cx - ix) * k)), int(round((cy - iy) * k))))


# ------------------------------------------------------------------------------------------------ widget gallery
WIDGETS = [
    ("Operator", "Buttons", "Runs a Blender operator"),
    ("Custom Script", "Buttons", "Runs your own Python script"),
    ("Toggle", "Data", "Switches an on / off property"),
    ("Enum", "Data", "Picks one value of an enum or integer"),
    ("Color Swatch", "Color", "Shows a colour, opens Blender's picker"),
    ("Color Picker", "Color", "Edits a colour on the canvas"),
    ("Color Palette", "Color", "A grid of colour swatches"),
    ("Brush Picker", "Brush", "Makes one brush the active brush"),
    ("Ring Menu", "Brush", "Brushes, toggles and operators in a ring"),
    ("List", "Data", "Layers, slots and groups as rows"),
    ("Lineal Slider", "Data", "Drag along a bar to change a number"),
    ("Number Field", "Data", "A number field like Blender's own"),
    ("Label", "Graphics", "Text, or a property's value"),
    ("Image", "Graphics", "Shows a picture"),
    ("Frame", "Layout", "A titled area that holds other widgets"),
    ("Flex Box", "Layout", "Lines widgets up in a row or a column"),
    ("Group", "Layout", "Moves and resizes widgets as one"),
    ("Bone Collection Toggle", "Picker", "Shows, hides or solos a collection"),
    ("Radial Slider", "Picker", "A knob you drag to change a number"),
    ("Lineal 2D Slider", "Picker", "A pad that drives two properties"),
    ("Bone Pickers", "Picker", "Buttons and shapes that select bones"),
]


def color_wheel(px):
    S = px
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    c = (S - 1) / 2
    dx, dy = (xx - c) / c, (yy - c) / c
    r = np.sqrt(dx * dx + dy * dy)
    hue = (np.arctan2(dy, dx) / (2 * np.pi)) % 1.0
    sat = np.clip(r, 0, 1)
    i = np.floor(hue * 6).astype(int) % 6
    f = hue * 6 - np.floor(hue * 6)
    v = np.ones_like(hue)
    p_, q, tt = v * (1 - sat), v * (1 - f * sat), v * (1 - (1 - f) * sat)
    rgb = np.zeros((S, S, 3), np.float32)
    for k, (a, b, cc) in enumerate(((v, tt, p_), (q, v, p_), (p_, v, tt), (p_, q, v), (tt, p_, v), (v, p_, q))):
        m = i == k
        rgb[m, 0], rgb[m, 1], rgb[m, 2] = a[m], b[m], cc[m]
    alpha = np.clip((1 - r) * S / 2, 0, 1) * 255
    return Image.fromarray(np.dstack([rgb * 255, alpha]).astype(np.uint8), "RGBA")


def draw_widget(p, t, name, cx, cy):
    """Each widget drawn in its reference state, centred on (cx, cy), in a cell of ~ 300 x 150 logical."""
    if name == "Operator":
        w_button(p, t, cx - 85, cy - 17, 170, 34, "Render Image", True, 12.5, 6)
    elif name == "Custom Script":
        w_button(p, t, cx - 85, cy - 17, 170, 34, "Randomize Colours", False, 12.5, 6)
    elif name == "Toggle":
        w_switch(p, t, cx - 58, cy - 12, True, "Shadow", 14, 1.4)
    elif name == "Enum":
        w_enum(p, t, cx - 120, cy - 13, 240, ["EEVEE", "Workbench", "Cycles"], 0, 26, 11.5)
    elif name == "Color Swatch":
        p.text(cx - 18, cy, "Light Colour", 12.5, 400, t["text"], "rm")
        w_swatch(p, t, cx - 8, cy - 13, 120, 26, (240, 142, 40), 6)
    elif name == "Color Picker":
        p.rrect(cx - 52, cy - 64, 104, 128, 6, fill=t["panel"], line=t["panel_line"])
        wh = color_wheel(int(78 * p.k))
        p.paste(wh, cx - 47, cy - 59, 78, 78)
        p.grad(cx + 37, cy - 59, 9, 78, (240, 142, 40), (10, 10, 10), 2)
        p.circle(cx - 47 + 39 + 28, cy - 59 + 39 - 18, 3.5, line=(30, 30, 30), lw=1.2)
        p.rrect(cx - 47, cy + 24, 94, 8, 2, fill=(240, 142, 40))
        for i, (g1, g2) in enumerate((((255, 0, 0), (0, 0, 255)), ((240, 240, 240), (240, 142, 40)), ((20, 20, 20), (240, 142, 40)))):
            p.grad(cx - 40, cy + 37 + i * 8.5, 64, 5, g1, g2, 1, vertical=False)
    elif name == "Color Palette":
        cols = [(10, 10, 10), (128, 128, 128), (250, 250, 250), (228, 52, 52), (240, 142, 40), (240, 210, 60),
                (80, 190, 80), (40, 170, 190), (60, 110, 225), (140, 80, 210), (220, 100, 170), (120, 76, 50)]
        p.rrect(cx - 116, cy - 52, 232, 104, 8, fill=t["panel"], line=t["panel_line"])
        for i, c in enumerate(cols):
            x, y = cx - 108 + (i % 6) * 36.5, cy - 44 + (i // 6) * 32
            p.rrect(x, y, 32, 28, 4, fill=c)
            if i == 4:
                p.rrect(x - 2.5, y - 2.5, 37, 33, 6, line=t["accent"], lw=2)
        p.rrect(cx - 108, cy + 22 - 4, 32, 26, 4, fill=t["btn"], line=t["btn_line"])
        icon(p, "plus", cx - 92, cy + 31 - 4, 12, t["text"], 1.4)
    elif name == "Brush Picker":
        w_brush(p, t, cx - 100, cy - 24, 200, 48, "Clay Strips", 3, True, 15)
    elif name == "Ring Menu":
        rm = scene_ring_menu(1.0, core="Draw", with_dots=False, bg=t["canvas"]).out()
        rm = rm.crop((40, 90, 700, 790))
        p.paste(rm, cx - 66, cy - 70, 132, 140)
    elif name == "List":
        p.rrect(cx - 92, cy - 62, 184, 124, 7, fill=t["panel"], line=t["panel_line"])
        for i, n in enumerate(("Clay", "Teal", "Chrome")):
            yy = cy - 44 + i * 26
            if i == 1:
                p.rrect(cx - 86, yy - 12, 172, 24, 5, fill=A(t["accent"], 80), line=t["accent"], lw=1.4)
            p.circle(cx - 72, yy, 6.5, line=t["dim"], lw=1)
            p.line([(cx - 78.5, yy), (cx - 65.5, yy)], t["dim"], .9, caps=False)
            p.ellipse(cx - 72, yy, 3, 6.5, line=t["dim"], lw=.9)
            p.text(cx - 60, yy, n, 12, 400, t["text"])
        for i, ic in enumerate(("plus", "minus")):
            p.rrect(cx + 24 + i * 32, cy + 30, 28, 24, 5, fill=t["btn"], line=t["btn_line"])
            icon(p, ic, cx + 38 + i * 32, cy + 42, 11, t["text"], 1.3)
    elif name == "Lineal Slider":
        w_slider(p, t, cx - 110, cy + 10, 220, .5, "Power", knob=13, size=12, th=9)
    elif name == "Number Field":
        w_num(p, t, cx - 100, cy - 13, 200, "Location X", "1.25 m", 26, 12)
    elif name == "Label":
        p.text(cx, cy, "Frame 24", 28, 400, t["text"], "mm")
    elif name == "Image":
        s = Pic(200, 110, p.k, bg=(58, 58, 60), ss=1)
        for i in range(-12, 13):
            s.line([(100 + i * 9, 30), (100 + i * 28, 110)], (80, 80, 84), .7, caps=False)
        for j in range(1, 9):
            yy = 30 + 80 * (j / 9) ** 1.5
            s.line([(0, yy), (200, yy)], (80, 80, 84), .7, caps=False)
        s.line([(0, 70), (200, 52)], (150, 70, 70), 1, caps=False)
        s.line([(60, 110), (150, 30)], (110, 150, 70), 1, caps=False)
        s.poly([(78, 45), (122, 38), (130, 82), (86, 92)], fill=(176, 120, 80))
        s.poly([(122, 38), (140, 46), (146, 86), (130, 82)], fill=(130, 86, 56))
        s.poly([(78, 45), (96, 34), (140, 46), (122, 38)], fill=(200, 146, 106))
        s.grad(0, 0, 200, 30, (50, 50, 52), (58, 58, 60))
        p.paste(s.out(), cx - 100, cy - 55, 200, 110)
    elif name == "Frame":
        w_frame(p, t, cx - 100, cy - 60, 200, 120, "Key Light", 7, 12)
        w_switch(p, t, cx - 86, cy - 22, True, "Shadow", 11)
        w_slider(p, t, cx - 86, cy + 34, 172, .5, "Power", knob=9, size=10)
    elif name == "Flex Box":
        p.rrect(cx - 100, cy - 52, 200, 104, 6, fill=A(t["panel"], 255), line=A(t["dim"], 70))
        for i, (n, v) in enumerate((("Location X", "1.25 m"), ("Location Y", "0 m"), ("Location Z", "0 m"))):
            w_num(p, t, cx - 92, cy - 44 + i * 30, 184, n, v, 24, 11)
    elif name == "Group":
        for i, lab in enumerate(("Prev", "Play", "Next")):
            w_button(p, t, cx - 96 + i * 65, cy - 16, 62, 32, lab, lab == "Play", 12)
        cursor_free_selection(p, t, cx - 97, cy - 17, 194, 34)
        p.rrect(cx - 56, cy + 26, 112, 18, 4, fill=(24, 24, 26), line=(70, 70, 76))
        p.text(cx, cy + 35, "Group \u00b7 3 \u00b7 196 \u00d7 30", 9, 500, t["text"], "mm")
    elif name == "Bone Collection Toggle":
        w_switch(p, t, cx - 70, cy - 12, True, "Torso", 14, 1.4)
        p.circle(cx + 66, cy, 10, line=t["dim"], lw=1.3)
    elif name == "Radial Slider":
        w_knob(p, t, cx, cy - 12, 32, .65, "Head Follow", 13)
    elif name == "Lineal 2D Slider":
        p.text(cx, cy - 60, "Gaze", 12, 400, t["text"], "mm")
        p.rrect(cx - 46, cy - 46, 92, 92, 7, fill=(28, 28, 30), line=t["panel_line"])
        for i in (1, 2, 3):
            p.line([(cx - 46 + i * 23, cy - 46), (cx - 46 + i * 23, cy + 46)], (48, 48, 52), 1, caps=False)
            p.line([(cx - 46, cy - 46 + i * 23), (cx + 46, cy - 46 + i * 23)], (48, 48, 52), 1, caps=False)
        p.line([(cx + 18, cy - 46), (cx + 18, cy + 46)], A(t["accent"], 140), 1, caps=False)
        p.line([(cx - 46, cy), (cx + 46, cy)], A(t["accent"], 140), 1, caps=False)
        p.circle(cx + 18, cy, 7, fill=t["accent"], line=(255, 255, 255), lw=2)
    elif name == "Bone Pickers":
        # the real thing: a crop of the Body page of the redesigned picker (Adult Female)
        w, h = 234, 130
        im = cover(picker_page("female").crop(PICKER_BONES_BOX), round(w * p.k), round(h * p.k), what="Bone Pickers cell")
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=8 * p.k, fill=255)
        p.im.paste(im, (round((cx - w / 2) * p.k), round((cy - h / 2) * p.k)), mask)
        p.rrect(cx - w / 2, cy - h / 2, w, h, 8, line=(64, 64, 70), lw=1)


def ring_tile(W, H, core="Draw", core_at=.62):
    """A Ring Menu tile W x H px that crops into the ring (it bleeds off the top and bottom), so its brushes read
    at thumbnail size: the core at core_at of the height."""
    rm = scene_ring_menu(1.0, core=core).out()
    cx, cy = 369, 412
    y0 = int(round(cy - core_at * H))
    return rm.crop((cx - W // 2, y0, cx - W // 2 + W, y0 + H))


def make_gallery_sheet():
    """All 21 widgets on one sheet, 3 columns, names and a one-line role (from the docs table)."""
    cols, cw, ch = 3, 720, 400
    W = 2400
    rows = math.ceil(len(WIDGETS) / cols)
    head = 330
    Hh = head + rows * (ch + 24) + 96
    bg = backdrop(W, Hh, [(.15, .02, 900, 420, GOLD, .16), (.9, .55, 1100, 900, BLUE, .1)], dots=False)
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)
    wm = wordmark(44)
    img.alpha_composite(wm, (120, 96))
    d.text((120, 236), "21 widgets, ready to bind", font=font(60, 750), fill=TEXT1, anchor="ls")
    d.text((W - 120, 232), "Flex Space widgets + the Armature Picker's own", font=font(26, 400), fill=TEXT2, anchor="rs")
    gx = (W - cols * cw - (cols - 1) * 24) // 2
    for i, (name, cat, desc) in enumerate(WIDGETS):
        c, r = i % cols, i // cols
        x, y = gx + c * (cw + 24), head + r * (ch + 24)
        th_ = (ch - 84) / 2
        tile = Pic(360, th_ + 4, 2.0, bg=DARK["canvas"])
        tile.dots(DARK["dot"], 30, 1.0)
        dy = {"Radial Slider": 6, "Lineal 2D Slider": 8, "Lineal Slider": -6}.get(name, 0)
        draw_widget(tile, DARK, name, 180, th_ / 2 + dy)
        ti = tile.out()
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        card.paste(ti, (0, 0))
        # bottom caption band
        band = Image.new("RGBA", (cw, 84), (16, 16, 18, 235))
        card.alpha_composite(band, (0, ch - 84))
        cd = ImageDraw.Draw(card)
        cd.text((26, ch - 50), name, font=font(27, 600), fill=TEXT1, anchor="ls")
        cd.text((26, ch - 18), desc, font=font(20, 400), fill=TEXT2, anchor="ls")
        chip = cat.upper()
        f = font(15, 650)
        tw_ = f.getlength(chip) + 22 * 1.0 + len(chip) * 1.5
        cd.rounded_rectangle([cw - 26 - tw_, ch - 66, cw - 26, ch - 38], radius=14,
                             fill=(40, 40, 46) if cat != "Picker" else (44, 36, 62),
                             outline=(70, 70, 78) if cat != "Picker" else (120, 96, 180))
        X = cw - 26 - tw_ + 11
        for chh in chip:
            cd.text((X, ch - 52), chh, font=f, fill=(200, 200, 206) if cat != "Picker" else (200, 180, 250), anchor="lm")
            X += f.getlength(chh) + 1.5
        card = round_corners(card, 18)
        card = add_border(card, 18, (255, 255, 255, 26))
        place_with_shadow(img, card, x, y, [(30, 12, .55), (6, 2, .5)])
    return img.convert("RGB")


# ------------------------------------------------------------------------------------------------ brand: wordmark
_NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def _parse_path(d):
    toks = re.findall(r"[A-Za-z]|" + _NUM, d)
    subs, cur, pos, start, cmd, i = [], [], (0.0, 0.0), (0.0, 0.0), None, 0

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
            if cmd in "zZ":
                if cur:
                    subs.append(cur)
                cur, pos = [], start
                continue
        rel = cmd.islower()
        c = cmd.lower()
        x0, y0 = pos
        if c == "m":
            x, y = num(), num()
            pos = (x0 + x, y0 + y) if rel else (x, y)
            if cur:
                subs.append(cur)
            cur, start = [pos], pos
            cmd = "l" if rel else "L"
        elif c == "l":
            x, y = num(), num()
            pos = (x0 + x, y0 + y) if rel else (x, y); cur.append(pos)
        elif c == "h":
            x = num(); pos = (x0 + x if rel else x, y0); cur.append(pos)
        elif c == "v":
            y = num(); pos = (x0, y0 + y if rel else y); cur.append(pos)
        elif c == "c":
            v = [num() for _ in range(6)]
            if rel:
                v = [v[0] + x0, v[1] + y0, v[2] + x0, v[3] + y0, v[4] + x0, v[5] + y0]
            for u in np.linspace(0, 1, 14)[1:]:
                cur.append(((1 - u) ** 3 * x0 + 3 * (1 - u) ** 2 * u * v[0] + 3 * (1 - u) * u * u * v[2] + u ** 3 * v[4],
                            (1 - u) ** 3 * y0 + 3 * (1 - u) ** 2 * u * v[1] + 3 * (1 - u) * u * u * v[3] + u ** 3 * v[5]))
            pos = (v[4], v[5])
        else:
            raise ValueError("unsupported path command " + cmd)
    if cur:
        subs.append(cur)
    return subs


def _apply_transform(subs, tf):
    ops = re.findall(r"(translate|scale)\(([^)]*)\)", tf)
    for op, args in reversed(ops):
        a = [float(v) for v in re.findall(_NUM, args)]
        if op == "translate":
            tx, ty = a[0], (a[1] if len(a) > 1 else 0)
            subs = [[(x + tx, y + ty) for x, y in s] for s in subs]
        else:
            sx, sy = a[0], (a[1] if len(a) > 1 else a[0])
            subs = [[(x * sx, y * sy) for x, y in s] for s in subs]
    return subs


def brand_glyphs():
    """The wordmark's glyphs as lists of subpaths, in SVG units."""
    svg = BRAND_SVG.read_text(encoding="utf-8")
    center = re.search(r'id="logo-center"[^>]*transform="([^"]*)"', svg).group(1)
    out = []
    for m in re.finditer(r"<path[^>]*?\sd=\"([^\"]+)\"[^>]*?transform=\"([^\"]+)\"", svg):
        subs = _apply_transform(_parse_path(m.group(1)), m.group(2))
        subs = _apply_transform(subs, center)
        out.append(subs)
    return out


def _glyph_mask(glyphs, height, pad=0):
    pts = [p for g in glyphs for s in g for p in s]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    SS = 4
    k = height * SS / (y1 - y0)
    W, Hh = int((x1 - x0) * k) + 2 * pad * SS + 2, int(height * SS) + 2 * pad * SS + 2
    total = np.zeros((Hh, W), bool)
    for g in glyphs:
        acc = np.zeros((Hh, W), bool)
        for s in g:
            m = Image.new("L", (W, Hh), 0)
            ImageDraw.Draw(m).polygon([((x - x0) * k + pad * SS, (y - y0) * k + pad * SS) for x, y in s], fill=255)
            acc ^= np.asarray(m) > 0
        total |= acc
    m = Image.fromarray((total * 255).astype(np.uint8), "L")
    return m.resize((W // SS, Hh // SS), RS.LANCZOS)


def gradient_fill(mask, stops, angle_deg=0):
    W, Hh = mask.size
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    a = math.radians(angle_deg)
    u = xx * math.cos(a) + yy * math.sin(a)
    u = (u - u.min()) / max(1e-6, (u.max() - u.min()))
    rgb = np.zeros((Hh, W, 3), np.float32)
    xs = [s[0] for s in stops]
    for ch in range(3):
        rgb[..., ch] = np.interp(u, xs, [s[1][ch] for s in stops])
    return Image.fromarray(np.dstack([rgb, np.asarray(mask, np.float32)]).astype(np.uint8), "RGBA")


def wordmark(height):
    """The FlexSpace wordmark (cap height ~ height), brand gradient, RGBA. Height = the F's height."""
    g = brand_glyphs()
    # height of the whole word box is taller than the F (p has a descender); scale so the F is `height`
    fpts = [p for s in g[0] for p in s]
    allpts = [p for gg in g for s in gg for p in s]
    fh = max(p[1] for p in fpts) - min(p[1] for p in fpts)
    ah = max(p[1] for p in allpts) - min(p[1] for p in allpts)
    m = _glyph_mask(g, height * ah / fh)
    return gradient_fill(m, BRAND_STOPS, 0)


def f_mark(size, color_stops=None):
    """The wordmark's F alone, filling a square of `size` (RGBA)."""
    g = brand_glyphs()[:1]
    m = _glyph_mask(g, size * .9)
    sq = Image.new("L", (size, size), 0)
    sq.paste(m, ((size - m.width) // 2, (size - m.height) // 2))
    return gradient_fill(sq, color_stops or [(0, H("#F6CB82")), (.55, GOLD), (1, H("#E3A24A"))], 90)


# ------------------------------------------------------------------------------------------------ composition
def backdrop(W, Hh, glows, base=INK, dots=True, seed=3, grid_alpha=.07):
    """Near-black with soft coloured lights; (cx, cy, rx, ry, colour, strength) per glow; dithered."""
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    img = np.zeros((Hh, W, 3), np.float32) + np.array(base, np.float32)
    for cx, cy, rx, ry, col, a in glows:
        d = ((xx - cx * W) / rx) ** 2 + ((yy - cy * Hh) / ry) ** 2
        img += np.array(col, np.float32)[None, None, :] * (np.exp(-d * 1.6) * a)[..., None]
    vx, vy = (xx / W - .5) * 2, (yy / Hh - .5) * 2
    img *= (1 - .28 * np.clip((vx * vx + vy * vy) / 2, 0, 1))[..., None]
    rng = np.random.default_rng(seed)
    img += rng.uniform(-.9, .9, img.shape[:2])[..., None]
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    if dots:
        layer = Image.new("L", (W, Hh), 0)
        d = ImageDraw.Draw(layer)
        step = max(22, W // 70)
        r = max(1.0, W / 1600)
        for y in range(step // 2, Hh, step):
            for x in range(step // 2, W, step):
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        fade = np.clip(1.2 - np.sqrt(((xx / W - .62) * 1.4) ** 2 + ((yy / Hh - .5) * 1.2) ** 2) * 1.6, 0, 1)
        a = (np.asarray(layer, np.float32) * fade * grid_alpha).astype(np.uint8)
        out.paste((255, 255, 255), (0, 0), Image.fromarray(a, "L"))
    return out


def round_corners(im, r):
    im = im.convert("RGBA")
    S = 4
    m = Image.new("L", (im.width * S, im.height * S), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width * S - 1, im.height * S - 1], radius=r * S, fill=255)
    m = m.resize(im.size, RS.LANCZOS)
    a = ImageChops.multiply(im.getchannel("A"), m)
    im.putalpha(a)
    return im


def add_border(im, r, color, width=1.5, top_highlight=True):
    S = 4
    W, Hh = im.size
    lay = Image.new("RGBA", (W * S, Hh * S), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([0, 0, W * S - 1, Hh * S - 1], radius=r * S, outline=color, width=int(width * S))
    lay = lay.resize((W, Hh), RS.LANCZOS)
    out = im.copy()
    out.alpha_composite(lay)
    if top_highlight:
        hl = Image.new("RGBA", (W * S, Hh * S), (0, 0, 0, 0))
        ImageDraw.Draw(hl).rounded_rectangle([0, 0, W * S - 1, Hh * S - 1], radius=r * S, outline=(255, 255, 255, 40),
                                             width=int(width * S))
        hl = hl.resize((W, Hh), RS.LANCZOS)
        g = np.clip(1 - np.linspace(0, 1, Hh) * 6, 0, 1).astype(np.float32)
        a = (np.asarray(hl.getchannel("A"), np.float32) * g[:, None]).astype(np.uint8)
        hl.putalpha(Image.fromarray(a))
        out.alpha_composite(hl)
    return out


def window(img, r=18, title=None, header=True, header_h=None):
    """Rounded editor window around a scene: a slim header strip, border, top highlight. RGBA."""
    W, Hh = img.size
    hh = (header_h or int(round(W * .028))) if header else 0
    win = Image.new("RGBA", (W, Hh + hh), (30, 30, 33, 255))
    win.paste(img.convert("RGB"), (0, hh))
    if header:
        d = ImageDraw.Draw(win)
        d.rectangle([0, 0, W, hh], fill=(34, 34, 37))
        d.line([(0, hh - 1), (W, hh - 1)], fill=(16, 16, 18), width=max(1, hh // 24))
        rr = hh * .16
        for i, c in enumerate(((68, 68, 74), (68, 68, 74), (68, 68, 74))):
            cx = hh * .55 + i * hh * .5
            d.ellipse([cx - rr, hh / 2 - rr, cx + rr, hh / 2 + rr], fill=c)
        if title:
            f = font(hh * .42, 500)
            d.text((W / 2, hh / 2), title, font=f, fill=(170, 170, 178), anchor="mm")
    win = round_corners(win, r)
    return add_border(win, r, (255, 255, 255, 30), max(1.0, W / 1200))


def shadow_of(rgba, blur, opacity, spread=0):
    a = rgba.getchannel("A")
    if spread:
        a = a.filter(ImageFilter.MaxFilter(spread * 2 + 1))
    pad = int(blur * 3)
    big = Image.new("L", (a.width + 2 * pad, a.height + 2 * pad), 0)
    big.paste(a, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", big.size, (0, 0, 0, 0))
    sh.putalpha(big)
    return sh, pad


def place_with_shadow(canvas, card, x, y, shadows=((40, 24, .6), (8, 4, .45))):
    """Composite card at (x, y) on canvas (RGBA) under soft shadows (blur, dy, opacity)."""
    for blur, dy, op in shadows:
        sh, pad = shadow_of(card, blur, op)
        canvas.alpha_composite(sh, (int(x - pad), int(y - pad + dy))) if x - pad >= 0 and y - pad + dy >= 0 else \
            _alpha_composite_clip(canvas, sh, int(x - pad), int(y - pad + dy))
    _alpha_composite_clip(canvas, card, int(x), int(y))


def _alpha_composite_clip(canvas, im, x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.width, x + im.width), min(canvas.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    canvas.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def _coeffs(src, dst):
    M = []
    for (X, Y), (x, y) in zip(dst, src):
        M.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y])
        M.append([0, 0, 0, X, Y, 1, -y * X, -y * Y])
    return np.linalg.solve(np.array(M, float), np.array(src, float).reshape(8))


def tilt(card, width, yaw=-18, pitch=8, roll=0, f=2.2):
    """Rotate a flat card in 3D and project it. Returns (RGBA, (ox, oy)): the image and the offset of its
    centre. width = the card's width in output pixels before projection."""
    w = width
    h = width * card.height / card.width
    corners = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]], float)
    ya, pa, ra = map(math.radians, (yaw, pitch, roll))
    Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(pa), -math.sin(pa)], [0, math.sin(pa), math.cos(pa)]])
    Rz = np.array([[math.cos(ra), -math.sin(ra), 0], [math.sin(ra), math.cos(ra), 0], [0, 0, 1]])
    P = corners @ (Rz @ Ry @ Rx).T
    F = f * w
    proj = [(x * F / (F + z), y * F / (F + z)) for x, y, z in P]
    xs, ys = [p[0] for p in proj], [p[1] for p in proj]
    x0, y0 = math.floor(min(xs)) - 2, math.floor(min(ys)) - 2
    W, Hh = math.ceil(max(xs)) - x0 + 2, math.ceil(max(ys)) - y0 + 2
    SS = 2
    dst = [((x - x0) * SS, (y - y0) * SS) for x, y in proj]
    src = [(0, 0), (card.width, 0), (card.width, card.height), (0, card.height)]
    co = _coeffs(src, dst)
    out = card.transform((W * SS, Hh * SS), getattr(Image, "Transform", Image).PERSPECTIVE, tuple(co), RS.BICUBIC)
    out = out.resize((W, Hh), RS.LANCZOS)
    return out, (-x0, -y0)


def place_tilted(canvas, card, cx, cy, width, yaw, pitch, roll=0, shadow=True):
    im, (ox, oy) = tilt(card, width, yaw, pitch, roll)
    x, y = int(cx - ox), int(cy - oy)
    if shadow:
        for blur, dy, op in ((width * .05, width * .05, .7), (width * .012, width * .01, .45)):
            sh, pad = shadow_of(im, blur, op)
            _alpha_composite_clip(canvas, sh, int(x - pad + dy * .3), int(y - pad + dy))
    _alpha_composite_clip(canvas, im, x, y)


def text_block(d, x, y, lines):
    """lines: (text, size, weight, colour, gap_after). Returns the y after."""
    for s, size, wgt, col, gap in lines:
        d.text((x, y), s, font=font(size, wgt), fill=col, anchor="la")
        y += size * 1.12 + gap
    return y


def wrap(s, size, wgt, maxw):
    f = font(size, wgt)
    out, line = [], ""
    for wd in s.split():
        t = (line + " " + wd).strip()
        if f.getlength(t) > maxw and line:
            out.append(line); line = wd
        else:
            line = t
    if line:
        out.append(line)
    return out


def tracked(d, x, y, s, size, wgt, col, track=.14, anchor="ls"):
    f = font(size, wgt)
    X = x
    for ch in s:
        d.text((X, y), ch, font=f, fill=col, anchor=anchor)
        X += f.getlength(ch) + track * size
    return X


def chip(d, x, y, s, size, fg, bg, line, pad=(16, 9)):
    f = font(size, 550)
    w = f.getlength(s) + pad[0] * 2
    h = size + pad[1] * 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg, outline=line, width=max(1, size // 14))
    d.text((x + w / 2, y + h / 2 + .5), s, font=f, fill=fg, anchor="mm")
    return x + w


# ------------------------------------------------------------------------------------------------ outputs
def save(img, name, alt, kind, size_note=None, store="jpg", swap=None, extra=None):
    """Write <name>.webp (Pages) and store/<name>.<store> (Superhive) and register them."""
    OUT.mkdir(parents=True, exist_ok=True)
    STORE.mkdir(parents=True, exist_ok=True)
    files = {}
    rgb = img.convert("RGB") if img.mode != "RGBA" else img
    webp = OUT / f"{name}.webp"
    (img if img.mode == "RGBA" else rgb).save(webp, "WEBP", quality=88, method=6)
    files["webp"] = webp.relative_to(DOCS).as_posix()
    if store == "jpg":
        p = STORE / f"{name}.jpg"
        img.convert("RGB").save(p, "JPEG", quality=90, subsampling=0, optimize=True, progressive=True)
    else:
        p = STORE / f"{name}.png"
        img.save(p, "PNG", optimize=True)
    files["store"] = p.relative_to(DOCS).as_posix()
    entry = {"name": name, "kind": kind, "size": list(img.size), "alt": alt, "files": files,
             "store_url": SITE + files["store"]}
    if swap:
        entry["swap"] = swap
    if extra:
        entry.update(extra)
    REGISTRY[:] = [e for e in REGISTRY if e["name"] != name] + [entry]
    print(f"  {name}: {img.size[0]}x{img.size[1]}  webp {webp.stat().st_size // 1024} KB, {p.suffix[1:]} {p.stat().st_size // 1024} KB")


_SCENES: dict = {}


def scene(name):
    """Scenes are drawn once per run (they are reused by cards, frames and thumbnails)."""
    if name not in _SCENES:
        f = {"control_panel": lambda: scene_control_panel(DARK, 2.4).out(),
             "control_panel_light": lambda: scene_control_panel(LIGHT, 2.4).out(),
             "ring_menu": lambda: scene_ring_menu(2.0).out(),
             "picker": lambda: picker_page("male"),
             "add_widget": lambda: scene_add_widget(2.2).out(),
             "edit_mode": lambda: scene_edit_mode(2.4).out(),
             "layers": lambda: scene_layers(2.4).out(),
             "binding": lambda: scene_binding(2.2).out(),
             "presets": lambda: scene_presets(2.4, presets_thumbs()).out(),
             "demo_browser": lambda: scene_demo_browser(2.2, {"Studio Control Panel": scene("control_panel"),
                                                              "FlexSpace Studio": scene("layers"),
                                                              "Sculpt Wheel": ring_thumb(),
                                                              "Rigify Character Picker": (real("shots/picker_hero.png").crop(PICKER_HERO_EDITOR), (.5, .3)),
                                                              "Animation Controls": scene_animation_controls(2.0).out(),
                                                              "Viewport Shading Panel": scene_viewport_shading(2.0).out()}).out(),
             "conditions": lambda: scene_conditions(2.4).out()}[name]
        _SCENES[name] = f()
    return _SCENES[name]


def presets_thumbs():
    """The four preset thumbnails, each cover-cropped to its card (focus = what has to stay in view)."""
    return [(scene("control_panel"), (0, 0)), (ring_thumb(), (.5, .5)), (picker_page("female"), (.5, .22)),
            (scene("layers"), (0, 0))]


def ring_thumb():
    rm = scene("ring_menu")
    return rm.crop((0, 120, rm.width, rm.height - 60))


def gallery_scene():
    """A 4 x 3 board of widgets, for the Widgets card."""
    names = ["Operator", "Toggle", "Enum", "Lineal Slider", "Color Palette", "Brush Picker", "Number Field",
             "Radial Slider", "Color Picker", "List", "Lineal 2D Slider", "Bone Pickers"]
    p = Pic(1280, 690, 2.0, bg=DARK["canvas"])
    p.dots(DARK["dot"], 40, 1.1)
    for i, n in enumerate(names):
        c, r = i % 4, i // 4
        x, y = 20 + c * 312, 20 + r * 222
        p.rrect(x, y, 300, 210, 12, fill=(32, 32, 35), line=(52, 52, 56))
        draw_widget(p, DARK, n, x + 150, y + 92 if n != "Radial Slider" else y + 96)
        p.text(x + 150, y + 192, n, 12.5, 500, DARK["dim"], "mm")
    return p.out()


def themes_scene():
    shots = scene_themes(1.6)   # each 1446 x 880
    W, Hh = 2600, 1500
    board = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    pos = [(0, 0), (380, 200), (760, 400), (1140, 600)]
    for (name, im), (x, y) in zip(shots, pos):
        crop = im.crop((0, 0, 980, 880))
        win = window(crop, 22, name, header_h=50)
        place_with_shadow(board, win, x + 60, y + 30, [(40, 26, .7), (8, 4, .5)])
        d = ImageDraw.Draw(board)
    return board


# ---- 1: hero, social, store covers
def key_visual(W, Hh, layout="wide"):
    s = W / 2400
    bg = backdrop(W, Hh, [(.16, .2, 1150 * s, 760 * s, GOLD, .26), (.86, .75, 1250 * s, 900 * s, BLUE, .22),
                          (.62, .05, 700 * s, 380 * s, H("#8B5CF6"), .06)])
    img = bg.convert("RGBA")
    cards = [(window(picker_figure("male"), 26, "Armature Picker"), 0.0),
             (window(scene("ring_menu").crop((0, 40, 1480, 1600)), 26, "Sculpt Wheel"), 0.0),
             (window(scene("control_panel"), 26, "Studio Control Panel"), 0.0)]
    if layout == "wide":
        # right side stack: back to front
        place_tilted(img, cards[1][0], W * .60, Hh * .30, 640 * s, -24, 7, -2)
        place_tilted(img, cards[0][0], W * .875, Hh * .43, 540 * s, -24, 7, -2)
        place_tilted(img, cards[2][0], W * .655, Hh * .70, 1120 * s, -24, 7, -2)
        tx, ty = 150 * s, 330 * s
        maxw = 860 * s
    else:
        place_tilted(img, cards[1][0], W * .62, Hh * .30, 600 * s, -24, 7, -2)
        place_tilted(img, cards[0][0], W * .88, Hh * .44, 500 * s, -24, 7, -2)
        place_tilted(img, cards[2][0], W * .68, Hh * .71, 1040 * s, -24, 7, -2)
        tx, ty = 130 * s, 300 * s
        maxw = 800 * s
    # a soft dark scrim under the text so it always reads
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    scr = np.clip(1.15 - (xx / W) / .5, 0, 1) ** 1.6 * 200
    scrim = Image.new("RGBA", (W, Hh), INK + (0,))
    scrim.putalpha(Image.fromarray(scr.astype(np.uint8)))
    img.alpha_composite(scrim)
    # glow behind the wordmark
    wm = wordmark(int(118 * s))
    glow = Image.new("RGBA", (wm.width + 400, wm.height + 400), (0, 0, 0, 0))
    gm = wm.getchannel("A").resize(wm.size)
    gl = Image.new("L", glow.size, 0); gl.paste(gm, (200, 200))
    gl = gl.filter(ImageFilter.GaussianBlur(60 * s)).point(lambda v: int(v * .55))
    glow = Image.new("RGBA", glow.size, GOLD + (0,)); glow.putalpha(gl)
    img.alpha_composite(glow, (int(tx - 200), int(ty - 200)))
    img.alpha_composite(wm, (int(tx), int(ty)))
    d = ImageDraw.Draw(img)
    y = ty + wm.height + 70 * s
    for ln in wrap("Control panels and rig pickers, built your way.", int(66 * s), 750, maxw):
        d.text((tx, y), ln, font=font(66 * s, 750), fill=TEXT1, anchor="la")
        y += 66 * s * 1.1
    y += 26 * s
    for ln in wrap("Buttons, sliders, toggles, colours, a Ring Menu and animator pickers on a GPU canvas, "
                   "bound to any property, operator or script.", int(29 * s), 400, maxw * .94):
        d.text((tx, y), ln, font=font(29 * s, 400), fill=TEXT2, anchor="la")
        y += 29 * s * 1.5
    y += 34 * s
    x = tx
    for lab, hi in (("Blender 5.3+", True), ("Live & Edit Mode", False), ("Ring Menu", False), ("Armature Picker", False)):
        x = chip(d, x, y, lab, int(22 * s), (26, 18, 6) if hi else TEXT1, GOLD if hi else (26, 26, 30),
                 GOLD if hi else (64, 64, 72), (int(18 * s), int(10 * s))) + 12 * s
    return img.convert("RGB")


def make_hero():
    print("hero")
    save(key_visual(2400, 1200), "hero-banner",
         "FlexSpace wordmark and tagline beside a tilted stack of three canvases: a studio control panel, "
         "a sculpt Ring Menu and the Armature Picker's Body page over the Adult Male character art.", "hero")
    og = key_visual(2400, 1260)
    save(og.resize((1200, 630), RS.LANCZOS), "og-card",
         "FlexSpace: control panels and rig pickers, built your way. A control panel, a Ring Menu and a body picker.",
         "social")
    cover = key_visual(1920, 1080)
    save(cover, "superhive-cover",
         "FlexSpace for Blender 5.3+: build your own control panels, ring menus and rig pickers.", "store-cover")
    save(key_visual(2560, 1440).resize((1280, 720), RS.LANCZOS), "superhive-thumb",
         "FlexSpace: control panels and rig pickers for Blender.", "store-thumbnail")


# ---- 2: feature cards
CARDS = [
    ("live-mode", "LIVE MODE", "Your panel drives the scene", "Lights, render, playback, modifiers and materials: every "
     "control you reach for, on one canvas.", "control_panel", "Studio Control Panel", None),
    ("edit-mode", "EDIT MODE", "Lay it out like a design tool", "Drag, resize and group widgets. Smart snapping to edges, "
     "centres, equal gaps and the grid.", "edit_mode", "Studio Control Panel  \u00b7  Edit Mode", None),
    ("ring-menu", "RING MENU", "A sculpt wheel that stays put", "Brushes in the outer ring, toggles and operators in the "
     "inner ring, the name in the core.", "ring_menu", "Sculpt Wheel", None),
    ("layers", "LAYERS & MODES", "One canvas for every mode", "A layer per mode or per object. Enter Sculpt Mode and your "
     "sculpt layer is there.", "layers", "FlexSpace Studio", None),
    ("binding", "BINDING", "Bind anything with a right-click", "From Property or the eyedropper: right-click a property "
     "anywhere in Blender and the widget is bound.", "binding", "Studio Control Panel", None),
    ("themes", "THEMES", "Dark, Light or your own", "One theme sets the colours, shapes and type of every widget, on "
     "every canvas.", "themes", None, None),
    ("presets", "GLOBAL PRESETS", "Build it once, use it everywhere", "Save a canvas as a global preset, export a "
     ".flexspace file or share a team folder.", "presets", "Studio Control Panel", None),
    ("add-widget", "ADD WIDGET", "Any widget in seconds", "Shift A, type to search, Enter, and a click places it.",
     "add_widget", None, None),
    ("widgets", "WIDGETS", "Every control, bound to anything", "Buttons, toggles, sliders, fields, colours, brushes, "
     "lists, images and layout widgets.", "gallery", None, None),
    ("demo-files", "DEMO FILES", "Open a demo, take it apart", "Control panels, modes and layers, a sculpt wheel and "
     "armature pickers, each in its own window.", "demo_browser", None, None),
    ("picker", "ARMATURE PICKER", "Pose without hunting for bones", "Bone buttons, IK/FK switches, knobs and bone "
     "collection toggles. A Rigify body, hands, feet and face picker in one step.", "picker", "Armature Picker", None),
    ("conditions", "TOOLTIPS & CONDITIONS", "Panels that explain and adapt", "Tooltips say what a widget does. Visible "
     "When and Disabled When follow a property.", "conditions", "Render Panel", None),
]

CARD_ACCENT = {"picker": H("#A77BFF"), "ring-menu": BLUE, "themes": H("#F2751F")}


def card_art(key):
    if key == "gallery":
        return window(gallery_scene(), 22, "Add Widget  \u00b7  21 widgets")
    if key == "themes":
        b = themes_scene()
        x0, y0, x1, y1 = b.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        return b.crop((max(0, x0 - 20), max(0, y0 - 20), min(b.width, x1 + 20), min(b.height, y1 + 40)))
    if key == "picker":
        return window(picker_page("female"), 22, "Armature Picker  \u00b7  Body")
    if key == "ring_menu":
        rm = scene("ring_menu")
        return window(rm, 22, "Sculpt Wheel")
    if key in ("add_widget", "demo_browser"):
        im = scene(key)
        return round_corners(im.convert("RGBA"), 22)
    titles = {c[4]: c[5] for c in CARDS}
    return window(scene(key), 22, titles.get(key))


def feature_card(slug, eyebrow, title, hook, key, swap):
    """1600 x 1000: text column on the left, the art on the right (bleeding off the right edge)."""
    W, Hh = 1600, 1000
    acc = CARD_ACCENT.get(slug, BLUE)
    bg = backdrop(W, Hh, [(.06, .1, 900, 620, GOLD, .2), (.85, .6, 1000, 760, acc, .2)], grid_alpha=.06,
                  seed=sum(map(ord, slug)))
    img = bg.convert("RGBA")
    art = card_art(key)
    # art
    left = 640
    if key == "ring_menu":
        tw = 760
    elif key == "themes":
        tw = 1000
    else:
        tw = 1060
    art = art.resize((tw, int(art.height * tw / art.width)), RS.LANCZOS)
    if art.height > 880:
        th = 880
        art = art.resize((int(art.width * th / art.height), th), RS.LANCZOS)
    ax = left + (40 if key == "ring_menu" else 0)
    ay = (Hh - art.height) // 2
    if key == "themes":
        _alpha_composite_clip(img, art, ax - 20, ay)
    else:
        place_with_shadow(img, art, ax, ay, [(46, 30, .75), (10, 4, .5)])
    # text column, vertically centred
    d = ImageDraw.Draw(img)
    tx, maxw = 96, 480
    tl = wrap(title, 58, 750, maxw)
    hl = wrap(hook, 26, 400, maxw - 10)
    block = 30 + 30 + len(tl) * 64 + 26 + len(hl) * 39
    y = (Hh - block) // 2 - 20
    tracked(d, tx, y + 18, eyebrow, 19, 650, GOLD, .16)
    y += 60
    for ln in tl:
        d.text((tx, y), ln, font=font(58, 750), fill=TEXT1, anchor="la")
        y += 64
    y += 26
    for ln in hl:
        d.text((tx, y), ln, font=font(26, 400), fill=TEXT2, anchor="la")
        y += 39
    wm = wordmark(24)
    img.alpha_composite(wm, (tx, Hh - 76))
    return img.convert("RGB")

def make_cards():
    print("cards")
    for slug, eyebrow, title, hook, key, _t, swap in CARDS:
        img = feature_card(slug, eyebrow, title, hook, key, swap)
        save(img, f"card-{slug}", f"{title}. {hook}", "feature-card", swap=swap)


# ---- 3: widget gallery sheet
def make_gallery():
    print("gallery")
    sheet = make_gallery_sheet()
    save(sheet, "widget-gallery", "All 21 FlexSpace widgets on one sheet, each with its name and what it does: "
         + ", ".join(w[0] for w in WIDGETS) + ".", "gallery", store="jpg")


# ---- 3b: one tile per widget (w-<slug>), for the widgets page and the store gallery
WIDGET_ALTS = {
    "Operator": "An Operator button labelled Render Image.",
    "Custom Script": "A Custom Script button labelled Randomize Colours.",
    "Toggle": "A Toggle switch, on, labelled Shadow.",
    "Enum": "A segmented Enum: EEVEE, Workbench and Cycles, EEVEE active.",
    "Color Swatch": "A Color Swatch labelled Light Colour, showing orange.",
    "Color Picker": "A Color Picker: hue and saturation wheel, brightness bar, swatch strip and sliders.",
    "Color Palette": "A Color Palette of twelve swatches, the orange one active, and a plus button.",
    "Brush Picker": "A Brush Picker for the Clay Strips brush, active.",
    "Ring Menu": "A Ring Menu: brushes in the outer ring, toggles in the inner ring, Draw named in the core.",
    "List": "A List of three material slots, Teal active, with Add and Remove buttons.",
    "Lineal Slider": "A Lineal slider labelled Power, half way.",
    "Number Field": "A Number Field: Location X, 1.25 m, with arrows on the sides.",
    "Label": "A Label reading Frame 24.",
    "Image": "An Image widget showing a picture of a box on a ground grid.",
    "Frame": "A Frame titled Key Light holding a Shadow switch and a Power slider.",
    "Flex Box": "A vertical Flex Box of three Number Fields: Location X, Y and Z.",
    "Group": "A Group of three buttons, Prev, Play and Next, selected in Edit Mode with its handles.",
    "Bone Collection Toggle": "A Bone Collection toggle for Torso, on, with its Solo button.",
    "Radial Slider": "A Radial slider knob labelled Head Follow.",
    "Lineal 2D Slider": "A Lineal 2D pad labelled Gaze, its handle right of centre.",
    "Bone Pickers": "Bone pickers on the Body page of the Armature Picker: the hips shape picked, the arm and thigh bars, and each IK hand's diamond with its IK/FK puck, the active one named hand_ik.L.",
}


def widget_slug(name):
    return "w-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def make_widget_tiles():
    print("widgets")
    zoom = {"Color Picker": 1.4, "Ring Menu": 1.35, "Lineal 2D Slider": 1.4, "Toggle": 1.4, "Enum": 1.15,
            "Bone Pickers": 1.15, "Label": 1.1, "Frame": 1.25, "Image": 1.3}
    for name, cat, desc in WIDGETS:
        if name == "Ring Menu":
            img = ring_tile(720, 400)
        elif name == "Bone Pickers":
            img = cover(picker_page("female").crop(PICKER_BONES_BOX), 720, 400, what="w-bone-pickers")
        else:
            z = zoom.get(name, 1.3)
            tile = Pic(720 / (2.0 * z), 400 / (2.0 * z), 2.0 * z, bg=DARK["canvas"])
            tile.dots(DARK["dot"], 30 / z, 1.0 / z)
            dy = {"Radial Slider": 8, "Lineal 2D Slider": 8, "Lineal Slider": -6}.get(name, 0)
            draw_widget(tile, DARK, name, tile.w / 2, tile.h / 2 + dy)
            img = tile.out().convert("RGB").resize((720, 400), RS.LANCZOS)
        save(img, widget_slug(name), WIDGET_ALTS[name], "widget", store="png",
             extra={"widget": name, "category": cat, "role": desc})
    # the Lineal 2D pad with Look: Eyes (the picker page's gaze control)
    z = 1.4
    tile = Pic(720 / (2.0 * z), 400 / (2.0 * z), 2.0 * z, bg=DARK["canvas"])
    tile.dots(DARK["dot"], 30 / z, 1.0 / z)
    gaze_eyes(tile, DARK, tile.w / 2, tile.h / 2 + 9, 186, 96, gaze=(.5, .2))
    save(tile.out().convert("RGB").resize((720, 400), RS.LANCZOS), "w-gaze-eyes",
         "A Lineal 2D pad with Look set to Eyes, labelled Gaze: two eyes looking up and to the right.", "widget",
         store="png", extra={"widget": "Lineal 2D Slider", "category": "Picker", "role": "Gaze (Eyes)"})


# ---- 4: framed scenes (rounded window chrome + shadow, transparent background)
FRAMES = [
    ("control-panel", "control_panel", "Studio Control Panel", "A studio control panel in Live Mode: lights, render, playback, objects and a camera preview.", None),
    ("control-panel-light", "control_panel_light", "Studio Control Panel", "The same control panel with the Light appearance.", None),
    ("edit-mode", "edit_mode", "Studio Control Panel  \u00b7  Edit Mode", "Edit Mode: a frame dragged under Lighting, snapped to its left edge, the gap shown by a magenta guide.", None),
    ("ring-menu", "ring_menu", "Sculpt Wheel", "A Ring Menu: sculpt brushes in the outer ring, toggles in the inner ring, Clay Strips named in the core, page 1 of 5.", None),
    ("layers", "layers", "FlexSpace Studio", "The Sculpt layer of a canvas with a layer per mode: brushes in titled blocks, stroke, remesh and viewport controls.", None),
    ("binding", "binding", "Binding", "Binding a slider: right-click Exposure in Blender's Light properties with the eyedropper; the widget shows its data path.", None),
    ("add-widget", "add_widget", None, "The Add Widget browser: search, categories, widget cards and From Property.", None),
    ("presets", "presets", None, "The global presets menu with thumbnails, a .flexspace export and a shared presets folder.", None),
    ("demo-browser", "demo_browser", None, "The demo browser: categories, demo cards and Open in New Window.", None),
    ("conditions", "conditions", None, "A tooltip with the property's name, description and data path; Visible When and Disabled When in the sidebar; a broken binding flagged.", None),
    ("picker", "picker", "Armature Picker  \u00b7  Body", "The Body page of the Humanoid Body (Rigify) picker over the Adult Male art, in Pose Mode: the body split into regions, left blue, right red and centre yellow, the IK hands and feet with their IK/FK pucks, the Rig Settings knobs and sliders and the bone collection toggles.", None),
    ("widgets-board", "gallery", None, "Twelve FlexSpace widgets on a board: buttons, toggles, enums, sliders, colours, brushes, lists, knobs, pads and bone pickers.", None),
]


def make_frames():
    print("frames")
    for slug, key, title, alt, swap in FRAMES:
        im = gallery_scene() if key == "gallery" else scene(key)
        target = 1600 if key != "picker" else im.width     # a 1x capture: shown as it is, never blown up
        win = window(im, 22, title, header=title is not None) if title is not None else round_corners(im.convert("RGBA"), 22)
        if title is None:
            win = add_border(win, 22, (255, 255, 255, 30))
        win = win.resize((target, int(win.height * target / win.width)), RS.LANCZOS)
        pad = 90
        canvas = Image.new("RGBA", (win.width + pad * 2, win.height + pad * 2), (0, 0, 0, 0))
        place_with_shadow(canvas, win, pad, pad - 20, [(40, 28, .6), (8, 4, .45)])
        save(canvas, f"frame-{slug}", alt, "framed-scene", store="png", swap=swap)


# ---- 4b: focus crops: the part of a scene that tells the story, drawn so its UI text reads at the size the
# site shows it (a feature row's ~650 px column: about 1 logical px per CSS px, so 11-12 px text).
# (slug, maker -> Pic at scale 2, logical crop box or None, window title, alt, swap)
FOCUS = [
    ("control", lambda: scene_control_panel(DARK, 2.0, 440, {"lighting", "render", "playback_compact"}), (6, 10, 594, 436),
     "Studio Control Panel", "The Studio Control Panel in Live Mode: Lighting with Key, Fill and Rim lights, Render "
     "settings and Playback buttons, every widget bound to the scene.", None),
    ("control-light", lambda: scene_control_panel(LIGHT, 2.0, 440, {"lighting", "render", "playback_compact"}),
     (6, 10, 594, 436), "Studio Control Panel", "The same Studio Control Panel with the Light appearance.", None),
    ("binding", lambda: scene_binding_focus(2.0), None, "Binding",
     "Binding with the eyedropper: right-click Exposure in Blender's Light properties and the canvas slider is bound "
     "to it; its data path shows below.", None),
    ("conditions", lambda: scene_conditions(2.0), (0, 0, 556, 536), None,
     "A tooltip with the property's name, description and data path over a Simplify slider; the top bar counts 2 "
     "broken bindings and a widget whose path is gone is flagged Path not found.", None),
    ("layers", lambda: scene_layers(2.0, compact=True), None, "FlexSpace Studio",
     "A canvas with a layer per mode: the layer tabs, Sculpt active, and the Sculpt layer's brushes and stroke "
     "settings.", None),
    ("presets", lambda: scene_presets(2.0, presets_thumbs(), compact=True),
     (4, 0, 528, 546), None, "The Global Presets menu: four presets as thumbnails, one from the shared folder, with "
     "Save as Global Preset and Manage.", None),
    ("edit-mode", lambda: scene_edit_mode(2.0), (4, 12, 592, 606), "Studio Control Panel  \u00b7  Edit Mode",
     "Edit Mode: the Preview frame dragged under Lighting snaps to its left edge; a magenta guide and the 22 px gap "
     "show what it lined up with.", None),
    ("picker", lambda: picker_figure("male"), None, "Armature Picker  \u00b7  Body",
     "The Body page of the Armature Picker over the Adult Male art: the chest and the right foot picked, the IK hand "
     "hand_ik.L active and named, left blue, right red, centre yellow, root purple.", None),
]


def make_focus():
    print("focus crops")
    S = 2.0
    for slug, maker, box, title, alt, swap in FOCUS:
        im = maker()
        im = im.out() if isinstance(im, Pic) else im
        if box:
            im = im.crop(tuple(int(round(v * S)) for v in box))
        if title:
            win = window(im, 22, title, header_h=56)
        else:
            win = add_border(round_corners(im.convert("RGBA"), 22), 22, (255, 255, 255, 30))
        pad = 56
        canvas = Image.new("RGBA", (win.width + 2 * pad, win.height + 2 * pad), (0, 0, 0, 0))
        place_with_shadow(canvas, win, pad, pad - 14, [(22, 14, .55), (6, 3, .4)])
        save(canvas, f"focus-{slug}", alt, "focus-crop", store="png", swap=swap)


# ---- 4c: the hero art around the Studio Control Panel (store page and site home): the Armature Picker as its equal
# (Body + Face with the gaze pad, Adult Female) and three small accents: a colour picker, the brushes, the Ring Menu
# (gif-ring-menu / frame-ring-menu, made elsewhere). All real captures, cropped and placed whole, never squashed.
HERO_BODY = (345, 30, 965, 990)        # Body page: the whole figure, both IK hands and pucks, hand_ik.L named
HERO_FACE = (352, 40, 1002, 972)       # Face page: the head, ear to ear, down to the neck
HERO_GAZE = (38, 163, 314, 364)        # Face page: the Expressions panel's title and the Gaze pad (two eyes)
PICKER_TABS = (7, 8, 198, 36)          # the Body | Hands | Feet | Face tab strip (pasted with its round ends)
BRUSH_TITLE = (772, 90, 1278, 150)     # brush_picker.png: "Sculpt Brushes"
BRUSH_ROWS = (772, 214, 1278, 576)     # brush_picker.png: Draw, Clay Strips (active), Inflate/Deflate
COLOR_RING = (10, 62, 534, 525)        # color_picker_ring.png (a 2x capture): Paint Color, ring + square, colour bar
COLOR_FOOT = (10, 836, 534, 862)       # color_picker_ring.png: the same panel's bottom edge (the sliders left out)
PICKER_BG = (26, 26, 26)               # the picker canvas behind the art


def ui_card(im, r, line=(255, 255, 255, 36)):
    """A capture as a floating card: rounded corners, a hairline border and the top highlight."""
    return add_border(round_corners(im.convert("RGBA"), r), r, line, max(1.0, im.width / 500))


def hero_picker(gender="female", k=.8):
    """The Armature Picker window: the Body page's figure with the Face page beside it as a card, and the gaze pad
    (Expressions > Gaze) floating over the corner between them at full size, so the eyes read first."""
    body, face = picker_page(gender, "body"), picker_page(gender, "face")

    def scaled(im, what):
        return cover(im, round(im.width * k), round(im.height * k), what=what)

    fig = scaled(body.crop(HERO_BODY), f"hero picker body ({gender})")
    head = scaled(face.crop(HERO_FACE), f"hero picker face ({gender})")
    P, G = 26, 30
    W, Hh = P + fig.width + G + head.width + P, P + max(fig.height, head.height) + P
    inner = Image.new("RGBA", (W, Hh), PICKER_BG + (255,))
    inner.paste(fig, (P, P + (Hh - 2 * P - fig.height) // 2))
    inner.alpha_composite(round_corners(body.crop(PICKER_TABS), 8), (14, 12))
    fc = ui_card(head, 16, (255, 255, 255, 40))
    fx, fy = P + fig.width + G, P + (Hh - 2 * P - head.height) // 2
    place_with_shadow(inner, fc, fx, fy, [(18, 10, .55), (4, 2, .4)])
    inner.alpha_composite(round_corners(face.crop(PICKER_TABS), 8), (fx + 12, fy + 12))
    gaze = ui_card(face.crop(HERO_GAZE), 12, (255, 255, 255, 46))
    place_with_shadow(inner, gaze, fx - 100, Hh - P - gaze.height - 4, [(22, 14, .7), (5, 3, .5)])
    return window(inner, 22, f"Armature Picker  ·  Adult {gender.title()}", header_h=40)


def hero_brushes():
    """The Brush Picker as the Sculpt Brushes demo shows it: its title, then Draw, Clay Strips (active), Inflate."""
    src = real("shots/brush_picker.png")
    title, rows = src.crop(BRUSH_TITLE), src.crop(BRUSH_ROWS)
    im = Image.new("RGB", (rows.width, 8 + title.height + 6 + rows.height + 16), src.getpixel((BRUSH_ROWS[0] + 4, 180)))
    im.paste(title, (0, 8))
    im.paste(rows, (0, 8 + title.height + 6))
    return ui_card(im, 18)


def hero_color():
    """The Color Picker, Ring + Square: Paint Color, the hue ring, the square and the colour bar (2x capture)."""
    src = real("shots/color_picker_ring.png")
    top, foot = src.crop(COLOR_RING), src.crop(COLOR_FOOT)
    im = Image.new("RGB", (top.width, top.height + foot.height))
    im.paste(top, (0, 0))
    im.paste(foot, (0, top.height))
    return ui_card(im, 22)


def make_hero_art():
    print("hero art (store page and site home)")
    save(hero_picker("female"), "hero-picker",
         "The Armature Picker over the Adult Female art: the Body page, the hips and the left foot picked and the IK "
         "hand hand_ik.L named, beside the Face page with its Gaze pad, two eyes you drag to aim the gaze.",
         "focus-crop", store="png")
    save(hero_brushes(), "hero-brushes",
         "A Brush Picker list: Sculpt Brushes with Draw, Clay Strips (active) and Inflate/Deflate.", "focus-crop",
         store="png")
    save(hero_color(), "hero-color",
         "A Color Picker, Ring + Square: Paint Color with the hue ring, the saturation square and the colour bar.",
         "focus-crop", store="png")


# ---- 5: icons
def make_icons():
    print("icons")
    ICONS.mkdir(parents=True, exist_ok=True)

    def tile(sz, radius=.22, inset=.2):
        S = sz * 4
        t = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
        g = np.clip(1 - np.sqrt((xx - .3) ** 2 + (yy - .2) ** 2) * 1.3, 0, 1)
        base = np.stack([20 + 40 * g * .9, 18 + 28 * g * .9, 16 + 12 * g * .9], -1)
        bg = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, S - 1, S - 1], radius=S * radius, fill=255)
        t.paste(bg, (0, 0), m)
        ImageDraw.Draw(t).rounded_rectangle([0, 0, S - 1, S - 1], radius=S * radius, outline=(255, 255, 255, 34),
                                            width=max(1, S // 128))
        fm = f_mark(int(S * (1 - inset * 2)))
        o = int(S * inset)
        full = Image.new("L", (S, S), 0)
        full.paste(fm.getchannel("A"), (o, o))
        gl = full.filter(ImageFilter.GaussianBlur(S * .035)).point(lambda v: int(v * .42))
        gl = ImageChops.multiply(gl, m)
        glow = Image.new("RGBA", (S, S), GOLD + (0,)); glow.putalpha(gl)
        t.alpha_composite(glow)
        t.alpha_composite(fm, (o, o))
        return t.resize((sz, sz), RS.LANCZOS)

    big = tile(1024)
    big.save(ICONS / "icon-1024.png", optimize=True)
    tile(512).save(ICONS / "icon-512.png", optimize=True)
    tile(192).save(ICONS / "icon-192.png", optimize=True)
    # apple touch: full-bleed square (iOS rounds it)
    at = tile(180, radius=0.0001)
    at.convert("RGB").save(ICONS / "apple-touch-icon.png", optimize=True)
    # favicon: bigger F (less inset) for small sizes
    fav = [tile(s, .2, .14) for s in (16, 32, 48, 64)]
    fav[-1].save(ICONS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)], append_images=fav[:-1])
    fav[1].save(ICONS / "favicon-32.png", optimize=True)
    # the bare mark, transparent
    f_mark(1024).save(ICONS / "f-mark.png", optimize=True)
    # SVG favicon from the wordmark's own F path
    g = brand_glyphs()[0]
    pts = [p for s in g for p in s]
    x0, y0, x1, y1 = min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
    k = 64 * .72 / (y1 - y0)
    ox = (64 - (x1 - x0) * k) / 2
    oy = (64 - (y1 - y0) * k) / 2
    path = " ".join("M " + " L ".join(f"{(x - x0) * k + ox:.2f} {(y - y0) * k + oy:.2f}" for x, y in s) + " Z" for s in g)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6CB82"/><stop offset=".55" stop-color="#F0B557"/><stop offset="1" stop-color="#E3A24A"/></linearGradient></defs>
  <rect width="64" height="64" rx="14" fill="#141210"/>
  <rect x=".5" y=".5" width="63" height="63" rx="13.5" fill="none" stroke="#ffffff" stroke-opacity=".12"/>
  <path fill="url(#g)" fill-rule="evenodd" d="{path}"/>
</svg>
"""
    (ICONS / "favicon.svg").write_text(svg, encoding="utf-8")
    # wordmark PNGs for places that can't use the SVG (Superhive)
    wordmark(96).save(ICONS / "wordmark-gradient.png", optimize=True)
    for f, alt in (("icons/icon-1024.png", "FlexSpace app icon: the gold F of the wordmark on a dark rounded tile."),
                   ("icons/icon-512.png", "FlexSpace icon, 512 px."), ("icons/icon-192.png", "FlexSpace icon, 192 px."),
                   ("icons/apple-touch-icon.png", "FlexSpace touch icon, 180 px."),
                   ("icons/favicon.ico", "FlexSpace favicon (16, 32, 48, 64 px)."),
                   ("icons/favicon-32.png", "FlexSpace favicon, 32 px."),
                   ("icons/favicon.svg", "FlexSpace favicon, vector."),
                   ("icons/f-mark.png", "The F of the FlexSpace wordmark, gold, transparent background."),
                   ("icons/wordmark-gradient.png", "The FlexSpace wordmark, gold to mist gradient, transparent background.")):
        p = OUT / f
        im = Image.open(p) if p.suffix != ".svg" else None
        REGISTRY[:] = [e for e in REGISTRY if e["name"] != p.name] + [{
            "name": p.name, "kind": "icon", "size": list(im.size) if im else [64, 64], "alt": alt,
            "files": {"any": p.relative_to(DOCS).as_posix()}, "store_url": SITE + p.relative_to(DOCS).as_posix()}]
        print(f"  {f}: {p.stat().st_size // 1024} KB")


# ---- 6: the wordmark as tight vector files for the site (the brand mark itself, recoloured, never redrawn)
def make_brand():
    """assets/brand/flexspace.svg (gradient, for dark backgrounds) and flexspace-light.svg (for light ones):
    the paths of FlexSpace.svg as they are, a viewBox cropped to the letters, one gradient fill."""
    print("brand")
    out = DOCS / "assets" / "brand"
    out.mkdir(parents=True, exist_ok=True)
    svg = BRAND_SVG.read_text(encoding="utf-8")
    center = re.search(r'id="logo-center"[^>]*transform="([^"]*)"', svg).group(1)
    pts = [p for g in brand_glyphs() for s in g for p in s]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    pad = 2
    vb = f"{x0 - pad:.2f} {y0 - pad:.2f} {x1 - x0 + 2 * pad:.2f} {y1 - y0 + 2 * pad:.2f}"
    paths = []
    for m in re.finditer(r"<path[^>]*?\sd=\"([^\"]+)\"[^>]*?transform=\"([^\"]+)\"", svg):
        paths.append(f'<path d="{m.group(1)}" transform="{m.group(2)}"/>')
    variants = {
        "flexspace.svg": [(0, "#F0B557"), (.18, "#EDB967"), (.40, "#E6C187"), (.62, "#DFCAA8"), (.82, "#D8D2C8"), (1, "#D5D6D8")],
        "flexspace-light.svg": [(0, "#B06A14"), (.45, "#8A5A22"), (1, "#3A3833")],
    }
    for fname, stops in variants.items():
        st = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{(x1 - x0 + 2 * pad):.0f}" '
               f'height="{(y1 - y0 + 2 * pad):.0f}" role="img" aria-label="FlexSpace">'
               f'<defs><linearGradient id="fsg" x1="0" y1="0" x2="1" y2="0">'
               f'{st}</linearGradient></defs><g fill="url(#fsg)" transform="{center}">{"".join(paths)}</g></svg>\n')
        (out / fname).write_text(doc, encoding="utf-8")
        print(f"  {fname}: {len(doc) // 1024} KB, viewBox {vb}")


def write_registry():
    p = OUT / "graphics.json"
    old = []
    if p.exists():
        try:
            old = json.loads(p.read_text(encoding="utf-8")).get("images", [])
        except Exception:
            old = []
    names = {e["name"] for e in REGISTRY}
    merged = [e for e in old if e["name"] not in names] + REGISTRY
    order = {"hero": 0, "social": 1, "store-cover": 2, "store-thumbnail": 3, "feature-card": 4, "gallery": 5,
             "widget": 6, "framed-scene": 7, "focus-crop": 8, "icon": 9}
    merged.sort(key=lambda e: (order.get(e["kind"], 9), e["name"]))
    for e in merged:
        for k in list(e["files"]):
            pass
    data = {
        "about": "Generated by docs/_design/make_graphics.py (py -3.10). The product UI is redrawn from the curated "
                 "screenshots, which are reference only, except the Armature Picker (see below). <name>.webp is for GitHub Pages, "
                 "store/<name>.jpg|png for Superhive (no WebP or MP4 there). Paths are relative to docs/; store_url "
                 "is the absolute URL to paste in Superhive. Armature Picker art is real captures of the redesigned "
                 "picker (B3D-MySpace/marketing/flexspace shots), cropped and composed, never squashed: the run "
                 "fails if any embedded image changes its aspect.",
        "base_url": SITE,
        "images": merged,
    }
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("graphics.json:", len(merged), "entries")


def main(argv):
    groups = argv or ["brand", "icons", "hero", "cards", "gallery", "widgets", "frames", "focus", "heroart"]
    for g in groups:
        {"hero": make_hero, "cards": make_cards, "gallery": make_gallery, "widgets": make_widget_tiles,
         "frames": make_frames, "focus": make_focus, "heroart": make_hero_art, "icons": make_icons,
         "brand": make_brand}[g]()
    write_registry()
    check_aspect()


if __name__ == "__main__":
    main(sys.argv[1:])
