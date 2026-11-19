# Superhive fragments

HTML for the FlexSpace product on Superhive, plus a local preview.

| File | What it is |
|---|---|
| `page.src.html` | Source of the store page: classes and one `<style>`. Edit this one |
| `page.html` | Built from `page.src.html`. Paste it into the product **description** |
| `docs.src.html` | Source of the documentation tab, written the same way. Edit this one |
| `docs.html` | Built from `docs.src.html`. Paste it into the product **documentation** |
| `page.old.html`, `docs.old.html` | The fragments as they were before Superhive (one `<style>` and classes, "Layer" wording). Kept for reference: they show the intended design |
| `preview.html` | Nothing to paste (local only): shows a fragment the way Superhive would, and checks the rules below |

Neither fragment is linked from the site (only `preview.html`, which is `noindex`, loads them), and `sitemap.xml` leaves `/store/` out. If they ever show up in search results, rename them `page.fragment.txt` / `docs.fragment.txt` (and the paths in `preview.html`).

## What Superhive keeps

Superhive's description editor is Summernote, and the HTML is sanitized on the server when you save. Measured by saving probes and reading them back (2026-11-19):

- **No `<style>`, no `class`, no `id`.** The `<style>` tag goes but its CSS text stays, as visible text. That is why the old fragments showed a wall of CSS. Everything must be inline `style=""`.
- **Tags kept:** `div p span a img video source iframe table thead tbody tr th td h1-h6 ul ol li dl dt dd blockquote strong b em i u s del ins cite small code kbd sup sub pre abbr hr br font`. Anything else (`section`, `article`, `figure`, `figcaption`, `picture`, `details`, `summary`, `svg`, `mark`...) is unwrapped: its text stays, the tag goes.
- **Attributes kept:** `style`, `title`, `href`, `target`, `src`, `width`, `height`, `alt`, `colspan`, `align` (img, table, td), `color` (font); on `<video>` `poster controls autoplay muted loop playsinline`, on `<source>` `src type`. Gone: `class id data-* aria-* role lang loading decoding srcset sizes rel` and the old table attributes.
- **CSS kept** (inside `style=""`): `display` (block, inline-block, flex, inline-flex, none), the flex properties, `position` relative/absolute with `top right bottom left`, widths and heights (px, %, em, rem, vw, `calc()`), margins and paddings (negative too), borders (`border` and its four sides as shorthands, `border-color/-style/-width`) and `border-radius` (not per-side or per-corner longhands), `background`/`background-color`/`background-image` with colours, `linear-gradient()` and `radial-gradient()` only, `background-position`, `color`, `font-family`, `font-size` (px/em/rem), `font-weight`, `font-style`, `line-height`, `letter-spacing`, `text-align`, `text-decoration`, `vertical-align`, `white-space`, `overflow` (not `overflow-x`/`-y`), `list-style`, `float`, `clear`, `cursor`, `aspect-ratio`, `!important`.
- **CSS stripped:** `gap` (all kinds), grid templates and placement, `transform`, `transition`, `animation`, `box-shadow`, `text-shadow`, `filter`, `opacity`, `object-fit`, `background-size`/`-repeat`/`-clip` and `url()` backgrounds, `z-index`, `inset`, `outline`, `text-transform`, `font-feature-settings`, `text-overflow`, `word-break`, `pointer-events`, `visibility`, any `min()`, `max()`, `clamp()`, `var()` and custom properties. No hover, no media or container queries, no keyframes.
- **The host page** (Bootstrap 5, `box-sizing: border-box` everywhere) sets Inter 16/24 in a purple-grey, list bullets and padding, `p` line-height 1.6 `!important` (the build gives every `<p>` whose line-height isn't 1.6 its own with `!important`), heading weight 600 and bottom margin `!important`, `li` bottom margins, `a` weight 600, a grey bar on `blockquote`. So every tag we emit sets what it relies on, with `!important` where the host uses it. The column is 832 px at desktop widths and about 343-358 px on phones.
- Length is not a problem (800 KB saved fine). `<video autoplay muted loop playsinline>` with an MP4 from GitHub Pages autoplays.

## How the page is built

```
py -3.10 docs/_design/build_superhive.py            # builds page.html and docs.html (or name one: page, docs)
py -3.10 docs/_design/build_superhive.py --check docs/store/superhive/page.html
py -3.10 docs/_design/build_superhive.py --sanitize docs/store/superhive/page.html   # what Superhive would keep
```

`page.src.html` and `docs.src.html` are plain HTML with class names and one `<style>` of simple selectors (`.class`, `tag`, `.a .b`, `.a > b`, comma lists). The build inlines the rules into each element's `style=""` in browser cascade order (specificity, then source order, `!important` respected, the element's own `style=""` last), drops the classes, the `<style>` and comments, and validates the result. **The build fails** on any tag, attribute, CSS property or value Superhive would strip, a leftover `class`/`id`, a relative link or media URL, a media file missing from `docs/assets/`, an `<img>` without `width`, `height` and `alt`, or a `<video>` without autoplay, muted, loop, playsinline, a poster and an MP4 source. Its output passes `--sanitize` unchanged.

`data-fit="16/10"` on an `<img>` or `<video>` letterboxes it inside a frame of that aspect (what `object-fit: contain` did): the build sizes it from its `width`/`height`.

How the design survives without the stripped CSS:

- **Responsive without media queries.** Cards sit in a flex row with `flex-wrap` and `flex-basis: calc((500px - 100%) * 999)`: below a 500 px row everything stacks, above it `min-width` (50 %, 33.333 %) sets the columns. Gaps are a negative-margin row with padded cells.
- **Two hero compositions.** The overlapping hero art (desktop) and the stacked one (phone) are both in the page; `max-width: calc((100% - 500px) * 999)` and its mirror collapse the one that doesn't fit to 0 x 0 (the switch is at a 700 px content width, so the overlapping art only shows in the 832 px desktop column). The art is the same real text + image layers as before, positioned in % of a box with `aspect-ratio`.
- **Glows** are `radial-gradient()` backgrounds; **gradient borders** are a 1 px padded gradient box around the card; **shadows** became borders; the gold-to-silver gradient text is a solid gold.
- **Baked into images** (only where CSS can't do it): the blueprint grid behind some sections (`grid-bg.png`, needs `background-size`), the tilted, shadowed Color Picker and Brush Picker in the hero (`hero-*-tilt.png`, need `transform` and `filter`). All copy, headings, lists, the FAQ and tables are real text.
- **GIFs became `<video>`** with the MP4 from `assets/media/` and the existing `-still.png` as poster; the two drawn GIFs got their own MP4s (`assets/media/store/gif-*.mp4`). `aria-label` is stripped, so the build copies each video's fallback text into its `title`, which is kept. `docs/_design/make_superhive_media.py` makes the new media.
- **Dropped:** hover and every animation, the `<details>` FAQ (now static question/answer blocks), the eyebrows' and chips' `text-transform` (the capitals are typed), Bricolage Grotesque and JetBrains Mono (the host serves Inter at 400-700 and 900, and IBM Plex Mono: display text uses Inter 700 with tight letter-spacing, keycaps and dates IBM Plex Mono). The store page has no in-page links, so nothing was lost to the missing `id`s.
- **The docs tab** keeps its 15 sections, tables and widget reference as real text. Its contents list can't jump (no `id`s), so it is a plain overview of the sections, and each section ends with its link to the full guide online instead of "↑ Contents". The diamond bullets are a gold square with its corners painted over by four `linear-gradient()`s (no `transform`); the step numbers and the section numbers (`01 /`) are typed; the widget thumbnails are cropped to the old 136 x 84 tile by a clipping box (no `object-fit`); the table stripes are a class on every other row (no `:nth-child`). Long URLs carry a zero-width space after `github.io/` so they break there on phones.

## How to paste

1. Push `docs/` to `main` first: the page loads its images and videos from `https://jfranmatheu.github.io/flexspace/assets/`.
2. Build (`py -3.10 docs/_design/build_superhive.py`) and open `page.html` in a text editor.
3. In Superhive's description editor (and for `docs.html`, the documentation editor), switch to **source mode** (the `</>` button), select all, delete, paste the whole file, switch back and save.
4. Open the product page at desktop and phone width. If something looks off, compare with `preview.html`.

## Preview locally

```
py -3.10 -m http.server 8000 -d docs
```

Then open http://localhost:8000/store/superhive/preview.html.

- **Store page / Store docs** switches the fragment; **360 / 720 / 832** sets the white column (832 is the desktop column).
- **Sanitize like Superhive** runs the same unwrapping and filtering as Superhive before showing it, so you see what the store will show.
- **Host defaults** adds what the store page does to bare tags (bullets, margins, heading weights, link colour), from the measurements above. It is not Superhive's stylesheet.
- **Local images** swaps the absolute URLs for the local files, so it works before you push.
- The **Superhive rules** box runs the same checks as the build, and checks that every media file exists in `docs/assets/`.

## Images

Generated art comes from `docs/_design/make_graphics.py` and `make_store_extras.py`, real screenshots and recordings from `make_media.py`, and the Superhive-only media from `make_superhive_media.py`. To change a picture, overwrite the file at the same path and push; the page doesn't need editing (re-paste only if Superhive caches the old HTML).
