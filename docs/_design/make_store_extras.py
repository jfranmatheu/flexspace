"""Widget thumbnails and the generated GIFs used by the Superhive fragments (docs/store/superhive/*.html).

    py -3.10 docs/_design/make_store_extras.py            # everything
    py -3.10 docs/_design/make_store_extras.py thumbs     # only the 21 widget thumbnails
    py -3.10 docs/_design/make_store_extras.py gifs       # only the GIFs

Reuses the drawing code of make_graphics.py (same widget art as the gallery sheet), so nothing here comes
from the marketing screenshots or recordings: the GIFs are rendered frame by frame from the vector widgets.

Outputs (registered in assets/img/graphics.json, merged with what make_graphics.py wrote):
  assets/img/store/w-<slug>.png                     one tile per widget, 720 x 324 (run make_graphics.py widgets first:
                                                    it writes the site's w-<slug>.webp, 720 x 400)
  assets/img/store/gif-<name>.gif + gif-<name>-still.png   motion for the store page (first frame = still)
"""
from __future__ import annotations

import sys

from PIL import Image

import make_graphics as mg
from make_graphics import DARK, Pic, draw_widget, w_frame, w_num, w_slider, w_switch


def slug(name: str) -> str:
    return name.lower().replace(" ", "-")


# ------------------------------------------------------------------------------------------------ thumbnails
def make_thumbs():
    """store/w-<slug>.png, 720 x 324 (the Superhive gallery's tile). Only the PNG: the site's w-<slug>.webp (720 x 400)
    comes from make_graphics.py widgets, so run that first; this rewrites the PNG and records its size."""
    print("widget thumbnails (store)")
    th = (400 - 84) / 2  # the gallery sheet's art height (logical)
    reg = {e["name"]: e for e in mg.REGISTRY}
    jobs = [(name, cat, desc) for name, cat, desc in mg.WIDGETS] + [("Gaze Eyes", "Picker", "")]
    for name, cat, desc in jobs:
        if name == "Ring Menu":
            img = mg.ring_tile(720, 324)
        else:
            tile = Pic(360, th + 4, 2.0, bg=DARK["canvas"])
            tile.dots(DARK["dot"], 30, 1.0)
            if name == "Gaze Eyes":
                mg.gaze_eyes(tile, DARK, 180, th / 2 + 10, 168, 86, gaze=(.5, .2))
            else:
                dy = {"Radial Slider": 6, "Lineal 2D Slider": 8, "Lineal Slider": -6}.get(name, 0)
                draw_widget(tile, DARK, name, 180, th / 2 + dy)
            img = tile.out().convert("RGB")
        slug_ = "w-" + slug(name)
        out = mg.STORE / f"{slug_}.png"
        mg.STORE.mkdir(parents=True, exist_ok=True)
        img.save(out, "PNG", optimize=True)
        e = reg.get(slug_)
        if e is not None:
            e["files"]["store"] = out.relative_to(mg.DOCS).as_posix()
            e["store_url"] = mg.SITE + e["files"]["store"]
            e["store_size"] = list(img.size)
        print(f"  {out.name}: {img.size[0]}x{img.size[1]}, {out.stat().st_size // 1024} KB")


# ------------------------------------------------------------------------------------------------ GIFs
def _save_gif(frames, durations, name, alt):
    mg.STORE.mkdir(parents=True, exist_ok=True)
    pal = [f.convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
           for f in frames]
    p = mg.STORE / f"{name}.gif"
    pal[0].save(p, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True, disposal=1)
    still = mg.STORE / f"{name}-still.png"
    frames[0].convert("RGB").save(still, "PNG", optimize=True)
    entry = {"name": name, "kind": "motion", "size": list(frames[0].size), "alt": alt,
             "files": {"store": p.relative_to(mg.DOCS).as_posix(), "still": still.relative_to(mg.DOCS).as_posix()},
             "store_url": mg.SITE + p.relative_to(mg.DOCS).as_posix(),
             "still_url": mg.SITE + still.relative_to(mg.DOCS).as_posix(),
             "frames": len(frames)}
    mg.REGISTRY[:] = [e for e in mg.REGISTRY if e["name"] != name] + [entry]
    print(f"  {name}: {frames[0].size[0]}x{frames[0].size[1]}, {len(frames)} frames, "
          f"gif {p.stat().st_size // 1024} KB, still {still.stat().st_size // 1024} KB")


def _ease(x):
    return x * x * (3 - 2 * x)


def gif_live_mode():
    """Live Mode: the Power slider dragged, the Number Field bound to the same property follows, Shadow flips."""
    frames, durs = [], []
    t = DARK
    n = 26
    for i in range(n):
        u = i / (n - 1)
        # 0..0.45 drag up, hold, 0.55..1 drag back; the toggle flips at the hold and back at the end
        if u < .45:
            v = .25 + .55 * _ease(u / .45)
        elif u < .55:
            v = .8
        else:
            v = .8 - .55 * _ease((u - .55) / .45)
        shadow = not (.42 <= u < .9)
        p = Pic(420, 210, 1.8, bg=t["canvas"])
        p.dots(t["dot"], 30, 1.0)
        w_frame(p, t, 40, 24, 340, 166, "Key Light", 8, 13)
        w_switch(p, t, 58, 62, shadow, "Shadow", 12, 1.15)
        w_num(p, t, 210, 60, 152, "Power", f"{round(v * 1000)} W", 24, 11.5)
        w_slider(p, t, 58, 150, 304, v, "Power", knob=11, size=11, th=8)
        frames.append(p.out())
        durs.append(900 if i in (0, n - 1) else 70)
    _save_gif(frames, durs, "gif-live-mode",
              "Live Mode: dragging a Lineal slider bound to a light's power. The Number Field bound to the same "
              "property follows, and the Shadow toggle flips.")


BRUSHES = ["Draw", "Clay Strips", "Clay", "Inflate/Deflate", "Blob", "Crease Polish", "Smooth", "Flatten/Contrast"]


def gif_ring_menu():
    """Ring Menu: the active brush moves around the outer ring, its name in the core."""
    frames, durs = [], []
    slots = [2, 3, 4, 5, 6, 7, 8, 9]
    for i, s in enumerate(slots):
        img = mg.scene_ring_menu(1.0, active_seg=0, active_slot=s, core=BRUSHES[i]).out()
        frames.append(img.resize((img.width * 9 // 10, img.height * 9 // 10), mg.RS.LANCZOS))
        durs.append(1100 if i == 0 else 650)
    _save_gif(frames, durs, "gif-ring-menu",
              "A Ring Menu in Live Mode: clicking brushes in the outer ring makes each one the active brush, named "
              "in the core and drawn with the accent ring.")


def main(argv):
    groups = argv or ["thumbs", "gifs"]
    import json
    reg = mg.OUT / "graphics.json"
    if reg.exists():  # keep the site entries (make_graphics.py) and update their store files
        mg.REGISTRY[:] = json.loads(reg.read_text(encoding="utf-8")).get("images", [])
    if "thumbs" in groups:
        make_thumbs()
    if "gifs" in groups:
        print("gifs")
        gif_live_mode()
        gif_ring_menu()
    mg.write_registry()


if __name__ == "__main__":
    main(sys.argv[1:])
