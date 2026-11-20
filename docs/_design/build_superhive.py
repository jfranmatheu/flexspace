"""Build the Superhive fragments (docs/store/superhive/page.html, docs.html) from their sources (*.src.html).

    py -3.10 docs/_design/build_superhive.py                 # build page.html (and docs.html if docs.src.html exists)
    py -3.10 docs/_design/build_superhive.py page            # just one
    py -3.10 docs/_design/build_superhive.py --check FILE    # validate a built fragment, exit 1 on any problem
    py -3.10 docs/_design/build_superhive.py --sanitize FILE # print what Superhive's sanitizer would keep of FILE

Why: Superhive sanitizes the product description on the server. It drops <style>, every class and id, and most
tags and CSS properties (the measured whitelist is in docs/store/superhive/README.md). What survives is plain
markup with inline style="" attributes. Writing a 100 KB page of inline styles by hand is unmaintainable, so the
source is authored with class names and ONE <style> block, and this tool inlines it:

  - Selectors: simple ones only. A compound is `tag`, `.class`, `tag.class` or `.a.b`; complex selectors join
    compounds with a space (descendant) or `>` (child). Lists with commas are fine. No pseudo-classes, no at-rules.
  - The cascade is the browser's for these selectors: rules are applied in (specificity, source order) and the
    element's own style="" comes last, so it wins. `!important` is honoured.
  - `data-fit="16/10"` on an <img> or <video> letterboxes it in a frame of that aspect (object-fit is stripped):
    the tool sizes it from its width/height attributes. <video> also gets aspect-ratio from its attributes.
  - Every <p> gets its line-height with !important (the host forces 1.6 on <p>), and a <video> without a title
    gets its fallback text as title (its accessible name: aria-label is stripped).
  - class attributes, the <style> block and comments are dropped; the result is validated (see validate()) and
    the build FAILS on anything Superhive would strip, on a leftover class/id, on a relative media URL, on a
    media file missing from docs/assets/, and on an <img> without width, height or alt.

Standard library only.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent          # docs/_design
DOCS = HERE.parent                              # docs/ (the Pages root)
STORE = DOCS / "store" / "superhive"
SITE = "https://jfranmatheu.github.io/flexspace/"
ASSETS = SITE + "assets/"

# ----------------------------------------------------------------------------------------------- the whitelist
# Measured on Superhive (save a probe, read it back). Keep in sync with docs/store/superhive/README.md.
# Only what was measured: no overflow-x/-y, no per-side border-*-width/-color/-style, no per-corner radius.
KEPT_TAGS = set("""div p span a img video source iframe table thead tbody tr th td h1 h2 h3 h4 h5 h6 ul ol li dt dd
    blockquote strong b em i u s del ins cite small code kbd sup sub pre abbr hr br font""".split())
VOID = {"img", "br", "hr", "source", "input", "meta", "link", "col", "area", "base", "embed", "param", "track", "wbr"}
GLOBAL_ATTRS = {"style", "title"}
TAG_ATTRS = {
    "a": {"href", "target"},
    "img": {"src", "width", "height", "alt", "align"},
    "video": {"poster", "controls", "autoplay", "muted", "loop", "playsinline", "width", "height"},
    "source": {"src", "type"},
    "iframe": {"width", "height", "src", "frameborder", "allowfullscreen"},
    "table": {"align"},
    "td": {"align", "colspan"},
    "th": {"colspan"},
    "font": {"color"},
}
KEPT_PROPS = set("""display flex flex-wrap flex-direction flex-flow flex-basis flex-grow flex-shrink align-items
    align-content align-self justify-content order position top right bottom left
    width min-width max-width height min-height max-height
    margin margin-top margin-right margin-bottom margin-left margin-inline margin-block
    margin-inline-start margin-inline-end margin-block-start margin-block-end
    padding padding-top padding-right padding-bottom padding-left padding-inline padding-block
    padding-inline-start padding-inline-end padding-block-start padding-block-end
    border border-top border-right border-bottom border-left border-color border-style border-width border-radius
    border-collapse border-spacing
    background background-color background-image background-position
    color font-family font-size font-weight font-style line-height letter-spacing text-align text-decoration
    vertical-align white-space overflow list-style float clear cursor aspect-ratio""".split())
DISPLAY_OK = {"block", "inline-block", "flex", "inline-flex", "none"}
POSITION_OK = {"relative", "absolute"}
BAD_FUNC = re.compile(r"\b(min|max|clamp|var|url|env|attr)\(", re.I)
GRADIENT = re.compile(r"^(linear|radial)-gradient\(")

ASSET_DIRS = ("img/store/", "media/store/")     # where NEW media must live (existing media/*.mp4 are allowed too)


def _split_top(value: str, sep: str = ",") -> list[str]:
    """Split on sep outside parentheses."""
    out, depth, cur = [], 0, []
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return out


def css_problem(prop: str, value: str) -> str | None:
    """Why Superhive would drop this declaration (None if it keeps it)."""
    p = prop.strip().lower()
    v = value.strip()
    vl = v.lower().replace("!important", "").strip()
    if p.startswith("--"):
        return "custom property"
    if p not in KEPT_PROPS:
        return f"property {p} is stripped"
    if BAD_FUNC.search(vl):
        return "min()/max()/clamp()/var()/url() is stripped"
    if p == "display" and vl not in DISPLAY_OK:
        return f"display:{vl} is stripped or useless (grid-* is stripped)"
    if p == "position" and vl not in POSITION_OK:
        return f"position:{vl} is not kept"
    if p in ("background", "background-image"):
        for layer in _split_top(vl):
            if GRADIENT.match(layer) or (p == "background" and re.fullmatch(r"#[0-9a-f]{3,8}|rgba?\([^)]*\)|transparent|none|[a-z]+", layer)):
                continue
            return f"{p} layer '{layer[:40]}' is not a colour or gradient"
        if p == "background" and re.search(r"\b(padding-box|border-box|content-box|text)\b", vl):
            return "background box keywords are not safe"
    if p == "font-size" and not re.fullmatch(r"[\d.]+(px|rem|em)|inherit", vl):
        return "font-size must be px, rem or em"
    if p == "color" and vl == "transparent":
        return "color:transparent (background-clip:text is stripped: invisible text)"
    return None


def parse_decls(text: str) -> list[tuple[str, str, bool]]:
    out = []
    for part in _split_top(text, ";"):
        if not part.strip():
            continue
        if ":" not in part:
            raise ValueError(f"bad declaration: {part!r}")
        prop, value = part.split(":", 1)
        value = value.strip()
        imp = value.lower().endswith("!important")
        if imp:
            value = value[: -len("!important")].strip()
        out.append((prop.strip().lower(), " ".join(value.split()), imp))
    return out


def decls_to_str(decls: list[tuple[str, str, bool]]) -> str:
    return ";".join(f"{p}:{v}{' !important' if i else ''}" for p, v, i in decls)


# ----------------------------------------------------------------------------------------------- a tiny DOM
class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text", "kind")

    def __init__(self, kind, tag=None, attrs=None, text=None):
        self.kind = kind            # "el", "text", "comment", "root"
        self.tag = tag
        self.attrs = attrs if attrs is not None else []
        self.children = []
        self.parent = None
        self.text = text

    def get(self, name, default=None):
        for k, v in self.attrs:
            if k == name:
                return v
        return default

    def set(self, name, value):
        for i, (k, _) in enumerate(self.attrs):
            if k == name:
                self.attrs[i] = (k, value)
                return
        self.attrs.append((name, value))

    def drop(self, name):
        self.attrs = [(k, v) for k, v in self.attrs if k != name]

    def classes(self):
        return (self.get("class") or "").split()

    def elements(self):
        for c in self.children:
            if c.kind == "el":
                yield c
                yield from c.elements()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def _add(self, node):
        node.parent = self.cur
        self.cur.children.append(node)

    def handle_starttag(self, tag, attrs):
        n = Node("el", tag, [(k, v) for k, v in attrs])
        self._add(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self._add(Node("el", tag, [(k, v) for k, v in attrs]))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.kind == "el" and n.tag != tag:
            n = n.parent
        if n is None or n.kind != "el":
            return                      # stray end tag
        self.cur = n.parent

    def handle_data(self, data):
        self._add(Node("text", text=data))

    def handle_comment(self, data):
        self._add(Node("comment", text=data))


def parse_html(src: str) -> Node:
    b = _Builder()
    b.feed(src)
    b.close()
    return b.root


def _esc_text(s: str) -> str:
    return html.escape(s, quote=False).replace("\xa0", "&nbsp;")


def _esc_attr(s: str) -> str:
    return html.escape(s, quote=True).replace("&#x27;", "'").replace("\xa0", "&nbsp;")


def serialize(node: Node) -> str:
    out = []

    def walk(n):
        if n.kind == "text":
            # raw text inside <style> must stay raw
            out.append(n.text if (n.parent and n.parent.kind == "el" and n.parent.tag == "style") else _esc_text(n.text))
        elif n.kind == "comment":
            out.append(f"<!--{n.text}-->")
        elif n.kind == "el":
            a = "".join(f" {k}" if v is None else f' {k}="{_esc_attr(v)}"' for k, v in n.attrs)
            out.append(f"<{n.tag}{a}>")
            if n.tag not in VOID:
                for c in n.children:
                    walk(c)
                out.append(f"</{n.tag}>")
        else:
            for c in n.children:
                walk(c)

    walk(node)
    return "".join(out)


# ----------------------------------------------------------------------------------------------- the inliner
_COMPOUND = re.compile(r"^([a-z][a-z0-9]*)?((?:\.[A-Za-z0-9_-]+)*)$")


class Rule:
    __slots__ = ("parts", "spec", "order", "decls", "text")

    def __init__(self, parts, spec, order, decls, text):
        self.parts, self.spec, self.order, self.decls, self.text = parts, spec, order, decls, text


def parse_css(css: str) -> list[Rule]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules, order = [], 0
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel_text, body = m.group(1).strip(), m.group(2)
        if sel_text.startswith("@"):
            raise ValueError(f"at-rules are not supported (Superhive has no <style>): {sel_text}")
        decls = parse_decls(body)
        for sel in sel_text.split(","):
            sel = sel.strip()
            if ":" in sel or "[" in sel or "#" in sel or "*" in sel or "+" in sel or "~" in sel:
                raise ValueError(f"unsupported selector (simple .class / tag / descendant / child only): {sel}")
            tokens = re.findall(r">|[^\s>]+", sel)
            parts, comb, spec_c, spec_t = [], " ", 0, 0
            for t in tokens:
                if t == ">":
                    comb = ">"
                    continue
                cm = _COMPOUND.match(t)
                if not cm:
                    raise ValueError(f"unsupported compound {t!r} in {sel!r}")
                tag = cm.group(1)
                cls = [c for c in cm.group(2).split(".") if c]
                spec_c += len(cls)
                spec_t += 1 if tag else 0
                parts.append((comb, tag, cls))
                comb = " "
            rules.append(Rule(parts, (spec_c, spec_t), order, decls, sel))
            order += 1
    return rules


def _match_compound(el: Node, tag, cls) -> bool:
    if tag and el.tag != tag:
        return False
    have = el.classes()
    return all(c in have for c in cls)


def _matches(el: Node, parts) -> bool:
    """Right-to-left match of descendant / child chains."""
    def rec(node, i):
        comb, tag, cls = parts[i]
        if not _match_compound(node, tag, cls):
            return False
        if i == 0:
            return True
        if comb == ">":
            p = node.parent
            return p is not None and p.kind == "el" and rec(p, i - 1)
        p = node.parent
        while p is not None and p.kind == "el":
            if rec(p, i - 1):
                return True
            p = p.parent
        return False

    return rec(el, len(parts) - 1)


def _apply(acc: list, decls) -> None:
    for prop, value, imp in decls:
        for i, (p, _, pi) in enumerate(acc):
            if p == prop:
                if pi and not imp:
                    break               # an !important already won
                del acc[i]
                acc.append((prop, value, imp))
                break
        else:
            acc.append((prop, value, imp))


def _fit(el: Node, frame: str, acc: list) -> None:
    fw, fh = (float(x) for x in frame.split("/"))
    w, h = float(el.get("width")), float(el.get("height"))
    a, fa = w / h, fw / fh
    pct = 100.0 if a >= fa else a / fa * 100.0
    _apply(acc, [("width", f"{pct:.2f}%".replace(".00%", "%"), False), ("height", "auto", False),
                 ("margin", "0 auto", False), ("flex", "none", False)])


def inline(src: str) -> str:
    root = parse_html(src)
    styles = [n for n in root.elements() if n.tag == "style"]
    if len(styles) > 1:
        raise ValueError("one <style> block only")
    rules = parse_css("".join(c.text for c in styles[0].children)) if styles else []
    # drop the <style> and every comment
    def prune(n):
        n.children = [c for c in n.children if c.kind != "comment" and not (c.kind == "el" and c.tag == "style")]
        for c in n.children:
            prune(c)
    prune(root)
    computed = []
    for el in root.elements():          # match everything first: dropping classes early would break descendants
        matched = sorted((r for r in rules if _matches(el, r.parts)), key=lambda r: (r.spec, r.order))
        acc: list = []
        for r in matched:
            _apply(acc, r.decls)
        frame = el.get("data-fit")
        if frame:
            _fit(el, frame, acc)
        if el.tag == "video" and el.get("width") and el.get("height"):
            _apply(acc, [("aspect-ratio", f"{el.get('width')}/{el.get('height')}", False)])
        if el.get("style"):
            _apply(acc, parse_decls(el.get("style")))
        computed.append((el, acc))
    # The host's `.quarantine p { line-height: 1.6 !important }` beats any plain line-height on a <p>, the inherited
    # one too, so every <p> whose line-height (own or inherited) isn't 1.6 states it with !important.
    accs = {id(el): acc for el, acc in computed}
    for el, acc in computed:
        if el.tag != "p":
            continue
        n, lh = el, None
        while n is not None and n.kind == "el" and lh is None:
            lh = next((v for p_, v, _ in accs.get(id(n), []) if p_ == "line-height"), None)
            n = n.parent
        if lh is not None and lh != "1.6":
            _apply(acc, [("line-height", lh, True)])
    # <video> has no alt and aria-label is stripped: its fallback text becomes its title (kept), its accessible name.
    for el, _ in computed:
        if el.tag == "video" and not el.get("title"):
            text = " ".join("".join(c.text for c in el.children if c.kind == "text").split())
            if text:
                el.set("title", text)
    for el, acc in computed:
        el.drop("class")
        el.drop("data-fit")
        if acc:
            el.set("style", decls_to_str(acc))
        else:
            el.drop("style")
    out = serialize(root)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


# ----------------------------------------------------------------------------------------------- validator
def _local_asset(url: str) -> Path | None:
    if not url.startswith(ASSETS):
        return None
    return DOCS / "assets" / url[len(ASSETS):]


def validate(fragment: str) -> list[str]:
    errors = []
    if re.search(r"<!--", fragment):
        errors.append("comment left in the output")
    root = parse_html(fragment)
    tops = [c for c in root.children if c.kind == "el"]
    if len(tops) != 1 or tops[0].tag != "div":
        errors.append("the fragment must be exactly one root <div>")
    for el in root.elements():
        where = f"<{el.tag}>"
        if el.tag not in KEPT_TAGS:
            errors.append(f"{where}: tag is stripped by Superhive")
        allowed = GLOBAL_ATTRS | TAG_ATTRS.get(el.tag, set())
        for k, v in el.attrs:
            if k in ("class", "id"):
                errors.append(f"{where}: {k} attribute left over ({v})")
            elif k not in allowed:
                errors.append(f"{where}: attribute {k} is stripped")
        if el.get("style") is not None:
            try:
                for p, v, _ in parse_decls(el.get("style")):
                    why = css_problem(p, v)
                    if why:
                        errors.append(f"{where} style {p}:{v[:60]} -> {why}")
            except ValueError as e:
                errors.append(f"{where}: {e}")
        href = el.get("href")
        if el.tag == "a" and href is not None and not re.match(r"https?://", href):
            errors.append(f"{where}: href {href!r} is not an absolute URL (no anchors)")
        for attr in ("src", "poster"):
            url = el.get(attr)
            if url is None or el.tag == "iframe":
                continue
            local = _local_asset(url)
            if local is None:
                errors.append(f"{where}: {attr} {url!r} is not under {ASSETS}")
            elif not local.is_file():
                errors.append(f"{where}: {attr} {url!r} has no file at {local.relative_to(DOCS)}")
        if el.tag == "img":
            for a in ("width", "height", "alt"):
                if el.get(a) is None:
                    errors.append(f"<img src={el.get('src')}>: missing {a}")
        if el.tag == "video":
            for a in ("autoplay", "muted", "loop", "playsinline", "poster", "width", "height", "title"):
                if not any(k == a for k, _ in el.attrs):
                    errors.append(f"<video>: missing {a}")
            if not any(c.kind == "el" and c.tag == "source" and (c.get("type") == "video/mp4") for c in el.children):
                errors.append("<video>: needs a <source type=\"video/mp4\">")
    for m in re.finditer(r"[{}]", "".join(n.text for n in _texts(root))):
        errors.append("a { or } in visible text (CSS leaking?)")
        break
    return errors


def _texts(root):
    stack = [root]
    while stack:
        n = stack.pop()
        if n.kind == "text":
            yield n
        stack.extend(n.children)


# ----------------------------------------------------------------------------------------------- sanitizer simulation
def sanitize(fragment: str) -> str:
    """What Superhive keeps: stripped tags are unwrapped (their text stays, <style> CSS included), stripped
    attributes and CSS declarations removed."""
    root = parse_html(fragment)

    def walk(n):
        new = []
        for c in n.children:
            if c.kind == "comment":
                continue
            if c.kind == "el":
                walk(c)
                if c.tag not in KEPT_TAGS:
                    for g in c.children:
                        g.parent = n
                    new.extend(c.children)
                    continue
                allowed = GLOBAL_ATTRS | TAG_ATTRS.get(c.tag, set())
                c.attrs = [(k, v) for k, v in c.attrs if k in allowed]
                st = c.get("style")
                if st is not None:
                    try:
                        kept = [d for d in parse_decls(st) if css_problem(d[0], d[1]) is None]
                    except ValueError:
                        kept = []
                    if kept:
                        c.set("style", decls_to_str(kept))
                    else:
                        c.drop("style")
            new.append(c)
        n.children = new

    walk(root)
    return serialize(root)


# ----------------------------------------------------------------------------------------------- main
def build(name: str) -> int:
    src = STORE / f"{name}.src.html"
    dst = STORE / f"{name}.html"
    out = inline(src.read_text(encoding="utf-8"))
    errors = validate(out)
    if errors:
        print(f"{dst.name}: {len(errors)} problem(s), not written:")
        for e in errors[:80]:
            print("  -", e)
        return 1
    dst.write_text(out, encoding="utf-8", newline="\n")
    print(f"{dst.relative_to(DOCS.parent)}: {len(out.encode('utf-8')):,} bytes, valid")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="page and/or docs (default: every *.src.html)")
    ap.add_argument("--check", metavar="FILE", help="validate a built fragment")
    ap.add_argument("--sanitize", metavar="FILE", help="print what Superhive would keep of FILE")
    args = ap.parse_args(argv)
    if args.sanitize:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(sanitize(Path(args.sanitize).read_text(encoding="utf-8")))
        return 0
    if args.check:
        errors = validate(Path(args.check).read_text(encoding="utf-8"))
        for e in errors:
            print("  -", e)
        print(f"{args.check}: {'valid' if not errors else f'{len(errors)} problem(s)'}")
        return 1 if errors else 0
    names = args.names or sorted(p.name[: -len(".src.html")] for p in STORE.glob("*.src.html"))
    if not names:
        print("no *.src.html in", STORE)
        return 1
    return max(build(n) for n in names)


if __name__ == "__main__":
    sys.exit(main())
