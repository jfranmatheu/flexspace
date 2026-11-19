# FlexSpace web: art direction and information architecture

Source of truth for the GitHub Pages site (`https://jfranmatheu.github.io/flexspace/`, served from `/docs` on `main`)
and for the two Superhive fragments (store page and store docs). Tokens live in `docs/assets/css/tokens.css`.
Everything here is checked against the user docs (`flexspace/help/*.md`), `blender_manifest.toml` and
`tools/products/flexspace.toml` of the dev checkout. If a sentence on the site can't be traced to those, it doesn't ship.

Product facts used everywhere (one place, keep in sync on release):

| Key | Value |
|---|---|
| Name | FlexSpace (one word). The canvas editor type is **Flex Space** (two words), the other is **Armature Picker**. |
| Version | 1.4.0 |
| Requires | Blender 5.3 or newer (an extension) |
| Taglines | Store: "Control panels and rig pickers, built your way". Manifest: "Build your own control panels for any Blender workflow". |
| Licence | GPL-3.0-or-later |
| Icons bundled | Phosphor Icons, Gravity UI Icons (both MIT) |
| Issues | `https://github.com/jfranmatheu/flexspace/issues` (form: `issues/new?template=flexspace.yml`) |
| Site | `https://jfranmatheu.github.io/flexspace/` |
| Superhive URL | `https://superhivemarket.com/products/flexspace-armature-picker` (`SUPERHIVE_URL` in `assets/js/site.js`, one constant; `build_docs.py` reads it) |
| Changelog | `CHANGELOG.md` at the repo root, shown as `changelog.html` (built by `_design/build_changelog.py`) |

---

## 1. Imagery: redrawn art plus real media from Blender

Author direction (latest, corrects an earlier note): the "don't reuse, reference only" rule was about **some character
drawings for the picker**, not about the product screenshots. The site and the store show **both**:

- **Redrawn art** (`docs/assets/img/`, `make_graphics.py`): hero, cards, focus/frame images, widget art. Kept as it is.
- **Real media** (`docs/assets/media/`, `make_media.py`): screenshots of the demos and the UI, features in detail, and
  screen recordings of features in use, copied from the curated `B3D-MySpace/marketing/flexspace/manifest.json`
  (quality >= 3). Captions are the manifest captions (or, in the docs, the help's own caption for that very shot).
  - Pages: stills as WebP; loops as H.264 MP4 (faststart, no audio) with a WebP poster, loaded and played only while
    in view (`video.fs-loop[data-src]`, site.js / docs.js), poster only with reduced motion; every item opens in
    the lightbox. Real items carry a small "Recording" / "Screenshot" tag.
  - Superhive: PNG (UI crops) or JPG (full screenshots) and the original GIFs (< 4 MB each) with a first-frame PNG
    for reduced motion, in `docs/assets/media/store/`, absolute URLs. No WebP, no MP4.
  - Where: index "See it in Blender" band (live-mode big + 4 loops + a screenshot strip), an "In Blender" strip under
    each feature row (features.html), an Illustration / In Blender switch on the widget gallery, real figures in the
    docs (`REAL` / `REAL_EXTRA` in build_docs.py), a "See it in action" section and "In Blender" strips on the store
    page, and real shots in the store docs.
  - **Armature Picker media is the redesigned picker only** (character-art pages Body, Hands, Feet and Face):
    `make_media.py` copies only the picker files it lists (`PICKER_OK`); `gifs/snapping.gif` and `gifs/picker.gif`
    (older captures) stay out. Where it shows (`<!-- REAL-PICKER-MEDIA -->` comments mark each place):
    - Recordings: `picker-select-transform` (rig controls hidden: click in the picker, G / R in the viewport; the
      lead picker loop everywhere, big on the store page), `picker-face-gaze` (gaze pad + real eyeballs, then brows
      and mouth corners), `picker-hands-curl` (four finger masters curled in one move), `picker-pages`,
      `picker-ikfk`, `picker-gaze`, `picker-pose`, `picker-mirror`.
    - Every page of both body charts: `picker-layer-{female,male}-{body,face,hands,feet}` (store: the 256-colour PNGs
      as they are). Shown as two strips (Adult Female, Adult Male) in the order Body, Face, Hands, Feet; Body + Face
      frames share one aspect and Hands + Feet another, so each row lines up (`.fs-pages` / `.fs-lgrid`).
    - Alternate the bodies across visuals: key visual (hero banner, og card, Superhive cover and thumbnail) and
      `focus-picker` / `frame-picker` = Adult Male; the hero picker (`hero-picker`, store page and site home),
      `card-picker`, the presets thumbnail and the `w-bone-pickers` tile = Adult Female; picker sections show both.

The rest of this section is about the redrawn art.

How we generate, in order of preference:

1. **Widget art (vector).** Each widget redrawn as SVG from its reference shot (`shots/widgets/*.png`): same geometry,
   same parts, same states, the brand palette on the add-on's own dark canvas look (`--fs-canvas` #1d1d1d, blue
   `--fs-ui` accents). Crisp at any size, tiny, themeable, animatable with CSS. A PNG render (2x) of each is made with
   Pillow for Superhive (which may not accept SVG `<img>`).
2. **Composed scenes (raster).** Hero and feature images composed new: a canvas of widget art in a stylised editor
   frame (Blender-like header strip, sidebar hint, the node-editor grid) beside an abstracted 3D Viewport (soft lit
   shapes on a gradient, no Blender UI chrome copied). Rendered at 2x with Pillow (`py -3.10`), exported as WebP
   (q 82–88) for Pages and PNG/JPG for Superhive. The Armature Picker in these scenes is a real capture of the
   redesigned picker (`picker_layer_*.png`, `picker_hero.png`), cropped, never redrawn.
   **Never distort:** every image placed in another is cover-cropped to its box and scaled uniformly (`cover()`).
   `make_graphics.py` guards `Image.resize` for the whole run and fails if any resize or placement changes an
   image's aspect (`check_aspect()`, also run by `make_store_extras.py`); a 1x capture is not blown up past its size
   in a frame.
3. **Motion.** CSS animations on the vector art (a toggle flipping, a slider filling, the Ring Menu's active slot
   moving, snapping guides appearing). Where a store page needs a moving image, a short GIF is *generated* from the
   same vector frames (Pillow, ≤ 2.5 MB, 24–30 frames, 640–960 px wide). (The real screen recordings are shown as they are, as real media: see above.)

Accuracy rules for generated images (non-negotiable):

- Only show widgets, panels, states and behaviours that exist (see the help docs). No invented buttons, menus,
  settings or numbers. Labels inside art use real names: **Live Mode**, **Edit Mode**, **Add Widget**, **From
  Property**, **Visible When**, **⚠ 2 broken**, **Humanoid Body (Rigify)**, `scene.frame_current`...
- Stylise the surroundings, never the feature: a Ring Menu still has an outer ring of slots, an inner ring of
  segments and a core with the name; a picker still uses left = blue, right = red, centre = yellow, root = purple.
- Animation-state colours, when shown, are Blender's: green (animated), yellow (key on frame), purple (driver),
  orange (changed, not keyed).
- Captions describe real behaviour in the docs' words.

### Image registry (one place to swap)

Every image on the site and in the Superhive files has a **stable slot name**. Files are
`docs/assets/img/<slot>.webp` (Pages) and `docs/assets/img/store/<slot>.png|.jpg|.gif` (Superhive). Replacing art =
overwriting the file at the same path; no HTML edit. `docs/assets/img/images.json` lists each slot:

```json
{ "slot": "picker-body", "alt": "...", "caption": "...", "pages": ["index", "picker", "store-page"],
  "reference": ["shots/features/picker_female_body_canvas.png"], "kind": "scene|widget|motion",
  "size": [1600, 1000], "status": "generated|placeholder" }
```

**Picker art** (`focus-picker`, `frame-picker`, `card-picker`, `hero-picker`, `w-bone-pickers`, the picker panel of
the key visual, the presets and demo-browser thumbnails) is composed from real captures of the redesigned picker
(marketing `shots/picker_layer_*.png`, `shots/picker_hero.png`; `FLEXSPACE_MEDIA_SRC` points at that folder).

Slot list (reference = manifest file(s), quality ≥ 3; hero references marked ★):

| Slot | Kind | Size (Pages) | Reference |
|---|---|---|---|
| `hero-canvas` | scene | 2400×1500 | ★ shots/control_panel_dark.png, ★ shots/features/control_panel_canvas_dark.png |
| `hero-canvas-light` | scene | 2400×1500 | shots/control_panel_light.png (light theme only) |
| `live-mode` | motion | 1280×800 | ★ gifs/live_mode.gif, gifs/lineal_slider.gif |
| `layers-modes` | motion | 1600×1000 | ★ gifs/studio_modes.gif, ★ shots/flexspace_studio_sculpt.png, shots/features/layers_by_mode_full.png |
| `layer-tabs` | scene | 1200×750 | shots/features/layer_tabs_full.png, shots/features/layers_panel.png |
| `ring-menu` | widget+motion | 1200×1200 | ★ gifs/sculpt_wheel.gif, ★ shots/features/ring_menu_hover.png, ring_menu_inner.png, ring_menu_page.png |
| `add-widget` | scene+motion | 1600×1000 | ★ shots/features/add_browser_full.png, gifs/add_panel.gif, add_browser_search.png |
| `from-property` | motion | 1280×800 | gifs/from_property.gif, shots/features/from_property_full.png |
| `edit-layout` | motion | 1600×1000 | ★ gifs/edit_layout.gif, snapping_guides.png, selection_bar.png, selection_handles.png |
| `layout-widgets` | scene | 1200×750 | shots/features/layout_layer.png, flex_box.png, group.png, frames.png |
| `broken-bindings` | scene | 1200×750 | shots/features/broken_bindings.png, top_bar_status.png |
| `themes` | motion | 1600×1000 | gifs/themes.gif, theme_sunset.png, theme_violet.png, theme_light.png |
| `presets` | scene | 1200×750 | presets_menu.png, top_bar_preset.png, library_panel.png |
| `demos` | scene | 1200×750 | demo_browser_full.png, empty_state_card.png |
| `focus-picker`, `frame-picker` | scene (real crop) | 832×1093, 1473×1219 | ★ shots/picker_layer_male_body.png |
| `hero-picker` | scene (real crops) | 1098×860 | ★ shots/picker_layer_female_body.png, ★ picker_layer_female_face.png |
| `hero-color`, `hero-brushes` | real crops (hero accents) | 524×489, 506×452 | shots/color_picker_ring.png, shots/brush_picker.png |
| `card-picker` | scene (real crop) | 1600×1000 | ★ shots/picker_layer_female_body.png |
| real picker media | shots + loops | as captured | picker_layer_*, picker_hero, picker_face_closeup, gifs/picker_* (see §1) |
| `w-<widget>` (one per widget) | widget | 640×400 | shots/widgets/<widget>.png (21 files) |
| `og-card` | scene | 1200×630 | composed from `hero-canvas` + wordmark |
| `bug-report` | scene | 1200×750 | shots/bug_report.png (support page) |

Docs figures (`<!-- image: ... -->` in help/*.md) show the real media when `build_docs.py` maps them (`REAL`), else
these slots where one fits; a figure with neither is left out. Picker figures show the redesigned picker's captures.

Budget: the whole `docs/` under 60 MB (about 30 MB with the real media). WebP scenes ≤ 350 KB, widget PNGs ≤ 120 KB,
generated store GIFs ≤ 2.5 MB; real store GIFs < 4 MB each.

---

## 2. Visual identity

### Concept: "the canvas is the brand"

FlexSpace is a canvas you design on. The site looks like one: a near-black board with the node-editor grid fading in
and out, product art placed on it like widgets, and the Edit Mode selection frame (corner handles + rotate knob) used
as a graphic device around key visuals and headlines. Bold display type, lots of black, one warm light source.

Five signature devices (use at least two per section, never all five at once):

1. **The grid.** The Node Editor background grid (fine 24 px lines + 120 px major lines), masked with a radial fade.
   `--fs-grid-*` tokens.
2. **The ember.** The logo gradient (gold `#F0B557` → sand `#DCCEB8` → mist `#D5D6D8`) as text fill on one or two
   words per headline, on the primary button and on 1 px gradient borders.
3. **The UI blue.** The add-on's widget accent (`#2F6FFF`) appears only inside product art and on interactive focus
   states, so the product reads as "the blue thing on the warm brand".
4. **Selection frame.** A 1 px frame with 8 px square handles and a round rotate knob, drawn with CSS
   (`.fs-select`) around a hero image or a highlighted word. It may animate in (handles pop, 320 ms).
5. **Keycaps.** Shortcuts as keycaps (`Tab`, `Shift A`, `I`) in JetBrains Mono, raised with a 1 px bottom border.

### Colour

Dark is the default on Pages and the only scheme on Superhive (the fragment paints its own dark background, so it
looks right whatever the store's page colour is). Light is an opt-in theme on Pages (`data-theme="light"` on `<html>`,
toggle in the nav, remembered in `localStorage`; no flash: a 3-line inline script in `<head>` sets it before paint).

Palette (raw):

| Token | Hex | Use |
|---|---|---|
| `--fs-ink-1000` | `#060607` | page bottom, footer |
| `--fs-ink-950` | `#0A0A0C` | page background |
| `--fs-ink-900` | `#0F0F12` | section alt background |
| `--fs-ink-850` | `#141417` | cards |
| `--fs-ink-800` | `#1A1A1E` | raised cards, inputs |
| `--fs-canvas` | `#1D1D1D` | product art canvas (the add-on's dark canvas) |
| `--fs-ink-700` | `#24242A` | hover surfaces |
| `--fs-ink-600` | `#2E2E35` | strong borders |
| `--fs-gold-300` | `#F6CB82` | highlights on dark |
| `--fs-gold-400` | `#F0B557` | **brand primary** (logo top) |
| `--fs-gold-500` | `#E8A94F` | primary hover / pressed |
| `--fs-gold-600` | `#D18A2E` | glow core |
| `--fs-gold-700` | `#9A5B12` | brand text on light |
| `--fs-sand` | `#DCCEB8` | logo middle, quiet accents |
| `--fs-mist` | `#D5D6D8` | logo end |
| `--fs-blue-400` | `#5B8CFF` | UI accent on dark text/links inside art |
| `--fs-blue-500` | `#2F6FFF` | **product UI accent**, focus ring |
| `--fs-blue-600` | `#1F55E0` | UI accent on light |
| `--fs-rose` | `#F78EA5` | docs accent (primary), category chips |
| `--fs-sage` | `#82B3A0` | docs accent (secondary), "works" ticks |
| Picker sides | `#4C8DFF` / `#FF5A5F` / `#F2C94C` / `#A77BFF` | left / right / centre / root, picker art only |
| Anim state | `#5FB34A` / `#E8C93A` / `#A35BD6` / `#E5862E` | animated / keyed / driver / changed, art only |

Text on dark: `#F4F2EE` (primary, 18:1), `#B6B3AD` (secondary, 9:1), `#85827C` (muted, 4.9:1; only ≥ 14 px).
Text on light: `#141416`, `#4A4844`, `#6E6B66` (4.9:1 on `#F7F5F1`). Gold is never body text on light: use
`--fs-gold-700`. Primary button: gold fill, `#1A1206` label (11:1).

Semantic tokens (`--bg`, `--surface-*`, `--text-*`, `--border-*`, `--accent*`, `--ui`, `--focus`) switch with the
theme; components only use semantic tokens.

### Gradients (from the logo)

- `--grad-brand`: `linear-gradient(100deg, #F0B557 0%, #EDB967 18%, #E6C187 40%, #DFCAA8 62%, #D8D2C8 82%, #D5D6D8 100%)`
  (the logo's 9 stops condensed). Headline highlight words (`background-clip:text`), primary button, logo-like rules.
- `--grad-brand-hot`: gold → deeper amber (`#F6CB82 → #F0B557 → #D18A2E`), for the primary button hover.
- `--grad-ember`: brand meets product: `#F0B557 → #E6C187 45% → #5B8CFF 100%`. At most once per page (hero
  underline, or the "Live Mode" pill).
- `--grad-hero-glow`: two radial lights on ink: warm gold top-left (18 % alpha), cool blue bottom-right (14 %).
- `--grad-fade-down`: transparent → `--bg`, to melt images and grids into the page.
- Gradient borders: a `::before` with `--grad-brand` and a 1 px mask (`mask-composite: exclude`); fallback is a
  plain `--border-strong` border.

### Type

Google pair, both variable:

- **Display: Bricolage Grotesque** (opsz 12–96, wght 500–800). Headlines and big numbers. Tight tracking
  (`-0.035em` at display sizes, `-0.02em` at h3), `font-optical-sizing: auto`, weight 750 for h1, 700 h2, 650 h3.
- **Text/UI: Inter** (wght 400–700). Body 400, UI 500, labels 600. `font-feature-settings: "ss01","cv11"`.
- **Mono: JetBrains Mono** 500. Data paths, keycaps, version strings.

Loading: Pages uses `<link rel="preconnect">` + one `css2` URL with `display=swap`. Superhive uses an `@import` of the
same URL as the first line of the fragment's `<style>` (degrades to the fallbacks if stripped).

```
https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Inter:wght@400..700&family=JetBrains+Mono:wght@500&display=swap
```

Fallbacks: display `"Bricolage Grotesque", "Segoe UI Variable Display", "SF Pro Display", system-ui, -apple-system,
"Segoe UI", Roboto, sans-serif`; text `Inter, "Segoe UI Variable Text", system-ui, -apple-system, "Segoe UI",
Roboto, "Helvetica Neue", Arial, sans-serif`; mono `"JetBrains Mono", ui-monospace, "Cascadia Code", "SF Mono",
Consolas, Menlo, monospace`.

Fluid scale (min @ 360 px → max @ 1440 px):

| Token | Size | Line height | Use |
|---|---|---|---|
| `--fs-text-display` | 48 → 104 px | 0.95 | landing hero only |
| `--fs-text-h1` | 40 → 72 px | 1.0 | page heroes |
| `--fs-text-h2` | 32 → 52 px | 1.05 | section titles |
| `--fs-text-h3` | 22 → 30 px | 1.15 | feature rows, cards |
| `--fs-text-h4` | 18 → 21 px | 1.25 | bento tiles, FAQ questions |
| `--fs-text-lead` | 18 → 22 px | 1.5 | intro paragraphs |
| `--fs-text-body` | 16 → 17 px | 1.6 | prose |
| `--fs-text-small` | 14 px | 1.5 | captions, meta |
| `--fs-text-eyebrow` | 12.5 px, 600, `+0.14em`, uppercase | 1 | eyebrows, chips |

Measure: prose 68ch max; leads 56ch; headlines balance with `text-wrap: balance`, prose `text-wrap: pretty`.

### Space, layout, radii

- 4 px base: `--fs-space-1` 4 · 2 8 · 3 12 · 4 16 · 5 20 · 6 24 · 8 32 · 10 40 · 12 48 · 16 64 · 20 80 · 24 96 · 32 128.
- Section padding: `clamp(64px, 10vw, 144px)` block; gutter `clamp(16px, 4vw, 40px)` inline (16 px at phone width).
- Containers: text 760 px, default 1200 px, wide 1360 px. 12-column grid, 24 px gap (16 px under 720 px).
- Breakpoints: 560 / 720 / 960 / 1200 px. Mobile first; no horizontal scroll at 360 px.
- Radii echo the add-on's rounded widgets: `--fs-radius-xs` 4 (keycaps), sm 8 (chips, inputs), md 12 (buttons),
  lg 18 (cards), xl 26 (media frames, bento), 2xl 36 (hero panel), pill 999.

### Depth: shadows, glow, glass

- Shadows are dark and soft, never grey haze: `--fs-shadow-1` (cards), 2 (hover), 3 (media), 4 (hero art, modal-like).
  On light, shadows are lighter and warmer.
- Glow: `--fs-glow-gold` (ring + 40 px bloom) for the primary CTA and the active bento tile; `--fs-glow-blue` for
  product art's focused widget. One glow per viewport.
- Glass: `--fs-glass-bg` (ink at 62 %), `--fs-glass-border` (white 8 %), `backdrop-filter: blur(16px) saturate(140%)`.
  Used for the sticky nav, floating captions over media and the trust row. Always with a solid fallback
  (`@supports not (backdrop-filter: blur(1px))` → `--surface-2`).
- Noise: an optional 2 % SVG noise overlay on hero sections only, to avoid banding in gradients.

### Motion

- Durations: `--fs-dur-1` 120 ms (hover colour), `--fs-dur-2` 200 ms (buttons, chips), `--fs-dur-3` 320 ms (cards,
  reveal), `--fs-dur-4` 600 ms (hero entrance), `--fs-dur-loop` 6–12 s (ambient loops).
- Easing: `--fs-ease-out` `cubic-bezier(.2,.8,.2,1)` (default), `--fs-ease-in-out` `cubic-bezier(.65,0,.35,1)`
  (loops), `--fs-ease-pop` `cubic-bezier(.34,1.56,.64,1)` (handles, toggles; max 1.06 overshoot).
- Rules: animate only `transform`, `opacity`, `filter`, `background-position`. Hover lifts ≤ 4 px. Reveal on scroll
  (Pages only, IntersectionObserver adds `.is-in`; content is visible without JS). Ambient loops are slow and small:
  grid drift, glow breathing, the widget art's own demo loop. Never animate body text.
- `prefers-reduced-motion: reduce`: all durations go to 0.01 ms (token override in `tokens.css`), loops stop,
  reveals show immediately, smooth scroll off. Generated GIFs sit in `<picture>` with a
  `<source media="(prefers-reduced-motion: reduce)" srcset="...-still.webp">` on Pages. On Superhive (if `<picture>`
  is stripped) every GIF has a static first frame that reads as a complete image.

### Iconography and marks

- Icons: Phosphor (regular, 1.5 px stroke at 24 px) as inline SVG on Pages; on Superhive, Unicode-free CSS shapes or
  small PNGs. Phosphor is MIT and already bundled with the add-on, so the visual language matches.
- Wordmark: `FlexSpace.svg` from `B3D-MySpace/docs/brand/` is the logo; it is the one asset used as-is (it is the
  brand mark, not a product image). Min height 24 px; clear space = cap height. On light, the same mark (it was drawn
  for both) on `--surface-1`.
- No cursor/hand illustrations. No stock 3D renders, no fake testimonials, no star ratings.

---

## 3. Component patterns

All classes are prefixed `fs-` on Pages. In Superhive fragments the same patterns are re-declared under `.fsx`
with literal values (see §6).

1. **Nav (Pages).** Sticky glass bar, 64 px: wordmark · Features · Widgets · Picker · Docs · Support · theme toggle ·
   gold "Get it on Superhive" button. Under 960 px: wordmark + button + a `<details>` menu (no JS needed).
2. **Hero.** Eyebrow chip (`v1.4.0 · Blender 5.3+`), display headline with one gradient word, lead, two buttons
   (primary gold → Superhive; ghost → Docs / "See it move" anchor), then the hero art on the grid with
   `--grad-hero-glow`. Under the art: a 4-item caption strip (`Tab` Edit ↔ Live · `Shift A` Add · Right-click bind ·
   `I` key it).
   **Hero art (site home and store page): two equals and three accents.** The two protagonists carry the same
   weight: the Studio Control Panel (FlexSpace; `focus-control` on the site, `frame-control-panel` on the store) in
   the selection frame device, top left, and the Armature Picker (`hero-picker`: the Adult Female Body page with the
   Face page beside it as a card and the Expressions › Gaze pad, the two eyes, floating over the corner between them;
   the face and the gaze are the picker's calling card), in front, right, overlapping the panel's edge, about the
   same size. The accents are clearly smaller: the Ring Menu peeks from behind the picker's top corner, a Color
   Picker (`hero-color`, Ring + Square) and the brushes (`hero-brushes`, Sculpt Brushes with Clay Strips active) sit
   tilted on the panel's lower edge, clear of the picker's body and gaze pad. Positions are % of the art box, so it
   scales; on phones the site mirrors it in a taller box (panel right, picker left, the accents hanging from the
   picker's lower edge, bottom right, clear of the face page) and the store stacks the two windows, their window edges
   lined up, with the accents in a row under them. Nothing covers the headline or the buttons, and every piece stays
   inside the content column (the transparent margins of the window PNGs may bleed past it, the windows may not).
   `hero-*` are made by `make_graphics.py heroart` from real captures (cropped, never scaled up or squashed).
3. **Feature row.** 12-col: text 5 cols, media 7 cols, alternating sides; eyebrow (feature name), h3, 2–3 sentence
   body, a 3-item check list with sage ticks, an optional keycap line. Media in an xl frame with a 1 px gradient
   border; caption below in `--text-3`. Stacks under 960 px (media first).
4. **Bento grid.** 4 × N grid (2 cols under 960, 1 under 560), tiles of 1×1, 2×1, 2×2. Each tile: icon or mini
   widget art, h4, one sentence. One tile per grid is "lit" (gold glow + gradient border). Hover: lift 3 px, border
   brightens.
5. **Widget gallery.** Filter chips (CSS only: radio inputs + `:checked ~` selectors; Pages may enhance with JS):
   All · Buttons · Data · Color & Brush · Layout · Picker. Cards 4-up (2-up mobile): `w-<widget>` art on
   `--fs-canvas`, name, one line from the docs table, a "Modes" chip. Hover plays the card's CSS demo loop.
6. **Comparison / specs.** Two-column spec sheet: label column in eyebrow style, values in body; rows separated by
   1 px `--border-1`. A second variant "Flex Space vs Armature Picker" table: what each canvas is for, where it is
   saved (.blend vs armature data), its modes, its extra widgets.
7. **Trust row** (no testimonials). Glass strip, 4–5 items with icon + two-line label:
   **Blender 5.3+** / built as an extension · **Demo files included** / each opens in its own window ·
   **Full docs** / online and inside Blender · **Public issue tracker** / Report a Bug from Blender · **GPL-3.0** /
   open licence. Updates are not a selling point: buyers download each new version from Superhive, as with any
   product there, so the pages don't mention them.
8. **FAQ.** `<details>`/`<summary>` accordion; summary is an h4-styled question with a `+` that rotates 45°. One
   open at a time is not enforced (no JS). Answers ≤ 3 sentences + a docs link.
9. **CTA band.** Full-bleed, `--grad-hero-glow` + grid, big h2, one sentence, primary button to Superhive, ghost to
   docs. On the store page itself the band points to the docs and support (the buy button is Superhive's own).
10. **Keycap** (`.fs-kbd`), **chip** (`.fs-chip`, pill, eyebrow type), **callout** (Note / Tip, rose and sage left
   rule, used in docs), **code/data path** (`.fs-path`, mono on `--surface-2`, wraps on `.`).
11. **Docs layout (Pages).** 3 columns ≥ 1200 px: left nav (pages), content (760 px), right "On this page" (h2 list).
    Prose styles: h2 with a 1 px gradient rule above, tables with sticky header and zebra rows, figures in lg frames.

Buttons: primary (gold fill, ink label, `--fs-glow-gold` on hover), secondary (ink-800 fill, 1 px border), ghost
(text + arrow, underline grows on hover). Height 48 px (40 px small), radius md, label Inter 600 15–16 px.
Focus: 2 px `--focus` (UI blue) ring with 2 px offset, always visible on keyboard focus.

---

## 4. GitHub Pages: page map

```
docs/
  index.html            Landing
  features.html         Everything, by topic
  widgets.html          Widget gallery
  picker.html           Armature Picker + Rigify
  support.html          Report a bug, troubleshooting, contact
  changelog.html        What changed in each version (generated from CHANGELOG.md)
  docs/index.html       Docs home (cards for each guide)
  docs/<slug>.html      One per help/*.md
  assets/css/tokens.css, site.css     assets/js/site.js (theme toggle, reveal, gallery filter enhancement)
  assets/img/…          generated art (+ images.json registry)   assets/img/store/… Superhive copies
  assets/brand/flexspace.svg
  superhive/page.html, superhive/docs.html   (fragments; not linked in the nav; noindex via robots.txt)
  _design/DESIGN.md
  404.html, robots.txt, sitemap.xml, .nojekyll
```

Nav order: Features · Widgets · Picker · Docs · Changelog · Support. Footer: the same + Superhive,
GitHub issues, licence line ("FlexSpace is GPL-3.0-or-later. Blender is a trademark of the Blender Foundation.").

**Changelog** is a page of the site, `changelog.html`, generated from `CHANGELOG.md` (repo root, Keep a Changelog
style) by `py -3.10 docs/_design/build_changelog.py`. The script takes the nav, footer and `<head>` from
`support.html`, so the shell stays in step with the hand-written pages. Every Changelog link points at it: the static
hrefs, `CHANGELOG_URL` in `site.js` (resolved from the script's own URL, so 404.html works too) and `CHANGELOG_URL`
in `build_docs.py`. Entries are user-facing (Added / Changed / Fixed), in the docs' words; no invented dates.

### index.html (landing)

1. Hero: *Build the Blender panel you always wanted.* (see store copy §5 for the shared hero text).
2. Trust row.
3. "Two modes. One canvas." Edit Mode / Live Mode split card with the `Tab` keycap in the middle.
4. Feature rows (4): Control panels · Bind anything · Pages per mode · Ring Menu.
5. Picker teaser: full-bleed dark band, `picker-hero`, "Pose without hunting for bones", link to picker.html.
6. Bento: the small things (8 tiles).
7. Widget strip: 8 widget cards scrolling horizontally (scroll-snap), "See all widgets" → widgets.html.
8. Story: "3+ years in the making" timeline (see §5, Story).
9. FAQ (6 questions).
10. CTA band.

### features.html

Sticky sub-nav (anchors): Canvas · Widgets · Binding · Pages · Editing · Color & Brush · Presets · Picker · Details.
Each anchor is a feature row group, deeper than the landing (2–4 rows each), every claim lifted from the matching
help page. Ends with the Flex Space vs Armature Picker table and the CTA band.

### widgets.html

Hero ("Every control you need, drawn on the canvas"), filter chips, the gallery (all Flex Space widgets + the picker's
own), then "Add one in a second" (`add-widget`, `from-property`) and the From Property mapping table
(On/off → Toggle, Enum → Enum, Number → Number Field, factor → Lineal, Colour → Color Swatch, Vector → Flex Box of
Number Fields, anything else → Label).

### picker.html

Hero (the `picker-select-transform` recording), "Saved with the rig", posing (+ hands curl, face gaze, pose
recordings), transform tools, the Humanoid Body (Rigify) section with its four pages (Body, Hands, Feet, Face) and
both bodies' page strips, IK/FK puck, knobs and 2D pads (+ IK/FK, gaze, face close-up), bone collections, mirror
(+ mirror recording, Edit Mode shots), repair bindings, the five picker demos.

### docs/ (from help/*.md)

Slugs and order: `getting-started`, `canvas`, `widgets`, `color-brush`, `editing`, `binding`, `picker`, `rigify`,
`recipes`, `demo-files`, `shortcuts`, `troubleshooting`. Conversion rules:

- `%PRODUCT%` → FlexSpace. Keep both `<!-- only: flex_canvas -->` and `<!-- only: armature_picker -->` blocks
  (FlexSpace ships both modules); drop the markers and `<!-- module: ... -->` lines.
- `<!-- hero|image: path | caption -->` → `<figure>` using the matching registry slot and the caption; no slot → omit.
- `<!-- demos -->` → the demo cards, read from each module's `demos/demos.json` (10 demos: 5 Flex Space, 5 pickers),
  no invented ones.
- Bold UI names stay bold; `code` stays mono; tables keep their columns; `> **Note:**` / `> **Tip:**` → callouts.
- "On this page" line → the right-column TOC (and is removed from the body).

### support.html

"Found a bug? Tell us from inside Blender." The in-app flow (Help > Report a Bug... → filled form → Open on GitHub),
the GitHub issue form link, the Superhive messages option, the Troubleshooting table (top 6 rows), and links to docs.

---

## 5. Copy

Voice: confident, concrete, short. Verbs first. Name the real UI ("press `Tab`", "right-click any property"). No
superlatives we can't prove, no "revolutionary", no numbers we don't have. British "colour" in prose, exact UI names
("Color Swatch", "Color Picker") when naming widgets. Never claim speed or performance figures.

### Superhive store page: `superhive/page.html`

Fragment: one `<div class="fsx">`, one scoped `<style>`, no scripts. Sections in order:

**0. Hero**
- Eyebrow: `BLENDER 5.3+ ADD-ON · v1.4.0`
- H1: **Build the Blender panel you always wanted.** (gradient on "you always wanted")
- Lead: FlexSpace turns any area into a canvas for your own controls. Lay out buttons, sliders, toggles, colour
  pickers and a sculpt-ready Ring Menu, bind them to any property, operator or script, and use them while you work.
  And when it's time to animate, the Armature Picker puts every bone of your rig one click away.
- Chips: `Control panels` · `Ring Menu` · `Pages per mode` · `Armature Picker` · `Rigify body picker`
- Links: "Read the docs →" (Pages docs) · "Report a bug →" (issues)
- Art (see the hero art in §3.2): `frame-control-panel` (PNG) in the selection frame, top left, and `hero-picker`
  (Body + Face with the gaze pad, Adult Female) as its equal, right; accents `hero-color`, `hero-brushes` and the Ring
  Menu GIF (`gif-ring-menu`, still PNG for reduced motion). From 860 px the wide composition, 560–859 px a taller one
  (the picker lower, overlapping more), under 560 px the panel and the picker stacked full width with the three
  accents in a row under them (the frame's name tag hides there, it would hit the rotate knob).

**1. Trust row** (as §3.7).

**2. Two modes. One canvas.**
- Edit Mode: *Lay it out.* Add widgets with `Shift A`, drag, resize, rotate, snap, group and frame them.
- Live Mode: *Use it.* Click buttons, drag sliders, flip toggles. Every change is one undo step.
- Centre keycap: `Tab` — "switches between them".

**3. Feature rows**

a. Eyebrow `CONTROL PANELS` — H3 **Every control, one click away.**
   Lights, render settings, playback, modifiers, materials: put the controls you reach for on one canvas, in the
   order that makes sense to you. Buttons run operators or your own Python scripts; sliders, number fields, toggles
   and enums drive any property.
   Ticks: Operator and Custom Script buttons · Sliders, Number Fields, Toggles, Enums, Lists · Labels that read values
   out, images and frames. Art: `live-mode`.

b. `BINDING` — **Bind anything with a right-click.**
   Press `Shift A` > From Property, right-click any property in Blender, and the right widget appears, already bound
   and labelled. Widgets show Blender's animation colours, `I` keys them, and Auto Keying just works.
   Ticks: Data paths, eyedropper or From Property · Follow the active object or pin one · Visible When and Disabled
   When conditions. Art: `from-property`.

c. `PAGES` — **One canvas for every mode.**
   Give each page its moment: always, in one Blender mode, for one object, or for one object in one mode. Switch to
   Sculpt Mode and your sculpt page is there; select the tower and its Geometry Nodes controls show up.
   Ticks: Show When: Always, Mode, Object, Object in Mode · Switch Pages Automatically · A clear notice, and one click
   to enter the right mode. Art: `layers-modes`.

d. `RING MENU` — **A sculpt wheel that stays put.**
   Brushes in the outer ring, toggles and operators in the inner ring, the active brush named in the core. It lives on
   the canvas: no pie to summon, no menu to close. Fill it with every Essentials brush in one click and page through
   the rest.
   Ticks: Brushes, toggles and operators · Pages for more brushes · Disabled When per item. Art (store page): only
   the real Sculpt Wheel recording (`media/store/sculpt-wheel.gif`, still for reduced motion); no redrawn wheel or
   static ring shots in this row.
   (Second line under the row: also on the canvas: Color Picker, Color Palette and Brush Picker.)

e. `EDIT MODE` — **Lay out like a design tool.**
   Smart snapping to edges, centres, equal gaps and the grid. A Selection Bar to align, distribute and match sizes.
   Frames, groups and Flex Boxes keep it tidy; copy and paste work across canvases of the same kind.
   Ticks: Snapping guides · Align, distribute, match size · Frames, groups, Flex Boxes, minimap. Art: `edit-layout`.

f. `ARMATURE PICKER` — **Pose without hunting for bones.**
   A picker is a canvas of buttons that select the bones of your rig. It's saved with the armature, so it travels when
   you link or append the rig, and your Pose Mode keys keep working over it. Using Rigify? Add a full Humanoid Body
   picker (body, hands, feet and face) in one step.
   Ticks: Bone buttons, custom shapes and mirroring · IK/FK switches, knobs and 2D pads · Bone collection toggles.
   Art: `focus-picker` (Adult Male); "In Blender": `picker-face-gaze`, `picker-hands-curl`, `picker-ikfk` GIFs.
   The "See it in action" section ends with `picker-select-transform` as big as the Live Mode recording.

g. `PRESETS` — **Build it once. Use it everywhere.**
   Save a canvas as a global preset and add it to any project. Linked canvases know when the preset changed, keep
   your local edits until you choose, and can restore any of the last 5 versions. Export a `.flexspace` file, or
   point your team at a shared presets folder.
   Ticks: Up to date, Modified and update badges · `.flexspace` export and import · Shared team folder.
   Art: `presets`.

**4. Bento — "The details that make it feel native."**
- **Tooltips that explain.** Rest on a widget for its operator or property, its data path, and why it can't run.
- **Broken bindings, found.** The top bar counts them; one click frames the next one.
- **Your keys still work.** Canvas keys come first; everything else goes to Blender's keymap, custom ones included.
- **Every change, one undo.** A slider drag, a toggle click, a paste: one step each.
- **Themes.** Auto, Dark or Light, plus themes of your own for colours, shapes and type. (lit tile, `themes`)
- **Add in a second.** `Shift A`, start typing, `Enter`. (`add-widget`)
- **Demo files.** Finished canvases open in their own window; your file stays untouched. (`demos`)
- **Report a bug from Blender.** Versions, system and recent errors filled in for you.

**5. Widget gallery — "Every widget, bound to anything."**
Static grid (no filters on the store): Operator, Custom Script, Toggle, Enum, Color Swatch, Color Picker, Color
Palette, Brush Picker, Ring Menu, List, Lineal slider, Number Field, Label, Image, Frame, Flex Box, Group, then the
picker's: Bone Collection toggle, Radial slider, Lineal 2D slider, Button / Button Image / Geometry Shape. Each with
its one-line description from the docs table.

**6. Picker spotlight — "Rigify? One step."**
In the picker's Edit Mode, press `Shift A` and choose **Bone Picker > Humanoid Body (Rigify)**. You get Adult Male or
Adult Female shapes, with Body, Hands, Feet and Face pages, IK/FK switches next to each IK hand and foot, and colours
that read at a glance: left blue, right red, centre yellow. Then "Four pages, two bodies.": the
`picker-layer-*` strips, Adult Female (with a line per page) and Adult Male, Body · Face · Hands · Feet.

**7. What's inside (specs)**
| | |
|---|---|
| Requires | Blender 5.3 or newer |
| Version | 1.4.0 |
| Editors | Flex Space (control panels) and Armature Picker (rig pickers) |
| Saved in | Your .blend (canvases), the armature data (pickers), your user folder (global presets) |
| Sharing | `.flexspace` preset files, shared presets folder |
| Demo files | Studio Control Panel, Viewport Shading Panel, Animation Controls, FlexSpace Studio, Sculpt Wheel, Rigify Human Picker, Simple Biped Picker, Rigify Male Body Picker, Rigify Female Body Picker, Rigify Character Picker (10) |
| Docs | Online at jfranmatheu.github.io/flexspace and in the Help menu |
| Support | Report a Bug inside Blender, GitHub issues, Superhive |
| Licence | GPL-3.0-or-later |

**7b. Story — "3+ years in the making."** (also on the landing, before the FAQ)
Lead: Built and refined by an independent developer since 2023. A timeline (vertical on phones, horizontal rows from
720 px, nodes drawn as Edit Mode handles, the last one "Now"). Verified milestones only, nothing else, no numbers:
Sep 2023 Armature Picker development starts · 25 Oct 2023 first public preview of interactive picker editing on X
(`https://x.com/jfranmatheu/status/1717207033701617889`) · Dec 2023 the shared base (MySpace, later FlexSpace) begins,
the picker becomes one of its modules · Jan–Mar 2024 MySpace 1.0 / 1.1 betas and FlexSpace 1.3 beta for Blender 4.0 ·
Oct 2026 FlexSpace becomes a Blender extension (5.2) · Nov 2026 FlexSpace 1.4.0 for Blender 5.3 (current). Then the
post's own line as a quote, "made by one independent developer, J. Fran Matheu", and two links: "See the first
preview on X" (the post) and "Follow the development" (`https://x.com/jfranmatheu`).

**8. FAQ — "Questions, answered."**
- *Which Blender versions does it support?* Blender 5.3 or newer. FlexSpace is a Blender extension: install the zip
  from **Edit > Preferences > Get Extensions > Install from Disk...**.
- *Is the Armature Picker included?* Yes. FlexSpace comes with two canvases: Flex Space for control panels and
  Armature Picker for rigs.
- *Does the picker work with my rig?* Any armature works: import selected bones and place their buttons. Rigify rigs
  get a full Humanoid Body picker in one step. Buttons follow renamed bones, and **Repair Bone Bindings** fixes the rest.
- *Can my team share panels?* Yes. Save a canvas as a global preset, export it as a `.flexspace` file, or set a shared
  presets folder on a network drive.
- *Will my shortcuts still work?* Yes. The canvas uses its own keys first; any other key goes to Blender's keymap,
  Industry Compatible and custom bindings included.
- *Can a button run my own Python?* Yes, with a Custom Script button. Buttons from an untrusted file ask before running.
- *What if something breaks?* Open **Help > Report a Bug...** in the canvas header: it opens a GitHub issue with your
  versions and recent errors filled in.

**9. Closing band — "Make Blender fit your hands."**
Line: Start with a demo, then build the panel your workflow deserves. Links: "Read the docs" · "Report a bug".

### Superhive store docs: `superhive/docs.html`

Same fragment rules. A one-page guide with a top index (anchor links; CSS `:target` highlights the section in view)
and a link to the full online docs on every section.

Index title: **FlexSpace Guide** — sub: "Everything you need to get going. The full docs live at
jfranmatheu.github.io/flexspace/docs."

1. **Install** — Download the zip from your Superhive library, then in Blender: **Edit > Preferences > Get Extensions**,
   the menu at the top right, **Install from Disk...**, pick the zip. Requires Blender 5.3 or newer.
2. **Your first canvas** — Three steps: open an area's Editor Type menu and pick **Flex Space**, click **New**; press
   `Tab` for Edit Mode and `Shift A` to add a widget; set its Data Path (or use From Property), then `Tab` back and
   use it.
3. **Edit Mode and Live Mode** — `Tab` switches. Edit Mode builds the layout; Live Mode uses it. On a picker, Live
   Mode is Blender's Pose Mode.
4. **Add widgets** — The Add Widget panel: type to search, `Enter` adds; categories Buttons, Data, Tools, Graphics,
   Layout (and Bone Picker in a picker). **From Property**: right-click any property and get the right widget, bound.
5. **Bind properties** — Data paths, the eyedropper, following the active object or pinning one, Visible When /
   Disabled When, animation colours and `I` / `Alt I` / `Backspace`.
6. **Pages and modes** — Show When (Always, Mode, Object, Object in Mode), Switch Pages Automatically, the notice
   and its Enter / Select buttons, `M` to move widgets between pages.
7. **Editing tools** — Select, `G` `R` `S`, handles, smart snapping, Selection Bar, groups (`Ctrl G`), frames
   (`Ctrl J`), Flex Boxes, copy and paste, minimap, themes.
8. **Color & brush widgets** — Color Picker (Wheel or Ring + Square), Color Palette, Brush Picker, Ring Menu (rings,
   items, pages, look).
9. **The Armature Picker** — Make one, pose with it, transform tools (`T`), bone names, bone collections, mirror.
10. **Picker with Rigify** — Humanoid Body in one step (Body, Hands, Feet and Face pages), colours and views, toes
    for Rigify, the IK/FK puck, repair bindings.
11. **Presets and sharing** — Global presets, the top bar badges, Overwrite / Sync / Unlink, Restore Previous
    Version, `.flexspace` export/import, shared presets folder, the Library.
12. **Shortcuts** — Keycap tables: everywhere, Edit Mode, while transforming, Live Mode, picker.
13. **Troubleshooting** — The top rows of the docs table (widgets gone, dashed outline, ⚠ N broken, red operator
    button, Run Untrusted Code?, `Shift A` does nothing).
14. **Report a bug** — Help > Report a Bug... → write what happened → Open on GitHub. Or open an issue by hand.

Each section: h2, one-sentence summary in lead style, 3–8 bullets or a short table, one generated figure at most,
"Full guide →" link to the matching Pages doc.

---

## 6. Superhive fragment rules (both files)

- Root: exactly one `<div class="fsx">`. First child: one `<style>`. No `<html>`, `<head>`, `<body>`, `<meta>`,
  `<link>`, `<script>`, no inline event handlers, no `<iframe>`, no `<video>`.
- Every selector starts with `.fsx` (`.fsx`, `.fsx .fs-hero h1`, `.fsx a:hover`). No `:root`, `html`, `body`, `*`
  alone, no global resets: reset only inside (`.fsx *, .fsx *::before, .fsx *::after { box-sizing: border-box }`).
- Values are **literal** (hex, px, clamp) generated from `tokens.css`, not `var()`, so a sanitizer that drops custom
  properties can't break the page. `@keyframes` names are prefixed `fsx-` to avoid clashes.
- `.fsx` paints its own dark background (`#0A0A0C`), radius 26 px, `overflow: hidden`, `color` and `font-family`
  set, `line-height` set; it never relies on the store's styles. Links are styled inside `.fsx` only.
- `@import` of the Google Fonts URL is the first rule; everything degrades to the system stacks.
- Images: absolute URLs `https://jfranmatheu.github.io/flexspace/assets/img/store/<slot>.png|.jpg|.gif` (redrawn) or
  `.../assets/media/store/<name>.png|.jpg|.gif` (real), with `width`,
  `height`, `alt` and `loading="lazy"` (except the hero). No WebP, no MP4.
- Interactions: CSS only (`:hover`, `:focus-visible`, `:target`, `<details>`, scroll-snap, `@keyframes`), all wrapped
  by `@media (prefers-reduced-motion: reduce)` overrides. No `position: fixed`.
- Width: fluid to 100 % of the store column; tested at 360, 720 and 1100 px. No horizontal overflow.

---

## 7. Open questions for the author

1. Does the Superhive editor keep `<picture>`, `<details>` and inline SVG? If not, fall back to `<img>` + GIF first
   frames, plain sections, and PNG icons (the fragments are written so each degrades cleanly).
