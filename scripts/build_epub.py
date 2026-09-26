#!/usr/bin/env python3
"""Build a reflowable EPUB 3 from a book folder (book.json + Markdown manuscript).

Usage:
    python build_epub.py path/to/book.json [--out build/book.epub] [--cover build/cover_ebook.jpg]

Front matter, chapters and back matter come from book.json. Footnotes ([^1]) become per-chapter notes
with back-links. The cover image is embedded as the EPUB cover (KDP also wants it uploaded separately).
After building, the file is structurally checked; if epubcheck is installed (on PATH, or EPUBCHECK_JAR
set with Java available), it is run too.
"""
import argparse
import datetime as dt
import html
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image as PILImage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import VOID, Book, Node, die, load_section, resolve_image, word_count  # noqa: E402

MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
               ".svg": "image/svg+xml", ".webp": "image/webp"}

CSS = """
body { margin: 0 3%; font-family: serif; line-height: 1.45; }
p { margin: 0 0 0.8em 0; text-indent: 0; text-align: left; }
h1 { font-family: sans-serif; font-size: 1.6em; line-height: 1.2; text-align: center; margin: 2em 0 0.4em 0; page-break-before: always; }
h1 + .ornament { margin-bottom: 1.6em; }
h2 { font-family: sans-serif; font-size: 1.25em; line-height: 1.25; margin: 1.6em 0 0.5em 0; page-break-after: avoid; }
h3 { font-family: sans-serif; font-size: 1.05em; margin: 1.3em 0 0.4em 0; page-break-after: avoid; }
.ornament { text-align: center; font-size: 0.9em; letter-spacing: 0.4em; color: #555; margin: 0 0 1.2em 0; }
blockquote { margin: 1em 0; padding: 0.6em 0.9em; border-left: 3px solid #888; background-color: #f3f3f3; }
blockquote p:last-child { margin-bottom: 0; }
ul, ol { margin: 0 0 0.9em 0; padding-left: 1.6em; }
li { margin-bottom: 0.3em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.9em; }
th, td { border: 1px solid #888; padding: 0.3em 0.45em; text-align: left; vertical-align: top; }
th { background-color: #e8e8e8; }
code { font-family: monospace; font-size: 0.95em; }
pre { font-family: monospace; font-size: 0.85em; white-space: pre-wrap; }
hr { border: 0; text-align: center; margin: 1.5em 0; }
hr:after { content: "\\2767"; }
.figure { text-align: center; margin: 1em 0; page-break-inside: avoid; }
.figure img { max-width: 100%; height: auto; }
img { max-width: 100%; height: auto; }
.page-break { page-break-after: always; height: 0; }
.footnotes { font-size: 0.85em; margin-top: 2em; border-top: 1px solid #999; padding-top: 0.5em; }
.footnotes h2 { font-size: 1.1em; margin-top: 0.4em; }
.footnotes li { margin-bottom: 0.5em; }
sup { line-height: 0; }
.small p { font-size: 0.85em; margin-bottom: 0.6em; }
.titlepage { text-align: center; margin-top: 20%; }
.titlepage .t { font-family: sans-serif; font-size: 2em; font-weight: bold; line-height: 1.2; margin-bottom: 0.5em; }
.titlepage .st { font-style: italic; font-size: 1.15em; margin-bottom: 3em; }
.titlepage .a { font-family: sans-serif; font-size: 1.1em; letter-spacing: 0.1em; }
.fullpage { text-align: center; margin: 0; padding: 0; }
.fullpage img { max-width: 100%; max-height: 100%; }
nav ol { list-style-type: none; padding-left: 0; }
nav ol ol { padding-left: 1.4em; }
nav li { margin-bottom: 0.4em; }
nav a { text-decoration: none; }
"""


def esc(s):
    return html.escape(s, quote=False)


def esc_attr(s):
    return html.escape(s, quote=True)


class ChapterWriter:
    """Serialise a parsed Markdown tree as well-formed XHTML, collecting images and heading ids."""

    def __init__(self, section_path, book_root, images):
        self.section_path = section_path
        self.book_root = book_root
        self.images = images  # source path -> epub name
        self.headings = []  # (level, id, text)
        self.counter = 0

    def image_name(self, src):
        p = resolve_image(src, self.section_path, self.book_root)
        if p not in self.images:
            stem = re.sub(r"[^A-Za-z0-9_-]", "-", p.stem)
            name = f"{stem}{p.suffix.lower()}"
            taken = set(self.images.values())
            i = 2
            while name in taken:
                name = f"{stem}-{i}{p.suffix.lower()}"
                i += 1
            self.images[p] = name
        return self.images[p]

    def render(self, node):
        if isinstance(node, str):
            return esc(node)
        if node.tag == "root":
            return "".join(self.render(c) for c in node.children)
        tag, attrs = node.tag, dict(node.attrs)

        if tag == "p":
            kids = [c for c in node.children if not (isinstance(c, str) and not c.strip())]
            if len(kids) == 1 and isinstance(kids[0], Node) and kids[0].tag == "img":
                return f'<div class="figure">{self.render(kids[0])}</div>\n'
        if tag == "img":
            src = attrs.get("src", "")
            attrs["src"] = "../images/" + self.image_name(src)
            attrs.setdefault("alt", "")
            width = attrs.pop("width", None)
            if width:
                attrs["style"] = f"width: {width if width.endswith('%') else width + 'px'};"
            attrs.pop("height", None)
        if tag in ("h2", "h3", "h4"):
            self.counter += 1
            attrs.setdefault("id", f"s{self.counter}")
            self.headings.append((int(tag[1]), attrs["id"], node.text().strip()))
        if tag == "a" and "footnote-ref" in attrs.get("class", ""):
            attrs["epub:type"] = "noteref"
            attrs["role"] = "doc-noteref"
        if tag == "a" and "footnote-backref" in attrs.get("class", ""):
            attrs["role"] = "doc-backlink"
            attrs.pop("title", None)
        if tag == "div" and node.has_class("footnote"):
            items = [c for c in node.element_children() if c.tag == "ol"]
            body = "".join(self.render(c) for c in items)
            return ('<section class="footnotes" epub:type="endnotes" role="doc-endnotes">'
                    f'<h2 id="notes">Notes</h2>{body}</section>\n')
        if tag == "li" and attrs.get("id", "").startswith("fn-"):
            attrs["epub:type"] = "endnote"
            attrs["role"] = "doc-endnote"
        if tag == "hr":
            return '<p class="ornament">• • •</p>\n'

        attr_s = "".join(f' {k}="{esc_attr(v)}"' for k, v in attrs.items())
        if tag in VOID:
            return f"<{tag}{attr_s}/>"
        inner = "".join(self.render(c) for c in node.children)
        nl = "\n" if tag in ("p", "ul", "ol", "li", "table", "tr", "thead", "tbody", "blockquote", "div", "h2", "h3",
                             "h4", "pre") else ""
        return f"<{tag}{attr_s}>{inner}</{tag}>{nl}"


def xhtml(title, body, lang, body_type=""):
    et = f' epub:type="{body_type}"' if body_type else ""
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{lang}" xml:lang="{lang}">\n<head>\n<meta charset="utf-8"/>\n<title>{esc(title)}</title>\n'
            f'<link rel="stylesheet" type="text/css" href="../css/book.css"/>\n</head>\n<body{et}>\n{body}\n</body>\n</html>\n')


def build(book, out_path, cover_path, title_page_image, max_px=1600):
    lang = book.get("language", "en")
    title = book.get("title")
    subtitle = book.get("subtitle", "")
    author = book.get("author")
    images = {}
    docs = []  # (id, filename, title, role, headings, xhtml)
    total_words = 0

    if title_page_image:
        tp_name = "titlepage" + Path(title_page_image).suffix.lower()
        images[Path(title_page_image).resolve()] = tp_name
        tp_body = f'<div class="fullpage"><img src="../images/{tp_name}" alt="{esc_attr(title)}"/></div>'
    else:
        tp_body = (f'<div class="titlepage"><p class="t">{esc(title)}</p>'
                   + (f'<p class="st">{esc(subtitle)}</p>' if subtitle else "")
                   + f'<p class="a">{esc(author)}</p></div>')
    docs.append(("titlepage", "titlepage.xhtml", "Title Page", "titlepage", [],
                 xhtml(title, tp_body, lang, "frontmatter")))

    counts = {"front": 0, "chapter": 0, "back": 0}
    for sec in book.sections():
        counts[sec["role"]] += 1
        prefix = {"front": "fm", "chapter": "ch", "back": "bm"}[sec["role"]]
        doc_id = f"{prefix}{counts[sec['role']]:02d}"
        sec_title, tree = load_section(sec)
        total_words += word_count(tree)
        w = ChapterWriter(sec["path"], book.root, images)
        inner = w.render(tree)
        cls = ' class="small"' if sec["style"] == "small" else ""
        show_h1 = sec["style"] != "small"
        head = (f'<h1 id="top">{esc(sec_title)}</h1>\n<p class="ornament">❧</p>\n' if show_h1
                else f'<h1 id="top" style="display:none">{esc(sec_title)}</h1>\n')
        etype = {"front": "frontmatter", "chapter": "bodymatter", "back": "backmatter"}[sec["role"]]
        body = f'<section epub:type="{"chapter" if sec["role"] == "chapter" else etype}"{cls}>\n{head}{inner}</section>'
        docs.append((doc_id, f"{doc_id}.xhtml", sec_title, sec["role"], w.headings, xhtml(sec_title, body, lang, etype)))

    # Navigation document (also the visible table of contents, placed after the front matter).
    first_chapter = next((d for d in docs if d[3] == "chapter"), docs[-1])
    toc_items = []
    for d in docs:
        if d[3] == "titlepage":
            continue
        subs = [h for h in d[4] if h[0] == 2]
        sub_html = ("<ol>" + "".join(f'<li><a href="{d[1]}#{hid}">{esc(ht)}</a></li>' for _, hid, ht in subs)
                    + "</ol>") if subs and d[3] == "chapter" else ""
        toc_items.append(f'<li><a href="{d[1]}">{esc(d[2])}</a>{sub_html}</li>')
    nav_body = (f'<nav epub:type="toc" id="toc" role="doc-toc"><h1>Contents</h1>\n<ol>\n' + "\n".join(toc_items)
                + "\n</ol></nav>\n"
                f'<nav epub:type="landmarks" id="landmarks" hidden="hidden"><h2>Landmarks</h2><ol>'
                f'<li><a epub:type="toc" href="nav.xhtml">Contents</a></li>'
                f'<li><a epub:type="bodymatter" href="{first_chapter[1]}">Start Reading</a></li></ol></nav>')
    nav_doc = xhtml("Contents", nav_body, lang).replace('href="../css/book.css"', 'href="../css/book.css"')

    # Spine order: title page, front matter, contents, chapters, back matter.
    ordered = [d for d in docs if d[3] in ("titlepage", "front")]
    rest = [d for d in docs if d[3] not in ("titlepage", "front")]

    modified = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = ['<item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="css/book.css" media-type="text/css"/>']
    for d in docs:
        manifest.append(f'<item id="{d[0]}" href="text/{d[1]}" media-type="application/xhtml+xml"/>')
    cover_name = None
    if cover_path:
        cover_name = "cover" + Path(cover_path).suffix.lower()
        manifest.append(f'<item id="cover-image" href="images/{cover_name}" '
                        f'media-type="{MEDIA_TYPES[Path(cover_path).suffix.lower()]}" properties="cover-image"/>')
    for i, (src, name) in enumerate(images.items(), 1):
        ext = Path(name).suffix.lower()
        if ext not in MEDIA_TYPES:
            die(f"Unsupported image type {ext} for {src}")
        manifest.append(f'<item id="img{i:03d}" href="images/{name}" media-type="{MEDIA_TYPES[ext]}"/>')
    spine = [f'<itemref idref="{d[0]}"/>' for d in ordered] + ['<itemref idref="nav"/>'] + \
            [f'<itemref idref="{d[0]}"/>' for d in rest]

    desc = book.get("description_plain", "")
    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="{lang}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="pub-id">{esc(book.identifier)}</dc:identifier>
<dc:title>{esc(title)}</dc:title>
<dc:creator id="creator">{esc(author)}</dc:creator>
<dc:language>{lang}</dc:language>
{f"<dc:description>{esc(desc)}</dc:description>" if desc else ""}
{f"<dc:publisher>{esc(book.get('publisher'))}</dc:publisher>" if book.get('publisher') else ""}
<dc:date>{book.get("year", dt.date.today().year)}</dc:date>
<meta property="dcterms:modified">{modified}</meta>
{'<meta name="cover" content="cover-image"/>' if cover_name else ""}
</metadata>
<manifest>
{chr(10).join(manifest)}
</manifest>
<spine toc="ncx">
{chr(10).join(spine)}
</spine>
<guide>
<reference type="toc" title="Contents" href="text/nav.xhtml"/>
<reference type="text" title="Start Reading" href="text/{first_chapter[1]}"/>
</guide>
</package>
'''
    nav_points = []
    for i, d in enumerate([d for d in docs if d[3] != "titlepage"], 1):
        nav_points.append(f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{esc(d[2])}</text></navLabel>'
                          f'<content src="text/{d[1]}"/></navPoint>')
    ncx = f'''<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="{lang}">
<head><meta name="dtb:uid" content="{esc_attr(book.identifier)}"/><meta name="dtb:depth" content="1"/>
<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>
<docTitle><text>{esc(title)}</text></docTitle>
<navMap>
{chr(10).join(nav_points)}
</navMap>
</ncx>
'''
    container = ('<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n<rootfiles>\n'
                 '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
                 '</rootfiles>\n</container>\n')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/css/book.css", CSS.strip() + "\n", compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/text/nav.xhtml", nav_doc, compress_type=zipfile.ZIP_DEFLATED)
        for d in docs:
            z.writestr(f"OEBPS/text/{d[1]}", d[5], compress_type=zipfile.ZIP_DEFLATED)
        if cover_name:
            z.write(cover_path, f"OEBPS/images/{cover_name}", compress_type=zipfile.ZIP_DEFLATED)
        for src, name in images.items():
            data = src.read_bytes() if name.startswith("titlepage") else ebook_image(src, max_px)
            z.writestr(f"OEBPS/images/{name}", data, compress_type=zipfile.ZIP_DEFLATED)
    return total_words, len([d for d in docs if d[3] == "chapter"])


def ebook_image(src, max_px):
    """Print-resolution art is far bigger than any e-reader needs, and on the 70% royalty KDP charges
    delivery per MB, so downscale to max_px on the long edge and re-compress."""
    with PILImage.open(src) as im:
        im.load()
        fmt = "JPEG" if src.suffix.lower() in (".jpg", ".jpeg") else "PNG"
        if max(im.size) > max_px:
            k = max_px / max(im.size)
            im = im.resize((round(im.width * k), round(im.height * k)), PILImage.LANCZOS)
        buf = io.BytesIO()
        if fmt == "JPEG":
            im.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
        else:
            if im.mode in ("L", "LA") or (im.mode == "RGB" and _is_gray(im)):
                im = im.convert("L").quantize(16)  # line art: 16 greys look identical and compress far better
            im.save(buf, "PNG", optimize=True)
        return buf.getvalue()


def _is_gray(im):
    small = im.resize((64, 64))
    return all(abs(r - g) < 6 and abs(g - b) < 6 for r, g, b in small.getdata())


def check_epub(path):
    """Structural checks that catch the usual reasons KDP or epubcheck reject a file."""
    problems = []
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        if infos[0].filename != "mimetype" or infos[0].compress_type != zipfile.ZIP_STORED:
            problems.append("mimetype must be the first entry and stored uncompressed")
        if z.read("mimetype") != b"application/epub+zip":
            problems.append("mimetype content is wrong")
        names = set(z.namelist())
        ns = {"opf": "http://www.idpf.org/2007/opf"}
        opf = ET.fromstring(z.read("OEBPS/content.opf"))
        items = {i.get("id"): i for i in opf.find("opf:manifest", ns)}
        hrefs = {"OEBPS/" + i.get("href") for i in items.values()}
        for h in hrefs:
            if h not in names:
                problems.append(f"manifest lists missing file {h}")
        for n in names:
            if n.startswith("OEBPS/") and n not in hrefs and n != "OEBPS/content.opf":
                problems.append(f"file not in manifest: {n}")
        for ir in opf.find("opf:spine", ns):
            if ir.get("idref") not in items:
                problems.append(f"spine references unknown id {ir.get('idref')}")
        if not any("nav" in (i.get("properties") or "") for i in items.values()):
            problems.append("no navigation document")
        if not opf.find(".//{http://purl.org/dc/elements/1.1/}identifier").text:
            problems.append("empty identifier")
        ids_by_file = {}
        docs = {}
        for n in names:
            if n.endswith(".xhtml"):
                try:
                    docs[n] = ET.fromstring(z.read(n))
                except ET.ParseError as e:
                    problems.append(f"{n} is not well-formed XML: {e}")
                    continue
                ids_by_file[n] = {el.get("id") for el in docs[n].iter() if el.get("id")}
        for n, root in docs.items():
            base = os.path.dirname(n)
            for el in root.iter():
                for attr in ("href", "src"):
                    v = el.get(attr)
                    if not v or re.match(r"^[a-z]+:", v):
                        continue
                    f, _, frag = v.partition("#")
                    target = os.path.normpath(os.path.join(base, f)).replace("\\", "/") if f else n
                    if target not in names:
                        problems.append(f"{n}: broken link {v}")
                    elif frag and target in ids_by_file and frag not in ids_by_file[target]:
                        problems.append(f"{n}: link to missing anchor {v}")
                if el.tag.endswith("}img") and el.get("alt") is None:
                    problems.append(f"{n}: image without alt text")
    return problems


def run_epubcheck(path):
    exe = shutil.which("epubcheck")
    jar = os.environ.get("EPUBCHECK_JAR")
    if exe:
        cmd = [exe, str(path)]
    elif jar and shutil.which("java"):
        cmd = ["java", "-jar", jar, str(path)]
    else:
        return None, "epubcheck not installed (optional). Kindle Previewer or KDP's upload check will also validate."
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-3000:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="path to book.json (or its folder)")
    ap.add_argument("--out", help="output .epub (default: build/<slug>.epub)")
    ap.add_argument("--cover", help="eBook cover image (default: book.json cover.ebook_image or build/cover_ebook.jpg)")
    ap.add_argument("--title-page", help="title page image (default: build/title_page.png if present)")
    ap.add_argument("--no-cover", action="store_true", help="build without an embedded cover (drafts only)")
    ap.add_argument("--max-image-px", type=int, default=1600,
                    help="downscale interior images to this long edge (smaller file = lower KDP delivery cost)")
    args = ap.parse_args()

    book = Book(args.book)
    slug = re.sub(r"[^a-z0-9]+", "-", book.get("title").lower()).strip("-")[:60]
    out = Path(args.out) if args.out else book.build_dir / f"{slug}.epub"

    cover = None
    if not args.no_cover:
        cover = Path(args.cover) if args.cover else book.resolve(
            (book.get("cover") or {}).get("ebook_image", str(book.build_dir / "cover_ebook.jpg")))
        if not cover.exists():
            die(f"Cover image not found: {cover}. Run build_cover.py first, pass --cover, or use --no-cover for a draft.")
    tp = Path(args.title_page) if args.title_page else book.build_dir / "title_page.png"
    tp = tp if tp.exists() else None

    words, chapters = build(book, out, cover, tp, args.max_image_px)
    problems = check_epub(out)
    print(f"EPUB written: {out}")
    mb = out.stat().st_size / 1e6
    print(f"  chapters: {chapters}, words: {words:,}, size: {mb:.2f} MB"
          f"{' (no cover embedded)' if not cover else ''}")
    print(f"  70% royalty delivery cost is roughly ${mb * 0.15:.2f} per US sale at $0.15/MB (KDP measures its"
          " converted file, so treat this as an estimate)")
    if problems:
        print("STRUCTURE CHECK: FAIL")
        for p in problems:
            print("  -", p)
    else:
        print("STRUCTURE CHECK: PASS")
    ok, msg = run_epubcheck(out)
    if ok is None:
        print("  " + msg)
    else:
        print(f"EPUBCHECK: {'PASS' if ok else 'FAIL'}")
        if not ok:
            print(msg)
    sys.exit(1 if problems or ok is False else 0)


if __name__ == "__main__":
    main()
