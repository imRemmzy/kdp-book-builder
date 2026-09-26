"""Shared helpers for the kdp-book-builder scripts: book config, fonts, KDP math, Markdown parsing."""
import json
import os
import re
import sys
import uuid
from html.parser import HTMLParser
from pathlib import Path

import markdown

# Windows consoles often use a legacy code page; never crash on printing a title with unusual characters.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"

# KDP figures (September 2026). See references/kdp_specs.md; override via CLI flags if KDP changes them.
TRIM_SIZES = {
    "5x8": (5.0, 8.0), "5.06x7.81": (5.06, 7.81), "5.25x8": (5.25, 8.0), "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0), "6.14x9.21": (6.14, 9.21), "6.69x9.61": (6.69, 9.61), "7x10": (7.0, 10.0),
    "7.44x9.69": (7.44, 9.69), "7.5x9.25": (7.5, 9.25), "8x10": (8.0, 10.0), "8.25x6": (8.25, 6.0),
    "8.25x8.25": (8.25, 8.25), "8.5x8.5": (8.5, 8.5), "8.5x11": (8.5, 11.0),
}
SPINE_PER_PAGE = {"white": 0.002252, "cream": 0.0025, "standard-color": 0.002252, "premium-color": 0.002347}
GUTTER_TABLE = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]
BLEED = 0.125
MIN_PAGES = 24
MAX_PAGES = 828
SPINE_TEXT_MIN_PAGES = 80  # KDP: spine text only for books over 79 pages

FONT_FILES = {
    "serif": {"regular": "STIXGeneral.ttf", "bold": "STIXGeneralBol.ttf",
              "italic": "STIXGeneralItalic.ttf", "bolditalic": "STIXGeneralBolIta.ttf"},
    "sans": {"regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf",
             "italic": "DejaVuSans-Oblique.ttf", "bolditalic": "DejaVuSans-BoldOblique.ttf"},
}
FONT_CREDITS = "STIX (SIL Open Font License 1.1) and DejaVu Sans (Bitstream Vera License)"


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def trim_size(name):
    if name in TRIM_SIZES:
        return TRIM_SIZES[name]
    m = re.fullmatch(r"\s*([\d.]+)\s*[xX×]\s*([\d.]+)\s*", str(name))
    if not m:
        die(f"Unknown trim size '{name}'. Use one of {', '.join(TRIM_SIZES)} or WxH in inches.")
    return float(m.group(1)), float(m.group(2))


def is_large_trim(w, h):
    return w > 6.12 or h > 9.0


def gutter_for(pages):
    for limit, g in GUTTER_TABLE:
        if pages <= limit:
            return g
    return GUTTER_TABLE[-1][1]


def spine_width(pages, paper):
    if paper not in SPINE_PER_PAGE:
        die(f"Unknown paper '{paper}'. Use one of {', '.join(SPINE_PER_PAGE)}.")
    return pages * SPINE_PER_PAGE[paper]


def cover_dimensions(trim_w, trim_h, pages, paper):
    spine = spine_width(pages, paper)
    return {
        "trim_w": trim_w, "trim_h": trim_h, "pages": pages, "paper": paper, "bleed": BLEED,
        "spine": round(spine, 4),
        "width": round(BLEED + trim_w + spine + trim_w + BLEED, 4),
        "height": round(BLEED + trim_h + BLEED, 4),
        "spine_text_allowed": pages >= SPINE_TEXT_MIN_PAGES,
    }


def font_path(family, style="regular", overrides=None):
    """Resolve a TTF path: book.json overrides first, then the skill's bundled fonts."""
    if overrides and family in overrides and style in overrides[family]:
        p = Path(overrides[family][style])
        if p.exists():
            return str(p)
        die(f"Font override not found: {p}")
    p = FONT_DIR / FONT_FILES[family][style]
    if not p.exists():
        die(f"Bundled font missing: {p}")
    return str(p)


class Book:
    """book.json plus resolved paths. All paths in book.json are relative to its folder."""

    def __init__(self, path):
        self.path = Path(path).resolve()
        if self.path.is_dir():
            self.path = self.path / "book.json"
        if not self.path.exists():
            die(f"book.json not found at {self.path}")
        self.root = self.path.parent
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        for key in ("title", "author", "chapters"):
            if not self.data.get(key):
                die(f"book.json needs '{key}'")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def resolve(self, rel):
        return (self.root / rel).resolve()

    def sections(self):
        """Ordered list of dicts: role (front/chapter/back), file path, style."""
        out = []
        for role, key in (("front", "front_matter"), ("chapter", "chapters"), ("back", "back_matter")):
            for item in self.data.get(key, []):
                if isinstance(item, str):
                    item = {"file": item}
                p = self.resolve(item["file"])
                if not p.exists():
                    die(f"Manuscript file not found: {p}")
                style = item.get("style") or ("small" if "copyright" in p.stem.lower() else "normal")
                out.append({"role": role, "path": p, "style": style, "title": item.get("title")})
        return out

    @property
    def build_dir(self):
        d = self.resolve(self.data.get("build_dir", "build"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def identifier(self):
        if self.data.get("identifier"):
            return self.data["identifier"]
        return "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self.data['title']}|{self.data['author']}"))

    def trim(self):
        return trim_size(self.data.get("trim", "6x9"))

    def fonts(self):
        return self.data.get("fonts")


# ---------- Markdown -> simple node tree ----------

MD_EXTENSIONS = ["tables", "footnotes", "attr_list", "sane_lists", "smarty", "md_in_html"]
MD_CONFIG = {"footnotes": {"SEPARATOR": "-", "BACKLINK_TEXT": "↑"}}
VOID = {"img", "br", "hr", "meta", "link", "input", "col", "wbr", "source"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def find_all(self, tag):
        for c in self.children:
            if isinstance(c, Node):
                if c.tag == tag:
                    yield c
                yield from c.find_all(tag)

    def has_class(self, cls):
        return cls in self.attrs.get("class", "").split()

    def element_children(self):
        return [c for c in self.children if isinstance(c, Node)]


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.children.append(n)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)

    def handle_comment(self, data):
        pass


def md_to_tree(md_text):
    html = markdown.markdown(md_text, extensions=MD_EXTENSIONS, extension_configs=MD_CONFIG,
                             output_format="xhtml")
    b = _TreeBuilder()
    b.feed(html)
    b.close()
    return b.root


def load_section(section):
    """Parse a manuscript file. Returns (title, tree) where the first h1 is removed from the tree."""
    tree = md_to_tree(section["path"].read_text(encoding="utf-8"))
    title = section.get("title")
    for c in tree.children:
        if isinstance(c, Node) and c.tag == "h1":
            title = title or c.text().strip()
            tree.children.remove(c)
            break
    if not title:
        title = section["path"].stem.split("-", 1)[-1].replace("-", " ").replace("_", " ").title()
    return title, tree


def word_count(tree):
    text = tree.text() if isinstance(tree, Node) else str(tree)
    return len(re.findall(r"[A-Za-z0-9À-ɏ]+(?:['’][A-Za-z]+)?", text))


def resolve_image(src, section_path, book_root):
    """Find an image referenced from a manuscript file: relative to the file, then to the book root."""
    if re.match(r"^[a-z]+://", src):
        die(f"Remote images aren't supported (download it into the book's images folder first): {src}")
    for base in (section_path.parent, book_root):
        p = (base / src).resolve()
        if p.exists():
            return p
    die(f"Image not found: {src} (referenced in {section_path.name})")


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def rel(p, base=None):
    try:
        return os.path.relpath(p, base or os.getcwd())
    except ValueError:
        return str(p)
