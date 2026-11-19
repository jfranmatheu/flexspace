"""Copy the curated real media (screenshots and screen recordings made in Blender) into the site.

    py -3.10 docs/_design/make_media.py                 # reads ../B3D-MySpace/marketing/flexspace/manifest.json
    py -3.10 docs/_design/make_media.py --src X:/path/to/marketing/flexspace

Real media sits next to the redrawn art (docs/assets/img/, make_graphics.py); it does not replace it.
Only the files listed below are copied (manifest quality >= 3). Armature Picker media is the redesigned picker only
(the character-art pages: Body, Hands, Feet and Face); anything else with "picker" in its name has to be listed in
PICKER_OK to be used, so an old capture of the block-style picker can't slip in.

Writes:
  docs/assets/media/<name>.webp           stills for the Pages site (WebP)
  docs/assets/media/<name>.mp4 + .webp    loops for the Pages site (H.264, faststart, no audio) and their posters
  docs/assets/media/widgets/<w>.webp      real widget thumbnails (padded to the gallery's 9:5 card)
  docs/assets/media/store/<name>.png|jpg  stills for Superhive (no WebP there)
  docs/assets/media/store/<name>.gif      loops for Superhive (< 4 MB) + <name>-still.png (first frame)
  docs/assets/media/media.json            registry: title, caption (from the manifest), size and files of each item
Needs Pillow and ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
OUT = DOCS / "assets" / "media"
STORE = OUT / "store"
WIDGETS = OUT / "widgets"
DEFAULT_SRC = DOCS.parent.parent / "B3D-MySpace" / "marketing" / "flexspace"

GIF_LIMIT = 4 * 1024 * 1024
MAX_W = 1920

# (manifest file, output name, store copy?)
LOOPS = [
    ("gifs/live_mode.gif", "live-mode", True),
    ("gifs/add_panel.gif", "add-panel", True),
    ("gifs/sculpt_wheel.gif", "sculpt-wheel", True),
    ("gifs/studio_modes.gif", "studio-modes", True),
    ("gifs/edit_layout.gif", "edit-layout", True),
    ("gifs/from_property.gif", "from-property", True),
    ("gifs/lineal_slider.gif", "lineal-slider", False),
    ("gifs/themes.gif", "themes", True),
    # the redesigned Armature Picker (Rigify Character Picker demo, rig controls hidden where it says so)
    ("gifs/picker_select_transform.gif", "picker-select-transform", True),
    ("gifs/picker_face_gaze.gif", "picker-face-gaze", True),
    ("gifs/picker_hands_curl.gif", "picker-hands-curl", True),
    ("gifs/picker_pages.gif", "picker-pages", True),
    ("gifs/picker_ikfk.gif", "picker-ikfk", True),
    ("gifs/picker_gaze.gif", "picker-gaze", False),
    ("gifs/picker_pose.gif", "picker-pose", False),
    ("gifs/picker_face.gif", "picker-face", False),
    ("gifs/picker_mirror.gif", "picker-mirror", False),
]
SHOTS = [
    ("shots/control_panel_dark.png", "control-panel-dark", True),
    ("shots/control_panel_light.png", "control-panel-light", True),
    ("shots/control_panel_dark_area.png", "control-panel-dark-area", False),
    ("shots/control_panel_light_area.png", "control-panel-light-area", False),
    ("shots/flexspace_studio_sculpt.png", "studio-sculpt", True),
    ("shots/flexspace_studio_texture_paint.png", "studio-texture-paint", True),
    ("shots/flexspace_studio_object.png", "studio-object", False),
    ("shots/flexspace_studio_look_dev.png", "studio-look-dev", False),
    ("shots/flexspace_studio_weight_paint.png", "studio-weight-paint", True),
    ("shots/flexspace_studio_draw.png", "studio-draw", False),
    ("shots/features/layer_tabs_full.png", "layer-tabs", True),
    ("shots/features/layers_panel_full.png", "layers-panel", False),
    ("shots/features/ring_menu_inner.png", "ring-menu-inner", True),
    ("shots/features/ring_menu_page.png", "ring-menu-page", True),
    ("shots/features/ring_menu_canvas.png", "ring-menu-canvas", False),
    ("shots/features/add_browser_full.png", "add-browser", True),
    ("shots/features/add_browser_search.png", "add-browser-search", True),
    ("shots/features/add_browser_data.png", "add-browser-data", False),
    ("shots/features/add_menu.png", "add-menu", False),
    ("shots/features/snapping_guides.png", "snapping-guides", True),
    ("shots/features/selection_bar.png", "selection-bar", True),
    ("shots/features/selection_handles.png", "selection-handles", False),
    ("shots/features/minimap_canvas.png", "minimap", False),
    ("shots/features/layout_layer.png", "layout-widgets", False),
    ("shots/features/flex_box.png", "flex-box", False),
    ("shots/features/frames.png", "frames", False),
    ("shots/features/group.png", "group", False),
    ("shots/features/from_property_full.png", "from-property-shot", False),
    ("shots/binding_eyedropper.png", "binding-eyedropper", True),
    ("shots/binding_data_path.png", "binding-data-path", True),
    ("shots/features/broken_bindings.png", "broken-bindings", True),
    ("shots/features/top_bar_status.png", "top-bar-status", False),
    ("shots/features/theme_sunset.png", "theme-sunset", True),
    ("shots/features/theme_violet.png", "theme-violet", False),
    ("shots/features/theme_light.png", "theme-light", False),
    ("shots/features/theme_menu.png", "theme-menu", False),
    ("shots/features/presets_menu.png", "presets-menu", True),
    ("shots/features/top_bar_preset.png", "top-bar-preset", False),
    ("shots/features/library_full.png", "library", True),
    ("shots/features/empty_state_card.png", "empty-state", True),
    # the redesigned Armature Picker: every page of both body charts (whole pages, Live Mode), and the demos
    ("shots/picker_layer_female_body.png", "picker-layer-female-body", True),
    ("shots/picker_layer_female_face.png", "picker-layer-female-face", True),
    ("shots/picker_layer_female_hands.png", "picker-layer-female-hands", True),
    ("shots/picker_layer_female_feet.png", "picker-layer-female-feet", True),
    ("shots/picker_layer_male_body.png", "picker-layer-male-body", True),
    ("shots/picker_layer_male_face.png", "picker-layer-male-face", True),
    ("shots/picker_layer_male_hands.png", "picker-layer-male-hands", True),
    ("shots/picker_layer_male_feet.png", "picker-layer-male-feet", True),
    ("shots/picker_hero.png", "picker-hero", True),
    ("shots/picker_face_closeup.png", "picker-face-closeup", True),
    ("shots/picker_pose_body.png", "picker-pose-body", False),
    ("shots/picker_pose_hands.png", "picker-pose-hands", False),
    ("shots/picker_pose_feet.png", "picker-pose-feet", False),
    ("shots/picker_pose_face.png", "picker-pose-face", False),
    ("shots/picker_male_body.png", "picker-male-body", False),
    ("shots/picker_female_body.png", "picker-female-body", False),
    ("shots/picker_hands.png", "picker-hands", False),
    ("shots/picker_feet.png", "picker-feet", False),
    ("shots/picker_humanoid_face.png", "picker-humanoid-face", False),
    ("shots/picker_edit_snapping.png", "picker-edit-snapping", False),
    ("shots/picker_edit_selected.png", "picker-edit-selected", False),
]
# shots/widgets/<file>.png -> the gallery id on widgets.html
WIDGET_SHOTS = {
    "operator": "operator", "custom_script": "custom-script", "toggle": "toggle", "enum": "enum",
    "color_swatch": "color-swatch", "color_picker": "color-picker", "color_palette": "color-palette",
    "brush_picker": "brush-picker", "ring_menu": "ring-menu", "list": "list", "slider_lineal": "lineal-slider",
    "number_field": "number-field", "label": "label", "image": "image", "frame": "frame", "flex_box": "flex-box",
    "group": "group",
    # the picker's own widgets
    "bone_collection_toggle": "bone-collection-toggle", "slider_radial": "radial-slider",
    "slider_lineal_2d": "lineal-2d-slider", "bone_pickers": "bone-pickers",
}
# Captures of the redesigned picker (character art, Face page): the only picker media allowed.
PICKER_OK = {f for f, _n, _s in LOOPS + SHOTS if "picker" in f} | {
    f"shots/widgets/{w}.png" for w in ("bone_collection_toggle", "slider_radial", "slider_lineal_2d", "bone_pickers")}


def is_picker(entry) -> bool:
    return "picker_" in entry["file"] or "armature-picker" in entry.get("tags", [])         or entry.get("feature") == "armature-picker"


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def save_webp(im: Image.Image, path: Path, q=84):
    """The smaller of a lossy (q) and a lossless encode: flat UI crops are often smaller and sharper lossless."""
    im = im.convert("RGB")
    lossy = path.with_suffix(".lossy.webp")
    im.save(lossy, "WEBP", quality=q, method=6)
    im.save(path, "WEBP", lossless=True, quality=100, method=6)
    if lossy.stat().st_size < path.stat().st_size:
        lossy.replace(path)
    else:
        lossy.unlink()


def fit(im: Image.Image, max_w=MAX_W) -> Image.Image:
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), getattr(Image, "Resampling", Image).LANCZOS)
    return im


def store_still(im: Image.Image, base: Path) -> Path:
    """JPG for big screenshots (smaller), PNG for UI crops (crisp text). Returns the file written."""
    im = im.convert("RGB")
    if im.width >= 1400:
        out = base.with_suffix(".jpg")
        im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    else:
        out = base.with_suffix(".png")
        im.save(out, "PNG", optimize=True)
    return out


def rel(p: Path) -> str:
    return p.relative_to(DOCS).as_posix()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    a = ap.parse_args()
    src = a.src
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    by_file = {e["file"]: e for e in manifest["images"]}
    for d in (OUT, STORE, WIDGETS):
        d.mkdir(parents=True, exist_ok=True)
    reg = {"source": "B3D-MySpace/marketing/flexspace/manifest.json", "items": {}}

    def entry_for(f):
        e = by_file.get(f)
        if e is None:
            raise SystemExit(f"not in the manifest: {f}")
        if e["quality"] < 3 or (is_picker(e) and f not in PICKER_OK):
            raise SystemExit(f"not allowed (quality < 3, or not a redesigned-picker capture): {f}")
        return e

    tmp = Path(tempfile.mkdtemp(prefix="fsmedia-"))
    try:
        for f, name, store in LOOPS:
            e = entry_for(f)
            gif = src / f
            mp4 = OUT / f"{name}.mp4"
            if e.get("video") and (src / e["video"]).is_file():
                run("ffmpeg", "-y", "-v", "error", "-i", str(src / e["video"]), "-an", "-c", "copy",
                    "-movflags", "+faststart", str(mp4))
            else:
                run("ffmpeg", "-y", "-v", "error", "-i", str(gif), "-an", "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=15", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "22", "-preset", "slow", "-movflags", "+faststart", str(mp4))
            frame = tmp / f"{name}.png"
            run("ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(frame))
            poster = Image.open(frame)
            w, h = poster.size
            save_webp(fit(poster, 1280), OUT / f"{name}.webp", q=80)
            item = {"kind": "loop", "file": f, "title": e["title"], "caption": e["caption"], "w": w, "h": h,
                    "mp4": rel(mp4), "poster": rel(OUT / f"{name}.webp")}
            if store:
                g = Image.open(gif)
                gw, gh = g.size
                if gif.stat().st_size > GIF_LIMIT:
                    raise SystemExit(f"{f} is over 4 MB: re-encode it before use")
                shutil.copyfile(gif, STORE / f"{name}.gif")
                g.seek(0)
                g.convert("RGB").save(STORE / f"{name}-still.png", "PNG", optimize=True)
                item.update(gif=rel(STORE / f"{name}.gif"), still=rel(STORE / f"{name}-still.png"), gw=gw, gh=gh)
            reg["items"][name] = item

        for f, name, store in SHOTS:
            e = entry_for(f)
            im = Image.open(src / f).convert("RGB")
            web = fit(im)
            save_webp(web, OUT / f"{name}.webp", q=84)
            item = {"kind": "shot", "file": f, "title": e["title"], "caption": e["caption"],
                    "w": web.width, "h": web.height, "webp": rel(OUT / f"{name}.webp")}
            if store:
                with Image.open(src / f) as raw:
                    palette_png = raw.format == "PNG" and raw.mode == "P" and raw.width <= 1600
                if palette_png:
                    # already a small 256-colour PNG (the picker pages): copy it as it is, crisp and light
                    for old in (STORE / f"{name}.jpg",):
                        old.unlink(missing_ok=True)
                    s = STORE / f"{name}.png"
                    shutil.copyfile(src / f, s)
                else:
                    s = store_still(fit(im, 1600), STORE / name)
                with Image.open(s) as si:
                    item.update(store=rel(s), sw=si.width, sh=si.height)
            reg["items"][name] = item

        for stem, wid in WIDGET_SHOTS.items():
            f = f"shots/widgets/{stem}.png"
            e = entry_for(f)
            im = Image.open(src / f).convert("RGB")
            bg = im.getpixel((2, 2)) if stem != "label" else im.getpixel((240, 5))
            h = round(im.width * 5 / 9)
            card = Image.new("RGB", (im.width, h), bg)
            card.paste(im, (0, (h - im.height) // 2))
            out = WIDGETS / f"{wid}.webp"
            save_webp(card, out, q=88)
            reg["items"][f"w-{wid}"] = {"kind": "widget", "file": f, "title": e["title"], "caption": e["caption"],
                                        "w": card.width, "h": card.height, "webp": rel(out)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    (OUT / "media.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    store = sum(p.stat().st_size for p in STORE.rglob("*") if p.is_file())
    print(f"{len(reg['items'])} items, assets/media {total / 1e6:.1f} MB (store {store / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
