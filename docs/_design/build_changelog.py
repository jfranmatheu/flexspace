"""Build the site's changelog page (docs/changelog.html) from CHANGELOG.md at the repository root.

    py -3.10 docs/_design/build_changelog.py

CHANGELOG.md follows Keep a Changelog: "## <version>" per release (newest first, an optional " - <date>"),
"### Added / Changed / Fixed / Removed / Deprecated / Security" groups, optional "####" subheadings, "- " items.
Paragraphs between the title and the first version become the page's lead. Inline Markdown: **bold**, `code`
(key names such as `Shift A` become keycaps), [links](url).

The page shell (<head>, nav, footer) is taken from support.html, so the changelog stays in step with the
hand-written pages: only the title, description, canonical/og URLs and the current nav item are changed.
Standard library only. Rewrites docs/changelog.html on every run.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # docs/_design
DOCS = HERE.parent                              # docs/ (the Pages root)
REPO = DOCS.parent
SRC = REPO / "CHANGELOG.md"
SHELL = DOCS / "support.html"
OUT = DOCS / "changelog.html"
SITE_URL = "https://jfranmatheu.github.io/flexspace/"

TITLE = "Changelog: FlexSpace"
OG_TITLE = "FlexSpace changelog"
DESCRIPTION = "What changed in each version of FlexSpace: new widgets, editing tools, picker features and fixes."

KINDS = {"added": "Added", "changed": "Changed", "fixed": "Fixed", "removed": "Removed",
         "deprecated": "Deprecated", "security": "Security"}
KEY = re.compile(r"^(?:(?:Shift|Ctrl|Alt|Cmd|Tab|Esc|Enter|Backspace|Delete|Home|Space|F\d{1,2}|[A-Z0-9])"
                 r"(?:[ +](?=\S)|$))+$")


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def inline(text: str) -> str:
    """**bold**, `code` / `Key`, [text](url). Everything else is escaped."""
    out, pos = [], 0
    for m in re.finditer(r"`([^`]+)`|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)", text):
        out.append(esc(text[pos:m.start()]))
        if m.group(1) is not None:
            code = m.group(1)
            if KEY.match(code):
                out.append(f'<kbd class="fs-kbd">{esc(code)}</kbd>')
            else:
                out.append(f'<code class="fs-path">{esc(code)}</code>')
        elif m.group(2) is not None:
            out.append(f"<strong>{inline(m.group(2))}</strong>")
        else:
            url = m.group(4)
            ext = url.startswith(("http://", "https://"))
            attrs = ' rel="noopener"' if ext else ""
            out.append(f'<a href="{esc(url)}"{attrs}>{inline(m.group(3))}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def slug(s: str) -> str:
    return "v" + re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") if re.match(r"\d", s) else \
        re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse(md: str):
    """-> (lead paragraphs, [version dict]). A version: name, date, blocks; a block is ('p', text),
    ('group', kind), ('sub', text) or ('list', [items])."""
    lead, versions = [], []
    cur = None
    para: list[str] = []
    items: list[str] | None = None

    def flush():
        nonlocal para, items
        target = cur["blocks"] if cur else None
        if para:
            text = " ".join(x.strip() for x in para)
            (target.append(("p", text)) if target is not None else lead.append(text))
            para = []
        if items is not None:
            if target is None:
                sys.exit("CHANGELOG.md: a list before the first version")
            target.append(("list", items))
            items = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            flush()
            continue
        m = re.match(r"^## +(.+)$", line)
        if m:
            flush()
            name, _, date = m.group(1).partition(" - ")
            cur = {"name": name.strip().strip("[]"), "date": date.strip(), "blocks": []}
            versions.append(cur)
            continue
        m = re.match(r"^### +(.+)$", line)
        if m:
            flush()
            if cur is None:
                sys.exit("CHANGELOG.md: a ### group before the first version")
            name = m.group(1).strip()
            cur["blocks"].append(("group", name))
            continue
        m = re.match(r"^#### +(.+)$", line)
        if m:
            flush()
            cur["blocks"].append(("sub", m.group(1).strip()))
            continue
        m = re.match(r"^[-*] +(.+)$", line)
        if m:
            if para:
                flush()
            if items is None:
                items = []
            items.append(m.group(1).strip())
            continue
        if not line.strip():
            if para:
                flush()
            continue
        if items is not None and raw.startswith((" ", "\t")):
            items[-1] += " " + line.strip()          # a wrapped list item
            continue
        if items is not None:
            flush()
        para.append(line)
    flush()
    if not versions:
        sys.exit("CHANGELOG.md: no '## <version>' heading")
    return lead, versions


def render_version(v: dict, latest: bool) -> str:
    vid = slug(v["name"])
    is_release = bool(re.match(r"\d", v["name"]))
    label = esc(v["name"])
    meta = []
    if latest and is_release:
        meta.append("Latest")
    if v["date"]:
        meta.append(esc(v["date"]))
    body, group_open = [], False
    for kind, val in v["blocks"]:
        if kind == "group":
            if group_open:
                body.append("</div>")
            key = val.lower()
            cls = f" fs-log__kind--{key}" if key in KINDS else ""
            body.append(f'<div class="fs-log__group"><h3 class="fs-log__kind{cls}">{inline(val)}</h3>')
            group_open = True
        elif kind == "sub":
            body.append(f'<h4 class="fs-log__sub">{inline(val)}</h4>')
        elif kind == "list":
            lis = "".join(f"<li>{inline(i)}</li>" for i in val)
            body.append(f'<ul class="fs-log__list">{lis}</ul>')
        else:
            body.append(f"<p>{inline(val)}</p>")
    if group_open:
        body.append("</div>")
    cls = "fs-log__ver" + (" fs-log__ver--latest" if latest and is_release else "") +         ("" if is_release else " fs-log__ver--note")
    meta_html = f'<p class="fs-log__meta">{" &middot; ".join(meta)}</p>' if meta else ""
    heading = f'<h2 class="fs-log__num" id="{vid}-h"><a href="#{vid}">{label}</a></h2>'
    inner = "\n          ".join(body)
    return (f'      <article class="{cls}" id="{vid}" aria-labelledby="{vid}-h">\n'
            f'        <header class="fs-log__aside">{heading}{meta_html}</header>\n'
            f'        <div class="fs-log__body">\n          {inner}\n        </div>\n'
            f'      </article>')


def build_main(lead: list[str], versions: list[dict]) -> str:
    latest = next((v for v in versions if re.match(r"\d", v["name"])), None)
    lead_html = "".join(f'<p class="fs-lead">{inline(p)}</p>' for p in lead[:1])
    extra = "".join(f'<p class="fs-muted fs-small" style="margin-top:12px">{inline(p)}</p>' for p in lead[1:])
    chip = f'<span class="fs-chip fs-chip--accent"><span class="fs-dot"></span>Changelog</span>'
    arts = "\n".join(render_version(v, v is latest) for v in versions)
    return f"""<main id="main">

  <section class="fs-hero fs-hero--page" aria-labelledby="page-title">
    <div class="fs-grid-bg" aria-hidden="true"></div>
    <div class="fs-wrap">
      <div class="fs-hero__copy">
        {chip}
        <h1 class="fs-h1" id="page-title">What's new in <span class="fs-grad-text">FlexSpace.</span></h1>
        {lead_html}{extra}
        <div class="fs-actions">
          <a class="fs-btn fs-btn--primary" href="#{slug(latest['name']) if latest else slug(versions[0]['name'])}">See {esc(latest['name']) if latest else 'the latest'}</a>
          <a class="fs-btn fs-btn--secondary" href="docs/">Read the docs</a>
        </div>
      </div>
    </div>
  </section>

  <section class="fs-section fs-section--alt" aria-label="Versions">
    <div class="fs-wrap">
      <div class="fs-log">
{arts}
      </div>
      <p class="fs-muted fs-small" style="margin-top:56px">Found a problem in this version? <a href="support.html">Tell us from Blender</a>.</p>
    </div>
  </section>

</main>"""


def sub1(pattern: str, repl: str, s: str, what: str, count: int = 1, flags: int = 0) -> str:
    out, n = re.subn(pattern, repl, s, flags=flags)
    if (count and n != count) or (not count and n == 0):
        sys.exit(f"build_changelog: support.html changed, can't find {what} ({n} matches)")
    return out


def shell(main_html: str) -> str:
    s = SHELL.read_text(encoding="utf-8")
    url = SITE_URL + OUT.name
    s = sub1(r"<title>[^<]*</title>", f"<title>{esc(TITLE)}</title>", s, "<title>")
    s = sub1(r'(<meta name="description" content=")[^"]*(")', rf"\g<1>{esc(DESCRIPTION)}\2", s, "description")
    s = sub1(r'(<link rel="canonical" href=")[^"]*(")', rf"\g<1>{url}\2", s, "canonical")
    s = sub1(r'(<meta property="og:title" content=")[^"]*(")', rf"\g<1>{esc(OG_TITLE)}\2", s, "og:title")
    s = sub1(r'(<meta property="og:description" content=")[^"]*(")', rf"\g<1>{esc(DESCRIPTION)}\2", s, "og:description")
    s = sub1(r'(<meta property="og:url" content=")[^"]*(")', rf"\g<1>{url}\2", s, "og:url")
    s = sub1(r'(<meta name="twitter:title" content=")[^"]*(")', rf"\g<1>{esc(OG_TITLE)}\2", s, "twitter:title")
    s = sub1(r'(<meta name="twitter:description" content=")[^"]*(")', rf"\g<1>{esc(DESCRIPTION)}\2", s,
             "twitter:description")
    s = sub1(r'(<a href="support\.html") aria-current="page"', r"\1", s, "the current nav item", count=0)
    s = sub1(r'<a href="changelog\.html" data-link="changelog">', '<a href="changelog.html" data-link="changelog" '
             'aria-current="page">', s, "the Changelog links", count=0)
    s = sub1(r'<main id="main">.*?</main>', lambda m: main_html, s, "<main>", flags=re.S)
    return s


def main() -> None:
    lead, versions = parse(SRC.read_text(encoding="utf-8"))
    page = shell(build_main(lead, versions))
    OUT.write_text(page, encoding="utf-8", newline="\n")
    items = sum(len(b[1]) for v in versions for b in v["blocks"] if b[0] == "list")
    print(f"  {OUT.relative_to(DOCS)}  {len(page) // 1024} KB, {len(versions)} versions, {items} items")


if __name__ == "__main__":
    main()
