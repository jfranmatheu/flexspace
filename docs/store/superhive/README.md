# Superhive fragments

Two HTML fragments for the FlexSpace product on Superhive, plus a local preview.

| File | Paste into | What it is |
|---|---|---|
| `page.html` | The product **description** (store page) | Hero, trust row, Edit/Live modes, 7 feature rows, themes, bento, 21-widget gallery, Rigify spotlight, what's inside + specs, the "3+ years in the making" timeline, FAQ, closing band |
| `docs.html` | The product **documentation** tab | A one-page guide: contents index, 15 sections (install to report a bug), widget reference with thumbnails, shortcut tables, troubleshooting; each section links to the full docs at https://jfranmatheu.github.io/flexspace/docs/ |
| `preview.html` | Nothing (local only) | Shows either fragment inside a fake store column at 360 / 720 / 900 / 1100 px and checks the fragment rules |

Neither fragment is linked from the site (only `preview.html`, which is `noindex`, loads them), and `sitemap.xml` leaves `/store/` out. A `robots.txt` can't help here: crawlers only read the one at the domain root (`jfranmatheu.github.io/robots.txt`, another repository), never `/flexspace/robots.txt`, and a fragment can't carry a `noindex` meta tag. If they ever show up in search results, rename them `page.fragment.txt` / `docs.fragment.txt` (and the two paths in `preview.html`'s fetch).

## How to paste

1. Make sure the images are online first: the fragments load them from `https://jfranmatheu.github.io/flexspace/assets/img/store/` (redrawn art) and `.../assets/media/store/` (real screenshots and GIFs from Blender), so push `docs/` to `main` (GitHub Pages) before pasting.
2. Open the file in a text editor and copy **everything**, from `<div class="fsx">` to the last `</div>`.
3. In Superhive's editor, switch the description (or documentation) field to its **HTML / source** mode, select all, paste, save.
4. Open the live product page and check it at desktop and phone width. If something looks off, compare with `preview.html` (below).

Paste the whole file every time you update: the `<style>` at the top belongs to the markup under it.

## Preview locally

```
py -3.10 -m http.server 8000 -d docs
```

Then open http://localhost:8000/store/superhive/preview.html.

- **Store page / Store docs** switches the fragment; the width buttons set the store column.
- **Local images** swaps the absolute URLs for the local files, so it works before you push.
- **Hostile store CSS** adds aggressive global styles (serif fonts, list bullets, red image borders, link underlines) to prove the fragment doesn't depend on the host page.
- The **Fragment rules** box re-checks everything listed below, and that every image file exists in `docs/assets/img/store/` or `docs/assets/media/store/`.

Opened straight from disk (`file://`) the preview can't read the fragment, so it shows the raw file and tells you to serve it.

## The rules (why the files look the way they do)

Superhive pastes the HTML into its own page, so a fragment has to be self-contained and must not touch anything outside itself:

- **One root.** Exactly one `<div class="fsx">`; its first child is the only `<style>`.
- **No page-level tags.** No `<html>`, `<head>`, `<body>`, `<meta>`, `<link>`, `<script>`, `<iframe>`, `<video>`, no `on...=` handlers, no `style="..."` attributes.
- **Scoped CSS.** Every selector starts with `.fsx`, including those inside `@media` and `@container`. No `:root`, `html`, `body` or bare `*`. The reset only touches elements inside `.fsx`.
- **Literal values.** No `var()` or custom properties (a sanitizer may drop them). Colours, sizes and fonts are copied from `docs/assets/css/tokens.css`; keep them in sync by hand.
- **Names that can't clash.** Classes are `fs-*` under `.fsx`; keyframes are `fsx-*`; anchors are `#fsx-*`.
- **Fonts.** The first rule is an `@import` of Google Fonts (Bricolage Grotesque, Inter, JetBrains Mono). If it is stripped, the system font stacks take over.
- **Images.** Absolute URLs under `https://jfranmatheu.github.io/flexspace/assets/img/store/` or `.../assets/media/store/` (real media, GIFs under 4 MB), PNG, JPG or GIF only (no WebP, no MP4), each with `width`, `height`, `alt` and `loading="lazy"` (except the hero).
- **CSS-only interaction.** Hover, `:focus-visible`, `:target` (the docs index highlights the section you jump to), `<details>` for the FAQ, `@keyframes`. Everything animated stops under `prefers-reduced-motion: reduce`, and each GIF sits in a `<picture>` whose reduced-motion source is a still PNG.
- **No fixed positioning**, and nothing wider than the store column: layouts respond to the fragment's own width (container queries on `.fsx`), not the window, and fall back to the single-column phone layout where container queries aren't supported.

If Superhive's editor strips something, the fragments degrade instead of breaking:

| Stripped | Result |
|---|---|
| `<style>` | Plain, readable HTML in the store's own styles (all text is real text); images then show as large as the store allows, so this one is worth checking first |
| `@import` | System fonts |
| `<picture>` / `<source>` | The GIF plays for everyone (its first frame is a complete image) |
| `<details>` | FAQ answers show open |
| `id` attributes | The docs index links stop jumping; the sections are still in order |

## Images

The redrawn art is generated; the Armature Picker in it is real captures of the redesigned picker, cropped and composed (never squashed: the scripts fail if any embedded image changes its aspect). Real screenshots and GIFs (`docs/assets/media/store/`) are copied by `docs/_design/make_media.py`.

- `docs/_design/make_graphics.py`: hero, cards, framed scenes (`frame-*.png`: a whole canvas), focus crops (`focus-*.png`: the part that tells the story, drawn so its UI text reads at the width the fragments show it), widget tiles for the site (`w-*.webp`, 720 x 400), widget gallery, icons.
- `docs/_design/make_store_extras.py` (run it after `make_graphics.py widgets`): the store's widget thumbnails (`w-*.png`, 720 x 324, plus `w-gaze-eyes.png`) and the two GIFs drawn frame by frame from the same vector widgets: `gif-live-mode.gif` and `gif-ring-menu.gif`, each with a `-still.png`.

Both register their outputs in `docs/assets/img/graphics.json`. To change a picture, overwrite the file at the same path and push; the fragments don't need editing (re-paste only if Superhive caches the old HTML).

**Picker media** (the redesigned picker, both body charts):

- Store page: the hero's floating picker (`float-picker.png`, Adult Female), `picker-select-transform.gif` big at the end of "See it in action", the Armature Picker row (`focus-picker.png`, Adult Male, plus `picker-face-gaze.gif`, `picker-hands-curl.gif`, `picker-ikfk.gif`), and in "Rigify? One step." every page of both bodies (`picker-layer-{female,male}-{body,face,hands,feet}.png`).
- Store docs: section 10 (`focus-picker.png`, `picker-select-transform.gif`, `picker-hero.jpg`) and 11 (`picker-layer-female-face.png`, `picker-pages.gif`).
- Each GIF has a `-still.png` first frame for reduced motion; every GIF is under 4 MB.

## Open points for the author

- **No buy button.** The store page has its own; the fragments link to the docs and the issue tracker only.
- **Superhive editor.** Check after the first paste that it keeps `<style>`, `<picture>`, `<details>` and `id` attributes (see the table above for what happens if not).
