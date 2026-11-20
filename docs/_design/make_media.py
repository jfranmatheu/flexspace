"""Copy the curated real media (screenshots and screen recordings made in Blender) into the site.

    py -3.10 docs/_design/make_media.py                 # reads ../B3D-MySpace/marketing/flexspace/manifest.json
    py -3.10 docs/_design/make_media.py --src X:/path/to/marketing/flexspace
    py -3.10 docs/_design/make_media.py --only views    # just the 3D views (VIEWS_*), merged into media.json

Real media sits next to the redrawn art (docs/assets/img/, make_graphics.py); it does not replace it.
Only the files listed below are copied (manifest quality >= 3). Armature Picker media is the redesigned picker only
(the character-art pages: Body, Hands, Feet and Face); anything else with "picker" in its name has to be listed in
PICKER_OK to be used, so an old capture of the block-style picker can't slip in.

The 3D views (View Preview, Camera View, Viewport Mirror, Silhouette) are not in the manifest: their captures are the
Superhive marketing ones (<src>/superhive/src/captures/view_preview/, 2x stills, from capture_view_preview.sh;
<src>/superhive/reel/footage/web/, 30 fps web cuts from make_store_3d_views.py cuts). VIEWS_LOOPS, VIEWS_SHOTS and
VIEWS_WIDGETS below list them with their own titles and captions, written from the help (widgets.md, View Preview).

Writes:
  docs/assets/media/<name>.webp           stills for the Pages site (WebP)
  docs/assets/media/<name>.mp4 + .webp    loops for the Pages site (H.264, faststart, no audio) and their posters
  docs/assets/media/widgets/<w>.webp      real widget thumbnails (padded to the gallery's 9:5 card)
  docs/assets/media/store/<name>.png|jpg  stills for Superhive (no WebP there)
  docs/assets/media/store/<name>.gif      loops for Superhive (< 4 MB) + <name>-still.png (first frame)
  docs/assets/media/<name>.webp           also the Add to FlexSpace Canvas and City Builder stills (SH_SHOTS, --only sh)
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
# The 3D views (Add > Graphics > 3D Views). Paths are relative to <src>/superhive. Loops use the web cuts: the widget
# next to the part of the viewport where things change, the pointer and keys drawn in, 1280 wide, ending in a dissolve
# into the first frame (a seamless loop). Encoded at their own size.
VIEWS_LOOPS = [
    ("reel/footage/web/view_preview_overview.mp4", "view-preview-overview", "Four live 3D views on one canvas",
     "View Preview, Camera View, Viewport Mirror and Silhouette next to the 3D Viewport. Orbit the viewport and the "
     "mirror follows; click the ball and the preview and the silhouette frame it."),
    ("reel/footage/web/view_preview_target.mp4", "view-preview-target", "A close-up of the active object",
     "View Preview frames the active object: click another object in the viewport and it frames that one."),
    ("reel/footage/web/view_preview_camera.mp4", "view-preview-camera", "What the camera sees",
     "Camera View shows the scene camera's frame, with bars around it, while the camera swings round the props."),
    ("reel/footage/web/view_preview_mirror.mp4", "view-preview-mirror", "A second look at your viewport",
     "Viewport Mirror follows the 3D Viewport: orbit it one way, then the other, and the mirror moves with it."),
    ("reel/footage/web/view_preview_silhouette.mp4", "view-preview-silhouette", "Check the shape, not the shading",
     "Silhouette draws the target as one flat shape with an outline. A Toggle bound to its Silhouette switch shows "
     "the shaded view and back; then Suzanne turns and the shape follows."),
]
VIEWS_SHOTS = [
    ("src/captures/view_preview/vp_overview_canvas.png", "view-preview-canvas", "The four 3D views",
     "View Preview, Camera View, Viewport Mirror and Silhouette on one canvas, each a ready-made entry of the Add "
     "menu."),
    ("src/captures/view_preview/vp_target_collection_canvas.png", "view-preview-collection", "Frame a collection",
     "Target set to the Props collection: the preview frames the pillar, the ball and the pyramid. It is a real view "
     "of the scene, so Suzanne, close by, shows too."),
    ("src/captures/view_preview/vp_sidebar_canvas.png", "view-preview-sidebar", "View Preview settings",
     "Edit Mode, the sidebar's Widget tab: the Source (Target, Camera, Navigate), the View and the Shading."),
    ("src/captures/view_preview/vp_sidebar_silhouette_canvas.png", "view-preview-sidebar-silhouette",
     "Silhouette settings", "Scope, Color, Background and the Outline, with its Width and Outline Color."),
]
# Gallery cards (widgets.html): the widget cut from a still of it alone, with the canvas around it, 9:5.
VIEWS_WIDGETS = [
    ("src/captures/view_preview/vp_target_suzanne_canvas.png", "view-preview", "View Preview",
     "View Preview framing the active object, Suzanne."),
    ("src/captures/view_preview/vp_camera_letterbox_canvas.png", "camera-view", "Camera View",
     "Camera View: the scene camera's 2.39 : 1 frame with bars above and below."),
    ("src/captures/view_preview/vp_mirror_canvas.png", "viewport-mirror", "Viewport Mirror",
     "Viewport Mirror: the 3D Viewport's view, grid and outline included."),
    ("src/captures/view_preview/vp_silhouette_canvas.png", "silhouette", "Silhouette",
     "Silhouette: the active object as a flat white shape with an orange outline."),
]

# Add to FlexSpace Canvas and the City Builder demo: 3440 x 1361 window shots of the shipped demo
# (<src>/superhive/src/captures/city_builder/, take_city_menu_shots.py through capture_city_menu.sh). The crops leave
# out the top bar (the Blender logo) and the status bar. (file, crop box, name, title, caption), captions from the help
# (binding.md, Add to FlexSpace Canvas; demo_files.md, City Builder).
SH_SHOTS = [
    ("src/captures/city_builder/menu_prop_submenu.png", (2330, 250, 3425, 1178), "add-to-canvas-property",
     "Add to FlexSpace Canvas on a property",
     "Right-click the Sea modifier's Water Level and choose Add to FlexSpace Canvas: City Builder, the canvas used "
     "last, comes first with its current page, then the other canvases' pages and New Canvas..."),
    # (The two menus cut out of menu_op_submenu.png, 16:10: make_store_city_menu.py --menus.)
    ("src/captures/city_builder/menu_op_menus.png", None, "add-to-canvas-button",
     "Add to FlexSpace Canvas on a button",
     "Right-click Render Image in the Render menu: the same entry adds an Operator button that runs it."),
    ("src/captures/city_builder/menu_result_zoom_live.png", (20, 360, 1190, 812), "add-to-canvas-result",
     "On the page, bound",
     "Both widgets went to a free spot in the part of the City Builder page in view: a Water Level slider bound to "
     "the Sea modifier and a Render button."),
    ("src/captures/city_builder/city_golden.png", (0, 40, 3440, 1322), "city-builder", "City Builder",
     "The City Builder demo as it opens: the canvas in Live Mode next to the 3D Viewport in Material Preview with the "
     "scene's lights and world, at golden hour."),
    ("src/captures/city_builder/city_night.png", (0, 40, 3440, 1322), "city-builder-night", "Nightfall",
     "Nightfall dragged to the end: the sun has set, the windows and the street lamps are lit and the sky is night."),
]
SH_DAY_NIGHT = ("src/captures/city_builder/city_day.png", "src/captures/city_builder/city_night.png",
                (1410, 82, 3405, 1322), "city-builder-day-night", "Six Geometry Nodes systems, one canvas",
                "The island city of the City Builder demo with Nightfall at 0 (left) and at 1 (right).")

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


def widget_box(im: Image.Image, top=120) -> tuple[int, int, int, int]:
    """The widget's rectangle on a still of one widget on the canvas: the longest run of rows (then columns) that
    differ from the canvas colour over a long stretch (the canvas dots are single specks, a toggle is short). The
    canvas is neutral grey, so even a dark widget (a Silhouette's tinted background) stands out from it."""
    im = im.convert("RGB")
    w, h = im.size
    bg = im.getpixel((40, top + 30))
    px = im.load()

    def off(x, y):
        p = px[x, y]
        return max(abs(p[0] - bg[0]), abs(p[1] - bg[1]), abs(p[2] - bg[2])) > 2

    def runs(n, hits):
        best, start = (0, 0), None
        for i in range(n + 1):
            on = i < n and hits(i)
            if on and start is None:
                start = i
            elif not on and start is not None:
                if i - start > best[1] - best[0]:
                    best = (start, i)
                start = None
        return best

    y0, y1 = runs(h, lambda y: y >= top and sum(off(x, y) for x in range(16, w - 16, 4)) > w // 16)
    x0, x1 = runs(w, lambda x: 16 <= x < w - 16 and sum(off(x, y) for y in range(y0, y1, 4)) > (y1 - y0) // 16)
    return x0, y0, x1, y1


def card_crop(im: Image.Image, box, size=(720, 400), top=120, pitch=92, clean=(20, 140)) -> Image.Image:
    """A 9:5 card centred on box, with canvas around it, scaled uniformly to size (never stretched). Where the
    editor is too narrow (a tall widget), the canvas around it is extended with its own dot grid: one grid cell
    (pitch px, taken at clean, an empty spot) repeated in step with the capture's grid, so the dots run on."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    # more room above than below: the card's "In Blender" badge sits top left, clear of the widget's name
    mt, mb, mx = round(0.25 * bh), round(0.12 * bh), round(0.11 * bh)
    k = max((bh + mt + mb + 4) // 5, (bw + 2 * mx + 8) // 9)
    cw, ch = 9 * k, 5 * k
    # the area of the capture that is canvas (no header, edges or scroll bars); the rest is dot grid
    ax0, ay0, ax1, ay1 = 6, top + 4, im.width - 14, im.height - 16
    cx = (x0 + x1) // 2
    left = min(max(cx - cw // 2, ax0), ax1 - cw) if cw <= ax1 - ax0 else cx - cw // 2
    upper = y0 - mt - (ch - bh - mt - mb) // 2
    card = Image.new("RGB", (cw, ch))
    cell = im.crop((clean[0], clean[1], clean[0] + pitch, clean[1] + pitch))
    ox, oy = (clean[0] - left) % pitch - pitch, (clean[1] - upper) % pitch - pitch
    for ty in range(oy, ch, pitch):
        for tx in range(ox, cw, pitch):
            card.paste(cell, (tx, ty))
    sx0, sy0, sx1, sy1 = max(left, ax0), max(upper, ay0), min(left + cw, ax1), min(upper + ch, ay1)
    card.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - left, sy0 - upper))
    check_ratio(card.size, size)
    return card.resize(size, getattr(Image, "Resampling", Image).LANCZOS)


def check_ratio(a, b):
    if abs(a[0] / a[1] - b[0] / b[1]) > 0.002:
        raise SystemExit(f"aspect change {a} -> {b}")


def make_views(src: Path, reg: dict, tmp: Path):
    """The 3D views: loops, stills and the four gallery cards (see VIEWS_*). src = marketing/flexspace."""
    sh = src / "superhive"
    for f, name, title, caption in VIEWS_LOOPS:
        clip = sh / f
        if not clip.is_file():
            raise SystemExit(f"missing: {clip} (run superhive/src/make_store_3d_views.py cuts)")
        mp4 = OUT / f"{name}.mp4"
        run("ffmpeg", "-y", "-v", "error", "-i", str(clip), "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-crf", "24", "-preset", "slow", "-tune", "animation", "-movflags", "+faststart", str(mp4))
        frame = tmp / f"{name}.png"
        run("ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(frame))
        poster = Image.open(frame)
        w, h = poster.size
        save_webp(poster, OUT / f"{name}.webp", q=80)
        reg["items"][name] = {"kind": "loop", "file": f"superhive/{f}", "title": title, "caption": caption,
                              "w": w, "h": h, "mp4": rel(mp4), "poster": rel(OUT / f"{name}.webp")}
    for f, name, title, caption in VIEWS_SHOTS:
        im = Image.open(sh / f).convert("RGB")
        web = fit(im)
        if web.size != im.size:
            check_ratio(im.size, web.size)
        save_webp(web, OUT / f"{name}.webp", q=84)
        reg["items"][name] = {"kind": "shot", "file": f"superhive/{f}", "title": title, "caption": caption,
                              "w": web.width, "h": web.height, "webp": rel(OUT / f"{name}.webp")}
    for f, wid, title, caption in VIEWS_WIDGETS:
        im = Image.open(sh / f).convert("RGB")
        card = card_crop(im, widget_box(im))
        out = WIDGETS / f"{wid}.webp"
        save_webp(card, out, q=88)
        reg["items"][f"w-{wid}"] = {"kind": "widget", "file": f"superhive/{f}", "title": title, "caption": caption,
                                    "w": card.width, "h": card.height, "webp": rel(out)}


def make_sh_shots(src: Path, reg: dict):
    """Add to FlexSpace Canvas and the City Builder (SH_SHOTS, SH_DAY_NIGHT). src = marketing/flexspace."""
    sh = src / "superhive"
    for f, box, name, title, caption in SH_SHOTS:
        if not (sh / f).is_file():
            raise SystemExit(f"missing: {sh / f} (run superhive/src/capture_city_menu.sh)")
        im = Image.open(sh / f).convert("RGB")
        im = fit(im.crop(box) if box else im)
        save_webp(im, OUT / f"{name}.webp", q=84)
        reg["items"][name] = {"kind": "shot", "file": f"superhive/{f}", "title": title, "caption": caption,
                              "w": im.width, "h": im.height, "webp": rel(OUT / f"{name}.webp")}
    fd, fn, box, name, title, caption = SH_DAY_NIGHT
    import numpy as np
    d = fit(Image.open(sh / fd).convert("RGB").crop(box), 1600)
    n = fit(Image.open(sh / fn).convert("RGB").crop(box), 1600)
    w, h = d.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.clip((xx - w * (.56 - .16 * yy / h)) / 40.0 + .5, 0, 1)[..., None]
    im = Image.fromarray((np.asarray(d, np.float32) * (1 - a) + np.asarray(n, np.float32) * a).astype(np.uint8))
    save_webp(im, OUT / f"{name}.webp", q=82)
    reg["items"][name] = {"kind": "shot", "file": f"superhive/{fd} + {fn}", "title": title, "caption": caption,
                          "w": w, "h": h, "webp": rel(OUT / f"{name}.webp")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--only", choices=["views", "sh"],
                    help="views: only the 3D views; sh: only Add to FlexSpace Canvas and the City Builder (SH_SHOTS); "
                         "merged into the current media.json")
    a = ap.parse_args()
    src = a.src
    if a.only == "sh":
        reg = json.loads((OUT / "media.json").read_text(encoding="utf-8"))
        make_sh_shots(src, reg)
        (OUT / "media.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{len(SH_SHOTS) + 1} items: " + ", ".join(n for _f, _b, n, _t, _c in SH_SHOTS) + ", " + SH_DAY_NIGHT[3])
        return
    if a.only == "views":
        for d in (OUT, WIDGETS):
            d.mkdir(parents=True, exist_ok=True)
        reg = json.loads((OUT / "media.json").read_text(encoding="utf-8"))
        tmp = Path(tempfile.mkdtemp(prefix="fsmedia-"))
        try:
            make_views(src, reg, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        (OUT / "media.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
        n = sum(1 for k, v in reg["items"].items() if v["file"].startswith("superhive/"))
        print(f"{n} 3D-view items, assets/media "
              f"{sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) / 1e6:.1f} MB")
        return
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
        make_views(src, reg, tmp)
        make_sh_shots(src, reg)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    (OUT / "media.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    store = sum(p.stat().st_size for p in STORE.rglob("*") if p.is_file())
    print(f"{len(reg['items'])} items, assets/media {total / 1e6:.1f} MB (store {store / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
