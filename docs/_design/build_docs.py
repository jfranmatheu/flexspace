"""Build the online documentation (docs/docs/*.html) from the add-on's help pages (help/*.md).

    py -3.10 docs/_design/build_docs.py                      # help from ../B3D-MySpace/flexspace
    py -3.10 docs/_design/build_docs.py --src X:/path/to/flexspace
    (or set FLEXSPACE_SRC)

The Markdown is converted by the add-on's own generator (src/docs_html/generator.py, standard library only, no
bpy), loaded by its path, so the site follows the same page conventions as the HTML help built into the add-on:
<!-- module: ... --> pages, <!-- only: ... --> blocks (FlexSpace ships both modules, so both kinds are kept),
%PRODUCT%, <!-- image|hero: path | caption -->, ![alt](shots/widgets/x.png) table cells, <!-- demos -->, key chips
for `Shift A`, and bold page names turned into links. This script adds the site shell (docs/_design/DESIGN.md §3.11):
top bar, left page list, right "On this page", search over a generated JSON index, dark/light, pager.

Pictures: a help picture with real media (REAL, docs/assets/media/, see make_media.py) shows that real screenshot or
loop; otherwise its generated slot (FIGURES, docs/assets/img/<slot>.webp, see graphics.json) or nothing. REAL_EXTRA
and EXTRA add more real and generated figures at the end of chosen sections. Picker art lives in the frame-picker
slot (swap = file drop); real picker media comes with the picker redesign.

Outputs (all rewritten on every run):
  docs/docs/index.html               the docs home: a card per guide
  docs/docs/<slug>.html              one page per help page
  docs/docs/search-index.json        the search index (one entry per section)
  docs/assets/css/docs.css, docs/assets/js/docs.js are hand-written and not touched here.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # docs/_design
DOCS = HERE.parent                              # docs/ (the Pages root)
OUT = DOCS / "docs"
IMG = DOCS / "assets" / "img"
WORKSPACE = DOCS.parent.parent                  # the folder that holds both repos

# ---------------------------------------------------------------------------------------------- site constants
SITE_URL = "https://franb3d.github.io/flexspace/"
ISSUES_URL = "https://github.com/franb3d/flexspace/issues"
BUG_URL = "https://github.com/franb3d/flexspace/issues/new?template=flexspace.yml"
CHANGELOG_URL = "https://github.com/franb3d/flexspace/releases"   # DESIGN §4: one constant
# DESIGN §7.1: one place for the store link, assets/js/site.js (var SUPERHIVE_URL = "..."): the site and the docs
# always agree. Empty there = no "Get it on Superhive" button here.
_SITE_JS = (DOCS / "assets" / "js" / "site.js").read_text(encoding="utf-8")
SUPERHIVE_URL = (re.search(r'var SUPERHIVE_URL = "([^"]*)"', _SITE_JS) or [None, ""])[1]
THEME_KEY = "fs-theme"      # localStorage key, shared with the rest of the site
FONTS_URL = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800"
             "&family=Inter:wght@400..700&family=JetBrains+Mono:wght@500&display=swap")

# (slug, help file, short label for the page list, group). DESIGN §4 order.
PAGES = [
    ("getting-started", "getting_started.md", "Getting Started", "Basics"),
    ("canvas", "canvas.md", "The Canvas", "Basics"),
    ("widgets", "widgets.md", "Widgets", "Basics"),
    ("color-brush", "color_brush.md", "Color & Brush", "Basics"),
    ("editing", "editing.md", "Editing Tools", "Basics"),
    ("binding", "binding.md", "Binding", "Basics"),
    ("picker", "picker.md", "Armature Picker", "Armature Picker"),
    ("rigify", "rigify.md", "Picker with Rigify", "Armature Picker"),
    ("recipes", "recipes.md", "Recipes", "Going further"),
    ("demo-files", "demo_files.md", "Demo Files", "Going further"),
    ("shortcuts", "shortcuts.md", "Shortcuts", "Going further"),
    ("troubleshooting", "troubleshooting.md", "Troubleshooting", "Going further"),
]
GROUP_INTRO = {
    "Basics": "Make a canvas, add widgets, lay them out and bind them to anything in Blender.",
    "Armature Picker": "A canvas of buttons that select the bones of your rig, saved with the armature.",
    "Going further": "Step-by-step studios, the demo files, every key, and what to do when something is off.",
}

# Help picture -> generated slot (docs/assets/img/<slot>.webp), used when REAL below has nothing for it.
# Not listed anywhere = left out.
FIGURES = {
    "shots/control_panel_dark.png": "frame-control-panel",
    "shots/control_panel_dark_area.png": "frame-control-panel",
    "shots/control_panel_light_area.png": "frame-control-panel-light",
    "shots/canvas_mode.png": "frame-layers",
    "shots/flexspace_studio_sculpt.png": "frame-layers",
    "shots/binding_eyedropper.png": "frame-binding",
    "shots/ring_menu.png": "frame-ring-menu",
    "shots/demo_browser.png": "frame-demo-browser",
    "shots/picker_edit_snapping.png": "frame-edit-mode",
    "gifs/snapping.gif": "frame-edit-mode",
    "gifs/theme.gif": "frame-control-panel-light",
    "shots/picker_pose_body.png": "frame-picker",
    "shots/picker_male_body.png": "frame-picker",
    "gifs/picker.gif": "frame-picker",
    "shots/color_picker.png": "w-color-picker",
    "shots/color_palette.png": "w-color-palette",
    "shots/brush_picker.png": "w-brush-picker",
    "shots/list_widget.png": "w-list",
    # DESIGN §1 slots not generated yet: they show up as soon as their file exists (picker ones: picker redesign).
    "shots/layer_show_when.png": "layer-tabs",
    "shots/picker_female_body.png": "picker-body",
    "shots/picker_hands.png": "picker-hands",
    "shots/picker_feet.png": "picker-feet",
    "shots/picker_pose_face.png": "picker-face",
    "shots/bug_report.png": "bug-report",
}
# Extra figures where a generated image helps: (page slug) -> [(heading text, slot)], placed at the end of that
# section (before the next heading).
EXTRA = {
    "widgets": [("The Add menu", "frame-add-widget")],
    "canvas": [("Global presets", "frame-presets")],
    "binding": [("Show, hide or disable a widget with a property", "frame-conditions")],
    "editing": [("Smart snapping", "frame-edit-mode")],
}
# Real media (docs/assets/media/<name>, made by make_media.py from the curated marketing shots and recordings).
# A help picture listed here shows the real screenshot or loop instead of the generated slot. "help" keeps the help's
# own caption (written for that very shot); "manifest" uses the manifest caption (the media differs a little from what
# the help describes). No Armature Picker media until the redesigned picker ships: those help figures keep their
# generated slot (FIGURES) or are left out.
REAL = {
    "shots/control_panel_dark.png": ("control-panel-dark", "help"),
    "shots/control_panel_dark_area.png": ("control-panel-dark-area", "help"),
    "shots/control_panel_light_area.png": ("control-panel-light-area", "help"),
    "shots/flexspace_studio_sculpt.png": ("studio-sculpt", "help"),
    "shots/flexspace_studio_texture_paint.png": ("studio-texture-paint", "help"),
    "shots/flexspace_studio_object.png": ("studio-object", "help"),
    "shots/flexspace_studio_look_dev.png": ("studio-look-dev", "help"),
    "shots/flexspace_studio_weight_paint.png": ("studio-weight-paint", "help"),
    "shots/flexspace_studio_draw.png": ("studio-draw", "help"),
    "shots/binding_eyedropper.png": ("binding-eyedropper", "help"),
    "shots/binding_data_path.png": ("binding-data-path", "help"),
    "shots/empty_state.png": ("empty-state", "manifest"),
    "shots/layer_show_when.png": ("layers-panel", "manifest"),
    "shots/ring_menu.png": ("ring-menu-inner", "manifest"),
    "gifs/theme.gif": ("themes", "manifest"),
    "shots/theme_menu.png": ("theme-menu", "manifest"),
}
# Extra real media at the end of a section: (page slug) -> [(heading text, media name)], manifest captions.
REAL_EXTRA = {
    "getting-started": [("Step 2: Add a widget", "add-panel")],
    "canvas": [("Layers and modes", "studio-modes"), ("The canvas top bar", "top-bar-status"),
               ("Global presets", "presets-menu"), ("The Library", "library")],
    "widgets": [("The Add menu", "add-browser-search"), ("Add from Property", "from-property"),
                ("Sliders", "lineal-slider"), ("Frame", "frames"), ("Flex Box", "flex-box"), ("Group", "group")],
    "binding": [("When a binding is broken", "broken-bindings")],
    "editing": [("Move, resize, rotate", "selection-handles"), ("Smart snapping", "edit-layout"),
                ("Smart snapping", "snapping-guides"), ("Selection Bar", "selection-bar"), ("Minimap", "minimap"),
                ("Themes", "theme-menu")],
    "color-brush": [("Ring Menu", "sculpt-wheel")],
    "demo-files": [("FlexSpace Studio", "studio-modes"), ("Sculpt Wheel", "ring-menu-canvas")],
}
MEDIA = DOCS / "assets" / "media"
# Table-cell thumbnails: shots/widgets/<stem>.png -> w-<widget name slug> (make_graphics.py names them by widget).
CELL_RENAME = {"slider_lineal": "lineal-slider", "slider_radial": "radial-slider",
               "slider_lineal_2d": "lineal-2d-slider"}
# The docs home's art.
HOME_ART = "frame-widgets-board"

ICON = {
    "search": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    "sun": '<svg class="i-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    "moon": '<svg class="i-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "back": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>',
    "ext": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
    "bug": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="13" rx="5"/><path d="M9 7a3 3 0 0 1 6 0M3 13h4M17 13h4M4 19l3-2M20 19l-3-2M4 7l3 2M20 7l-3 2"/></svg>',
    "book": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/></svg>',
    "chev": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>',
}


# ---------------------------------------------------------------------------------------------- sources
def load_generator(src: Path):
    path = src / "src" / "docs_html" / "generator.py"
    if not path.is_file():
        sys.exit(f"Can't find the add-on's docs generator at {path} (pass --src or set FLEXSPACE_SRC).")
    spec = importlib.util.spec_from_file_location("fs_help_generator", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def toml_value(text: str, key: str):
    m = re.search(rf'^{key}\s*=\s*(.+?)\s*(?:#.*)?$', text, re.M)
    if m is None:
        return None
    raw = m.group(1)
    if raw.startswith("["):
        return re.findall(r'"([^"]*)"', raw)
    return raw.strip().strip('"')


def product_facts(src: Path) -> dict:
    manifest = (src / "blender_manifest.toml").read_text(encoding="utf-8")
    prod_path = src.parent / "tools" / "products" / "flexspace.toml"
    prod = prod_path.read_text(encoding="utf-8") if prod_path.is_file() else ""
    return {
        "name": toml_value(prod, "name") or toml_value(manifest, "name") or "FlexSpace",
        "version": toml_value(prod, "version") or toml_value(manifest, "version") or "",
        "tagline": toml_value(prod, "tagline") or toml_value(manifest, "tagline") or "",
        "blender": toml_value(manifest, "blender_version_min") or "",
        "modules": toml_value(prod, "modules") or ["core", "flex_canvas", "armature_picker"],
    }


def read_demos(src: Path, modules) -> list:
    out = []
    for m in modules:
        p = src / "modules" / m / "demos" / "demos.json"
        if p.is_file():
            try:
                out += json.loads(p.read_text(encoding="utf-8")).get("demos", [])
            except ValueError:
                print(f"  ! {p} is not valid JSON, its demos are left out")
    return out


def registry() -> dict:
    p = IMG / "graphics.json"
    try:
        return {e["name"]: e for e in json.loads(p.read_text(encoding="utf-8")).get("images", [])}
    except (OSError, ValueError):
        return {}


def image_size(path: Path):
    """(w, h) of a WebP/PNG file, read from its header."""
    try:
        head = path.read_bytes()[:40]
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        kind = head[12:16]
        if kind == b"VP8X":
            return 1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little")
        if kind == b"VP8 ":
            return struct.unpack("<H", head[26:28])[0] & 0x3FFF, struct.unpack("<H", head[28:30])[0] & 0x3FFF
        if kind == b"VP8L":
            b = head[21:25]
            bits = int.from_bytes(b, "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


# ---------------------------------------------------------------------------------------------- page text
ON_THIS_PAGE = re.compile(r"^>\s*\*\*On this page:\*\*\s*(.+?)\s*$\n?", re.M)


def summary_of(text: str):
    m = ON_THIS_PAGE.search(text)
    if m is None:
        return text, ""
    s = m.group(1).strip()
    s = s[0].upper() + s[1:]
    return ON_THIS_PAGE.sub("", text, count=1), s


def inject_extras(text: str, extras) -> str:
    lines = text.split("\n")
    for heading, slot in extras:
        at = next((i for i, ln in enumerate(lines) if re.match(rf"^#{{2,3}}\s+{re.escape(heading)}\s*$", ln)), None)
        if at is None:
            print(f"  ! extra figure: heading not found: {heading}")
            continue
        end = next((i for i in range(at + 1, len(lines)) if re.match(r"^#{1,3}\s", lines[i])), len(lines))
        while end > at + 1 and (not lines[end - 1].strip() or re.match(r"^-{3,}$", lines[end - 1].strip())):
            end -= 1
        lines[end:end] = ["", f"<!-- image: @{slot} -->", ""]
    return "\n".join(lines)


def title_of(text: str, gen) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return gen.plain(m.group(1)) if m else ""


# ---------------------------------------------------------------------------------------------- HTML pieces
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def post_process(body: str) -> str:
    def callout(m):
        label = m.group(1)
        kind = "tip" if label == "Tip" else "note"
        return (f'<aside class="fs-callout fs-callout--{kind}"><p><strong class="fs-callout__label">{label}</strong> ')
    body = re.sub(r'<aside class="note"><p><strong>(Note|Tip):</strong>\s*', callout, body)
    body = body.replace('<aside class="note">', '<aside class="fs-callout fs-callout--note">')
    body = re.sub(r"<code>([^<]{18,})</code>",
                  lambda m: "<code>" + m.group(1).replace(".", ".<wbr>") + "</code>", body)
    body = body.replace('<div class="table-wrap">', '<div class="fs-table">')
    body = body.replace('<span class="keys">', '<span class="fs-keys">')
    body = body.replace('<a class="anchor"', '<a class="fs-anchor"')
    body = body.replace('<a class="xref"', '<a class="fs-xref"')
    body = body.replace("<hr>", '<hr class="fs-rule">')
    return body


def figure_html(slot, entry, size, eager=False) -> str:
    w, h = size
    alt = entry.get("alt", "") if entry else ""
    kind = (entry or {}).get("kind", "")
    cls = "fs-figure" + (" fs-figure--frame" if kind == "framed-scene" else " fs-figure--widget" if kind == "widget" else "")
    load = ' fetchpriority="high"' if eager else ' loading="lazy"'
    src = f"../assets/img/{slot}.webp"
    return (f'<figure class="{cls}"><a class="fs-zoom" href="{src}" data-zoom>'
            f'<img src="{src}" alt="{esc(alt)}" width="{w}" height="{h}" decoding="async"{load}></a>'
            + (f"<figcaption>{esc(alt)}</figcaption>" if alt else "") + "</figure>")


def media_registry() -> dict:
    try:
        return json.loads((MEDIA / "media.json").read_text(encoding="utf-8")).get("items", {})
    except (OSError, ValueError):
        return {}


def real_figure_html(name, m, caption_html, alt, eager=False) -> str:
    """A real screenshot (zooms) or loop (video started by docs.js when visible; zooms into the lightbox)."""
    w, h = m["w"], m["h"]
    cap = f"<figcaption>{caption_html}</figcaption>" if caption_html else ""
    if m["kind"] == "loop":
        mp4, poster = f"../{m['mp4']}", f"../{m['poster']}"
        return (f'<figure class="fs-figure fs-figure--real fs-figure--loop"><a class="fs-zoom" href="{mp4}" data-zoom data-video>'
                f'<video class="fs-loop" muted loop playsinline preload="none" poster="{poster}" data-src="{mp4}" '
                f'width="{w}" height="{h}" aria-label="{esc(alt)}"></video>'
                f'<span class="fs-figure__tag">Recording</span></a>{cap}</figure>')
    src = f"../{m['webp']}"
    load = ' fetchpriority="high"' if eager else ' loading="lazy"'
    return (f'<figure class="fs-figure fs-figure--real"><a class="fs-zoom" href="{src}" data-zoom>'
            f'<img src="{src}" alt="{esc(alt)}" width="{w}" height="{h}" decoding="async"{load}>'
            f'<span class="fs-figure__tag fs-figure__tag--still">Screenshot</span></a>{cap}</figure>')


def demo_cards(demos: list) -> str:
    cards = []
    for d in demos:
        cards.append(
            f'<article class="fs-demo" id="demo-{esc(d.get("id", ""))}">'
            f'<p class="fs-demo__cat">{esc(d.get("category", ""))}</p>'
            f'<h3 class="fs-demo__title">{esc(d.get("title", ""))}</h3>'
            f'<p class="fs-demo__text">{esc(d.get("description", ""))}</p></article>')
    return f'<div class="fs-demos">{"".join(cards)}</div>' if cards else ""


def toc_html(heads, cls) -> str:
    items = [(lvl, t, a) for lvl, t, a in heads if lvl in (2, 3)]
    if len(items) < 2:
        return ""
    links = "".join(f'<li class="lv{lvl}"><a href="#{esc(a)}">{esc(t)}</a></li>' for lvl, t, a in items)
    return f'<ul class="{cls}">{links}</ul>'


def side_nav(current: str, titles: dict) -> str:
    out, group = [], None
    for slug, _f, label, grp in PAGES:
        if grp != group:
            if group is not None:
                out.append("</ul>")
            out.append(f'<p class="fs-side__group">{esc(grp)}</p><ul class="fs-side__list">')
            group = grp
        cur = ' aria-current="page"' if slug == current else ""
        out.append(f'<li><a href="{slug}.html"{cur}>{esc(label)}</a></li>')
    out.append("</ul>")
    return "".join(out)


def site_links(active: str = "docs") -> list:
    return [("Features", "../features.html", ""), ("Widgets", "../widgets.html", ""), ("Picker", "../picker.html", ""),
            ("Docs", "index.html", "docs"), ("Changelog", CHANGELOG_URL, "ext"), ("Support", "../support.html", "")]


def topbar(facts) -> str:
    links = []
    for label, url, kind in site_links():
        if kind == "ext":
            links.append(f'<a href="{url}" target="_blank" rel="noopener">{label}{ICON["ext"]}</a>')
        elif kind == "docs":
            links.append(f'<a href="{url}" aria-current="true">{label}</a>')
        else:
            links.append(f'<a href="{url}">{label}</a>')
    buy = (f'<a class="fs-btn fs-btn--primary fs-btn--sm fs-top__buy" href="{esc(SUPERHIVE_URL)}" target="_blank" '
           f'rel="noopener">Get it on Superhive</a>') if SUPERHIVE_URL else ""
    return f"""<header class="fs-top">
  <div class="fs-top__in">
    <a class="fs-top__brand" href="../index.html" aria-label="{esc(facts['name'])} home"><img src="../assets/img/icons/wordmark-gradient.png" alt="{esc(facts['name'])}" width="111" height="22"></a>
    <a class="fs-top__docs" href="index.html">Docs</a>
    <nav class="fs-top__nav" aria-label="Site">{''.join(links)}</nav>
    <div class="fs-top__actions">
      <button class="fs-searchbtn" type="button" data-search-open aria-label="Search the docs">{ICON['search']}<span>Search</span><kbd>/</kbd></button>
      <button class="fs-iconbtn" type="button" data-theme-toggle aria-label="Switch to the light theme" title="Light / dark">{ICON['sun']}{ICON['moon']}</button>
      {buy}
      <details class="fs-top__menu"><summary aria-label="Menu">{ICON['menu']}</summary>
        <nav class="fs-top__sheet" aria-label="Site">{''.join(links)}{buy}</nav>
      </details>
    </div>
  </div>
</header>"""


def footer(facts) -> str:
    return f"""<footer class="fs-foot">
  <div class="fs-foot__in">
    <div class="fs-foot__brand"><img src="../assets/img/icons/wordmark-gradient.png" alt="{esc(facts['name'])}" width="111" height="22" loading="lazy">
      <p>{esc(facts['tagline'])}. v{esc(facts['version'])} &middot; Blender {esc(facts['blender'].rsplit('.0', 1)[0] or facts['blender'])}+</p></div>
    <nav class="fs-foot__links" aria-label="Footer">
      <a href="../features.html">Features</a><a href="../widgets.html">Widgets</a><a href="../picker.html">Picker</a>
      <a href="index.html">Docs</a><a href="{CHANGELOG_URL}" target="_blank" rel="noopener">Changelog</a>
      <a href="../support.html">Support</a>{f'<a href="{esc(SUPERHIVE_URL)}" target="_blank" rel="noopener">Superhive</a>' if SUPERHIVE_URL else ''}
      <a href="{ISSUES_URL}" target="_blank" rel="noopener">GitHub issues</a>
    </nav>
    <p class="fs-foot__legal">FlexSpace is GPL-3.0-or-later. Blender is a trademark of the Blender Foundation.</p>
  </div>
</footer>"""


SEARCH_UI = f"""<div class="fs-search" id="fs-search" hidden>
  <div class="fs-search__panel" role="dialog" aria-modal="true" aria-label="Search the documentation">
    <div class="fs-search__field">{ICON['search']}<input type="search" placeholder="Search the docs" autocomplete="off" spellcheck="false" aria-label="Search the docs" aria-controls="fs-search-results"><kbd>Esc</kbd></div>
    <ul class="fs-search__results" id="fs-search-results" role="listbox" aria-label="Results"></ul>
    <p class="fs-search__empty" hidden>No results. Try another word.</p>
    <p class="fs-search__hint"><span><kbd>&uarr;</kbd><kbd>&darr;</kbd> to choose</span><span><kbd>Enter</kbd> to open</span></p>
  </div>
</div>
<div class="fs-lightbox" id="fs-lightbox" hidden><figure><img alt=""><video controls loop muted playsinline hidden></video><figcaption></figcaption></figure></div>"""


def page_html(facts, *, slug, title, description, main, side, toc="", page_class="") -> str:
    canonical = f"{SITE_URL}docs/{slug}.html" if slug != "index" else f"{SITE_URL}docs/"
    full_title = f"{title} · {facts['name']} Docs" if slug != "index" else f"{facts['name']} Docs"
    og = f"{SITE_URL}assets/img/store/og-card.jpg"
    toc_col = (f'<aside class="fs-doc__toc" aria-label="On this page"><p class="fs-doc__toc-title">On this page</p>'
               f'<nav>{toc}</nav><a class="fs-doc__top" href="#top">Back to top</a></aside>') if toc else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0a0a0c">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{esc(facts['name'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<script>(function(){{try{{var t=localStorage.getItem('{THEME_KEY}');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}}})();</script>
<link rel="icon" href="../assets/img/icons/favicon.ico" sizes="32x32">
<link rel="icon" href="../assets/img/icons/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../assets/img/icons/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS_URL.replace('&', '&amp;')}">
<link rel="stylesheet" href="../assets/css/tokens.css">
<link rel="stylesheet" href="../assets/css/docs.css">
<script src="../assets/js/docs.js" defer></script>
</head>
<body class="fs-docs {page_class}" id="top">
<a class="fs-skip" href="#main">Skip to content</a>
{topbar(facts)}
<div class="fs-doc{' fs-doc--wide' if not toc else ''}">
  <aside class="fs-doc__side" aria-label="Guides">
    <nav class="fs-side">{side}</nav>
    <div class="fs-side__foot">
      <p>Also in Blender: the <strong>Help</strong> menu of the canvas header.</p>
      <a href="{BUG_URL}" target="_blank" rel="noopener">{ICON['bug']}Report a bug</a>
    </div>
  </aside>
  <main id="main" class="fs-doc__main">
{main}
  </main>
  {toc_col}
</div>
{footer(facts)}
{SEARCH_UI}
</body>
</html>
"""


def mobile_nav(slug, label, titles) -> str:
    return (f'<details class="fs-doc__mnav"><summary><span>Guides</span><strong>{esc(label)}</strong>{ICON["chev"]}</summary>'
            f'<nav class="fs-side">{side_nav(slug, titles)}</nav></details>')


# ---------------------------------------------------------------------------------------------- build
def search_chunks(gen, text, title, url, heads) -> list:
    """One search entry per section (as the add-on's generator does): page title, heading, link, text."""
    out, current, buf = [], ("", url), []
    for line in gen.strip_media(text).splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m is not None:
            if buf:
                out.append((current, " ".join(buf)))
            buf = []
            level, heading = len(m.group(1)), gen.plain(m.group(2))
            anchor = next((a for _lvl, t, a in heads if t == heading), "")
            current = ("" if level == 1 else heading, url if level == 1 else f"{url}#{anchor}")
            continue
        s = line.strip()
        if s and not re.match(r"^\|?\s*:?-{3,}", s) and not re.match(r"^-{3,}$", s) and not s.startswith("<!--"):
            buf.append(gen.plain(re.sub(r"^\s*([-*>]|\d+\.)\s*|\|", " ", line)))
    if buf:
        out.append((current, " ".join(buf)))
    return [{"p": title, "h": h, "u": u, "t": re.sub(r"\s+", " ", t).strip()} for (h, u), t in out if t.strip()]


def build(src: Path) -> dict:
    gen = load_generator(src)
    facts = product_facts(src)
    help_dir = src / "help"
    modules = set(facts["modules"])
    sources = {Path(f).name: text for _pid, f, text in gen.page_sources(help_dir, "flexspace", facts["name"], modules)}
    demos = read_demos(src, facts["modules"])
    reg = registry()
    media = media_registry()
    notes: list[str] = []

    def slot_file(slot):
        p = IMG / f"{slot}.webp"
        if not p.is_file():
            return None
        size = image_size(p) or tuple((reg.get(slot) or {}).get("size") or (0, 0))
        return p, size

    # First pass: titles, summaries and sections, for links between pages.
    pages = []
    for slug, file, label, group in PAGES:
        text = sources.get(file)
        if text is None:
            notes.append(f"missing help page: {file}")
            continue
        text, summary = summary_of(text)
        text = inject_extras(text, EXTRA.get(slug, []))
        text = inject_extras(text, [(hd, "real:" + n) for hd, n in REAL_EXTRA.get(slug, []) if n in media])
        title = title_of(text, gen)
        pages.append(dict(slug=slug, file=file, label=label, group=group, text=text, title=title,
                          summary=gen.plain(summary), summary_html=gen.inline(summary)))
    titles = {p["title"]: f'{p["slug"]}.html' for p in pages}
    sections = {}
    for p in pages:
        _b, heads = gen.markdown(gen.strip_media(p["text"]))
        sections[f'{p["slug"]}.html'] = {t: a for lvl, t, a in heads if lvl in (2, 3)}
    linker = gen.Linker(titles, sections)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in list(OUT.glob("*.html")) + [OUT / "search-index.json"]:
        if old.exists():
            old.unlink()

    search = []
    order = [p["slug"] for p in pages]
    for i, p in enumerate(pages):
        url = f'{p["slug"]}.html'
        linker.current = url
        used: set = set()

        def figure(kind, rel, caption, _p=p, _used=used):
            if kind == "cell":
                stem = Path(rel).stem
                slot = "w-" + CELL_RENAME.get(stem, stem.replace("_", "-"))
                found = slot_file(slot)
                if found is None:
                    notes.append(f'{_p["slug"]}: no art for table cell {rel} ({slot})')
                    return ""
                _used.add(slot)
                w, h = found[1]
                return (f'<img class="fs-cell-art" src="../assets/img/{slot}.webp" alt="{esc(gen.plain(caption))}" '
                        f'width="{w}" height="{h}" loading="lazy" decoding="async">')
            real = (rel[len("@real:"):], "manifest") if rel.startswith("@real:") else REAL.get(rel)
            if real is not None and real[0] in media:
                name, capsrc = real
                key = "real:" + name
                if key in _used:
                    return ""
                _used.add(key)
                m = media[name]
                if capsrc == "help" and caption:
                    cap_html, alt = gen.inline(caption), gen.plain(caption)
                else:
                    cap_html = esc(m["caption"])
                    alt = m["caption"]
                return real_figure_html(name, m, cap_html, alt, eager=(kind == "hero"))
            slot = rel[1:] if rel.startswith("@") else FIGURES.get(rel)
            if slot is None:
                notes.append(f'{_p["slug"]}: no generated slot for {rel}, figure left out')
                return ""
            if slot in _used:
                return ""
            found = slot_file(slot)
            if found is None:
                notes.append(f'{_p["slug"]}: slot {slot} not generated yet, figure left out')
                return ""
            _used.add(slot)
            return figure_html(slot, reg.get(slot), found[1], eager=(kind == "hero"))

        body, heads = gen.markdown(p["text"], linker, figure, lambda: demo_cards(demos))
        body = re.sub(r"^<h1 [^>]*>.*?</h1>\n?", "", body, count=1)
        body = post_process(body)
        toc = toc_html(heads, "fs-toc")
        mtoc = (f'<details class="fs-doc__mtoc"><summary>On this page{ICON["chev"]}</summary>{toc_html(heads, "fs-toc")}'
                f'</details>') if toc else ""
        prev_p = pages[i - 1] if i > 0 else None
        next_p = pages[i + 1] if i + 1 < len(pages) else None
        pager = '<nav class="fs-pager" aria-label="Previous and next guide">'
        pager += (f'<a class="fs-pager__link fs-pager__link--prev" href="{prev_p["slug"]}.html"><span>{ICON["back"]}Previous</span>'
                  f'<strong>{esc(prev_p["title"])}</strong></a>') if prev_p else (
                  f'<a class="fs-pager__link fs-pager__link--prev" href="index.html"><span>{ICON["back"]}Docs home</span>'
                  f'<strong>All guides</strong></a>')
        pager += (f'<a class="fs-pager__link fs-pager__link--next" href="{next_p["slug"]}.html"><span>Next{ICON["arrow"]}</span>'
                  f'<strong>{esc(next_p["title"])}</strong></a>') if next_p else ""
        pager += "</nav>"
        main = f"""    {mobile_nav(p['slug'], p['label'], titles)}
    <header class="fs-doc__head">
      <p class="fs-eyebrow"><a href="index.html">Docs</a><span aria-hidden="true">/</span>{esc(p['group'])}</p>
      <h1>{esc(p['title'])}</h1>
    </header>
    {mtoc}
    <article class="fs-prose">
{body}
    </article>
    {pager}
    <aside class="fs-doc__help"><p>Something unclear or broken? In Blender, <strong>Help &gt; Report a Bug...</strong> fills in the details for you.</p>
      <a class="fs-btn fs-btn--ghost fs-btn--sm" href="{BUG_URL}" target="_blank" rel="noopener">Open an issue{ICON['arrow']}</a></aside>"""
        description = (f'{p["title"]}: {p["summary"][0].lower() + p["summary"][1:]}' if p["summary"]
                       else f'{p["title"]} · {facts["name"]} documentation')
        out = page_html(facts, slug=p["slug"], title=p["title"], description=description, main=main,
                        side=side_nav(p["slug"], titles), toc=toc)
        (OUT / url).write_text(out, encoding="utf-8")
        search += search_chunks(gen, p["text"], p["title"], url, heads)
        if gen.DEMOS.search(p["text"]):
            search += [{"p": p["title"], "h": d.get("title", ""), "u": f'{url}#demo-{d.get("id", "")}',
                        "t": d.get("description", "")} for d in demos]

    # The docs home.
    groups = []
    for grp in dict.fromkeys(p["group"] for p in pages):
        cards = []
        for p in pages:
            if p["group"] != grp:
                continue
            n = order.index(p["slug"]) + 1
            cards.append(f'<a class="fs-guide" href="{p["slug"]}.html"><span class="fs-guide__n">{n:02d}</span>'
                         f'<span class="fs-guide__title">{esc(p["title"])}{ICON["arrow"]}</span>'
                         f'<span class="fs-guide__text">{p["summary_html"]}</span></a>')
        gid = re.sub(r"[^a-z0-9]+", "-", grp.lower()).strip("-")
        groups.append(f'<section class="fs-guides" aria-labelledby="g-{gid}"><div class="fs-guides__head">'
                      f'<h2 id="g-{gid}">{esc(grp)}</h2><p>{esc(GROUP_INTRO.get(grp, ""))}</p></div>'
                      f'<div class="fs-guides__grid">{"".join(cards)}</div></section>')
    art = slot_file(HOME_ART)
    art_html = ""
    if art is not None:
        w, h = art[1]
        art_html = (f'<div class="fs-home__art"><img src="../assets/img/{HOME_ART}.webp" '
                    f'alt="{esc((reg.get(HOME_ART) or {}).get("alt", ""))}" width="{w}" height="{h}" fetchpriority="high"></div>')
    first = pages[0]["slug"] if pages else "getting-started"
    home_main = f"""    <header class="fs-home">
      <div class="fs-home__text">
        <p class="fs-chip">Documentation &middot; v{esc(facts['version'])} &middot; Blender {esc(facts['blender'].rsplit('.0', 1)[0])}+</p>
        <h1>Learn <span class="fs-grad">{esc(facts['name'])}</span></h1>
        <p class="fs-lead">Build your own control panels and rig pickers in Blender. Start with three steps, then
          go as deep as you like: widgets, binding, layers, the Armature Picker and every key.</p>
        <div class="fs-home__actions">
          <a class="fs-btn fs-btn--primary" href="{first}.html">Get started{ICON['arrow']}</a>
          <button class="fs-btn fs-btn--secondary" type="button" data-search-open>{ICON['search']}Search the docs<kbd>/</kbd></button>
        </div>
      </div>
      {art_html}
    </header>
    {''.join(groups)}
    <aside class="fs-callout fs-callout--tip fs-home__note"><p><strong class="fs-callout__label">Tip</strong>
      The same guides are inside Blender: open the <strong>Help</strong> menu in the header of a Flex Space or
      Armature Picker editor. <strong>Help &gt; Demo Files</strong> opens finished canvases to take apart.</p></aside>"""
    out = page_html(facts, slug="index", title="Docs",
                    description=f"{facts['name']} documentation: {facts['tagline'].lower()}. Guides for the canvas, "
                                "widgets, binding, layers, the Armature Picker, Rigify, shortcuts and troubleshooting.",
                    main=home_main, side=side_nav("", titles), page_class="fs-docs--home")
    (OUT / "index.html").write_text(out, encoding="utf-8")
    search += [{"p": p["title"], "h": "", "u": f'{p["slug"]}.html', "t": p["summary"]} for p in pages if p["summary"]]
    (OUT / "search-index.json").write_text(
        json.dumps({"version": facts["version"], "entries": search}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    files = sorted(p for p in OUT.iterdir() if p.is_file())
    return {"files": files, "bytes": sum(f.stat().st_size for f in files), "entries": len(search), "notes": notes}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=os.environ.get("FLEXSPACE_SRC") or str(WORKSPACE / "B3D-MySpace" / "flexspace"),
                    help="the add-on's dev checkout (holds help/, src/docs_html/generator.py, blender_manifest.toml)")
    args = ap.parse_args(argv)
    res = build(Path(args.src))
    for f in res["files"]:
        print(f"  {f.relative_to(DOCS).as_posix()}  {f.stat().st_size // 1024} KB")
    print(f"{len(res['files'])} files, {res['bytes'] // 1024} KB, {res['entries']} search entries")
    for n in res["notes"]:
        print("  note:", n)


if __name__ == "__main__":
    main()
