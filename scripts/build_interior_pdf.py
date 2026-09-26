#!/usr/bin/env python3
"""Build a print-ready KDP paperback interior PDF from a book folder (book.json + Markdown manuscript).

Usage:
    python build_interior_pdf.py path/to/book.json [--out build/interior.pdf] [--trim 6x9] [--bleed]

What it does:
  * trim size page, mirrored margins, gutter chosen from KDP's page-count table (re-laid out until the
    gutter matches the final page count)
  * title page, copyright page, contents with page numbers, chapters starting on right-hand (odd) pages,
    running heads (book title on left pages, chapter title on right pages), page numbers
  * footnotes ([^1]) collected into numbered endnotes grouped by chapter at the back
  * embeds all fonts (bundled OFL/Bitstream fonts unless book.json overrides), warns on images < 300 DPI
  * pads to an even page count; writes build/interior_report.json for check_package.py and build_cover.py
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.fonts import addMapping
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, ListFlowable, ListItem,
                                PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BLEED, FONT_CREDITS, MIN_PAGES, Book, Node, die, font_path, gutter_for,  # noqa: E402
                    load_section, resolve_image, trim_size, word_count, write_json)

try:
    import pyphen  # noqa: F401
    HYPHEN = "en_US"
except ImportError:
    HYPHEN = None

MIN_OUTSIDE = 0.25
# Table sets its default font (Helvetica, never embedded) before drawing each cell; override it.
EMBED = [("FONTNAME", (0, 0), (-1, -1), "BookSerif")]


def register_fonts(overrides):
    for fam, name in (("serif", "BookSerif"), ("sans", "BookSans")):
        for style, suffix in (("regular", ""), ("bold", "-Bold"), ("italic", "-Italic"), ("bolditalic", "-BoldItalic")):
            pdfmetrics.registerFont(TTFont(name + suffix, font_path(fam, style, overrides)))
        addMapping(name, 0, 0, name)
        addMapping(name, 1, 0, name + "-Bold")
        addMapping(name, 0, 1, name + "-Italic")
        addMapping(name, 1, 1, name + "-BoldItalic")


def make_styles(trim_w):
    base = 10.5 if trim_w <= 5.25 else 11 if trim_w <= 6.5 else 12
    lead = base * 1.38
    hy = {"hyphenationLang": HYPHEN, "embeddedHyphenation": 1, "uriWasteReduce": 0.3} if HYPHEN else {}
    s = {}
    s["body"] = ParagraphStyle("body", fontName="BookSerif", fontSize=base, leading=lead, alignment=TA_JUSTIFY,
                               spaceAfter=lead * 0.55, allowWidows=0, allowOrphans=0, **hy)
    s["small"] = ParagraphStyle("small", parent=s["body"], fontSize=base * 0.8, leading=base * 1.1,
                                alignment=TA_LEFT, spaceAfter=base * 0.6)
    s["chapter"] = ParagraphStyle("chapter", fontName="BookSans-Bold", fontSize=base * 2.0, leading=base * 2.4,
                                  alignment=TA_CENTER, spaceAfter=base * 0.6)
    s["h2"] = ParagraphStyle("h2", fontName="BookSans-Bold", fontSize=base * 1.25, leading=base * 1.55,
                             spaceBefore=lead * 0.9, spaceAfter=lead * 0.35, keepWithNext=1)
    s["h3"] = ParagraphStyle("h3", fontName="BookSans-Bold", fontSize=base * 1.05, leading=base * 1.35,
                             spaceBefore=lead * 0.6, spaceAfter=lead * 0.25, keepWithNext=1)
    s["list"] = ParagraphStyle("list", parent=s["body"], alignment=TA_LEFT, spaceAfter=lead * 0.2)
    s["quote"] = ParagraphStyle("quote", parent=s["body"], alignment=TA_LEFT, fontSize=base * 0.95,
                                leading=lead * 0.95, spaceAfter=lead * 0.3)
    s["cell"] = ParagraphStyle("cell", fontName="BookSerif", fontSize=base * 0.85, leading=base * 1.1,
                               alignment=TA_LEFT)
    s["cellhead"] = ParagraphStyle("cellhead", parent=s["cell"], fontName="BookSans-Bold")
    s["pre"] = ParagraphStyle("pre", fontName="BookSans", fontSize=base * 0.8, leading=base * 1.05,
                              spaceAfter=lead * 0.5)
    s["toc"] = ParagraphStyle("toc", parent=s["body"], alignment=TA_LEFT, spaceAfter=0)
    s["tocnum"] = ParagraphStyle("tocnum", parent=s["toc"], alignment=TA_RIGHT)
    s["note"] = ParagraphStyle("note", parent=s["body"], fontSize=base * 0.85, leading=base * 1.15,
                               alignment=TA_LEFT, spaceAfter=base * 0.35)
    s["notehead"] = ParagraphStyle("notehead", parent=s["h3"], spaceBefore=lead * 0.8)
    s["base"] = base
    return s


def spaced(f, before, after):
    """Spacing on the flowable itself (not separate Spacers) so a heading's keepWithNext binds to it."""
    f.spaceBefore, f.spaceAfter = before, after
    return f


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- state markers (zero-size flowables that tell the page decorator what's on the page) ----------

class Marker(Flowable):
    def __init__(self, doc, **state):
        super().__init__()
        self.doc_ref = doc
        self.state = state

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        d = self.doc_ref
        d.page_state.update({k: v for k, v in self.state.items() if k != "record"})
        if "record" in self.state:
            d.starts[self.state["record"]] = d.page


class BlankPage(Flowable):
    """Occupies an otherwise empty page so it's emitted, and suppresses head/folio on it."""

    def __init__(self, doc):
        super().__init__()
        self.doc_ref = doc

    def wrap(self, aw, ah):
        return aw, 1

    def draw(self):
        self.doc_ref.page_state["blank"] = True


class Ornament(Flowable):
    def __init__(self, width=1.4 * inch, gap=6):
        super().__init__()
        self.w, self.gap = width, gap

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 10 + self.gap

    def draw(self):
        c = self.canv
        cx, y = self.aw / 2, 5
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(cx - self.w / 2, y, cx - 7, y)
        c.line(cx + 7, y, cx + self.w / 2, y)
        p = c.beginPath()
        p.moveTo(cx, y + 3.5); p.lineTo(cx + 3.5, y); p.lineTo(cx, y - 3.5); p.lineTo(cx - 3.5, y); p.close()
        c.setFillColor(colors.black)
        c.drawPath(p, fill=1, stroke=0)


class TitlePage(Flowable):
    def __init__(self, title, subtitle, author, styles):
        super().__init__()
        self.title, self.subtitle, self.author, self.s = title, subtitle, author, styles

    def wrap(self, aw, ah):
        self.aw, self.ah = aw, ah
        return aw, ah - 1

    def draw(self):
        c, b = self.canv, self.s["base"]
        y = self.ah * 0.78
        tstyle = ParagraphStyle("tp", fontName="BookSans-Bold", fontSize=b * 2.6, leading=b * 3.0, alignment=TA_CENTER)
        p = Paragraph(esc(self.title), tstyle)
        _, h = p.wrap(self.aw, self.ah)
        p.drawOn(c, 0, y - h)
        y -= h + b * 1.2
        o = Ornament(1.8 * inch)
        o.wrap(self.aw, 20)
        o.drawOn(c, 0, y - 10)
        y -= 10 + b * 1.4
        if self.subtitle:
            sstyle = ParagraphStyle("tps", fontName="BookSerif-Italic", fontSize=b * 1.3, leading=b * 1.7,
                                    alignment=TA_CENTER)
            p = Paragraph(esc(self.subtitle), sstyle)
            _, h = p.wrap(self.aw * 0.85, self.ah)
            p.drawOn(c, self.aw * 0.075, y - h)
        astyle = ParagraphStyle("tpa", fontName="BookSans", fontSize=b * 1.2, leading=b * 1.5, alignment=TA_CENTER)
        p = Paragraph(esc(self.author.upper()), astyle)
        _, h = p.wrap(self.aw, self.ah)
        p.drawOn(c, 0, self.ah * 0.08)


# ---------- Markdown tree -> flowables ----------

class Converter:
    def __init__(self, s, frame_w, frame_h, book_root, notes, warnings):
        self.s, self.fw, self.fh = s, frame_w, frame_h
        self.book_root = book_root
        self.notes = notes  # list of (chapter title, [note markup])
        self.warnings = warnings
        self.section_path = None

    def inline(self, node):
        if isinstance(node, str):
            return esc(node)
        t = node.tag
        inner = "".join(self.inline(c) for c in node.children)
        if t in ("strong", "b"):
            return f"<b>{inner}</b>"
        if t in ("em", "i"):
            return f"<i>{inner}</i>"
        if t == "code":
            return f'<font face="BookSans">{inner}</font>'
        if t in ("del", "s"):
            return f"<strike>{inner}</strike>"
        if t == "br":
            return "<br/>"
        if t == "sup":
            if node.attrs.get("id", "").startswith("fnref"):
                return f"<super>{esc(node.text())}</super>"
            return f"<super>{inner}</super>"
        if t == "sub":
            return f"<sub>{inner}</sub>"
        if t == "a":
            if "footnote-backref" in node.attrs.get("class", ""):
                return ""
            return inner
        if t == "img":
            return ""
        return inner

    def image(self, node, max_h=None):
        p = resolve_image(node.attrs.get("src", ""), self.section_path, self.book_root)
        with PILImage.open(p) as im:
            px_w, px_h = im.size
        width = self.fw
        pct = node.attrs.get("width", "")
        if pct.endswith("%"):
            width = self.fw * float(pct[:-1]) / 100
        height = width * px_h / px_w
        max_h = max_h or self.fh * 0.9
        if height > max_h:
            height = max_h
            width = height * px_w / px_h
        dpi = px_w / (width / 72)
        if dpi < 299.5:
            self.warnings.append(f"{p.name}: {dpi:.0f} DPI at printed size (KDP wants 300+)")
        img = Image(str(p), width=width, height=height)
        img.hAlign = "CENTER"
        return [spaced(img, 4, 8)]

    BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote", "table", "hr", "pre",
                  "div", "section", "figure"}

    def blocks(self, node, style=None):
        """Block children become flowables; runs of loose text and inline tags become one paragraph."""
        out, run = [], []
        style = style or self.s["body"]

        def flush():
            text = "".join(self.inline(c) for c in run).strip()
            if text:
                out.append(Paragraph(text, style))
            run.clear()

        for c in node.children:
            if isinstance(c, Node) and (c.tag in self.BLOCK_TAGS or c.tag == "img"):
                flush()
                out.extend(self.block(c, style))
            else:
                run.append(c)
        flush()
        return out

    def block(self, n, style):
        t, s = n.tag, self.s
        if t == "p":
            kids = [c for c in n.children if not (isinstance(c, str) and not c.strip())]
            if len(kids) == 1 and isinstance(kids[0], Node) and kids[0].tag == "img":
                return self.image(kids[0])
            text = "".join(self.inline(c) for c in n.children).strip()
            return [Paragraph(text, style)] if text else []
        if t == "h2":
            return [Paragraph(self.inline(n), s["h2"])]
        if t in ("h3", "h4", "h5", "h6"):
            return [Paragraph(self.inline(n), s["h3"])]
        if t in ("ul", "ol"):
            items = []
            for li in n.element_children():
                if li.tag != "li":
                    continue
                has_block = any(isinstance(c, Node) and c.tag in ("p", "ul", "ol") for c in li.children)
                if has_block:
                    fl = self.blocks(li, s["list"])
                else:
                    fl = [Paragraph("".join(self.inline(c) for c in li.children).strip(), s["list"])]
                items.append(ListItem(fl, leftIndent=16))
            kw = dict(bulletType="1", bulletFormat="%s.", bulletFontName="BookSerif") if t == "ol" else \
                dict(bulletType="bullet", start="•", bulletFontName="BookSerif")
            return [spaced(ListFlowable(items, leftIndent=16, bulletFontSize=s["base"], **kw), 0, s["base"] * 0.5)]
        if t == "blockquote":
            inner = self.blocks(n, s["quote"])
            text_len = len(n.text())
            if text_len > 900:
                return [Spacer(1, 4)] + [self._indent(f) for f in inner] + [Spacer(1, 6)]
            tbl = Table([[inner]], colWidths=[self.fw - 4])
            tbl.setStyle(TableStyle(EMBED + [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.94, 0.94, 0.94)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            return [spaced(tbl, 4, s["base"])]
        if t == "table":
            return self.table(n)
        if t == "hr":
            return [Spacer(1, 6), Ornament(), Spacer(1, 6)]
        if t == "pre":
            return [Preformatted(n.text().rstrip("\n"), s["pre"])]
        if t == "div" and n.has_class("page-break"):
            return [PageBreak()]
        if t == "div" and n.has_class("footnote"):
            for ol in n.find_all("ol"):
                for li in ol.element_children():
                    txt = " ".join(
                        "".join(self.inline(c) for c in (p.children if isinstance(p, Node) else [p])).strip()
                        for p in li.children if not (isinstance(p, str) and not p.strip()))
                    self.notes[-1][1].append(txt.strip())
                break
            return []
        if t in ("div", "section", "figure"):
            return self.blocks(n, style)
        if t == "img":
            return self.image(n)
        text = self.inline(n).strip()
        return [Paragraph(text, style)] if text else []

    def _indent(self, f):
        if isinstance(f, Paragraph):
            st = ParagraphStyle("qi", parent=f.style, leftIndent=18, rightIndent=12)
            return Paragraph(f.text, st)
        return f

    def table(self, n):
        rows = []
        head_rows = 0
        for sect in n.element_children():
            trs = [sect] if sect.tag == "tr" else [r for r in sect.element_children() if r.tag == "tr"]
            for tr in trs:
                cells = []
                for cell in tr.element_children():
                    st = self.s["cellhead"] if cell.tag == "th" else self.s["cell"]
                    cells.append(Paragraph("".join(self.inline(c) for c in cell.children).strip(), st))
                if sect.tag == "thead":
                    head_rows += 1
                rows.append(cells)
        if not rows:
            return []
        ncol = max(len(r) for r in rows)
        rows = [r + [Paragraph("", self.s["cell"])] * (ncol - len(r)) for r in rows]
        lens = [max(len(rows[i][j].text) for i in range(len(rows))) + 4 for j in range(ncol)]
        total = sum(lens)
        widths = [max(self.fw * 0.12, self.fw * L / total) for L in lens]
        k = self.fw / sum(widths)
        widths = [w * k for w in widths]
        tbl = Table(rows, colWidths=widths, repeatRows=head_rows)
        style = [("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
        if head_rows:
            style.append(("BACKGROUND", (0, 0), (-1, head_rows - 1), colors.Color(0.88, 0.88, 0.88)))
        tbl.setStyle(TableStyle(EMBED + style))
        return [spaced(tbl, 4, self.s["base"])]


# ---------- document ----------

class BookDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        self.page_state = {}
        self.starts = {}
        super().__init__(filename, **kw)


def layout(book, sections, out, trim, bleed, gutter, extra_gutter, margins, blanks, toc_numbers, pad_end):
    tw, th = trim
    pw = tw + (BLEED if bleed else 0)
    ph = th + (2 * BLEED if bleed else 0)
    s = make_styles(tw)
    inside = gutter + extra_gutter
    outside = margins["outside"] + (BLEED if bleed else 0)
    top = margins["top"] + (BLEED if bleed else 0)
    bottom = margins["bottom"] + (BLEED if bleed else 0)
    fw = (pw - inside - outside) * inch
    fh = (ph - top - bottom) * inch

    doc = BookDoc(str(out), pagesize=(pw * inch, ph * inch), title=book.get("title"), author=book.get("author"),
                  subject=book.get("subtitle", ""), creator="kdp-book-builder", initialFontName="BookSerif",
                  initialFontSize=11, leftMargin=0, rightMargin=0,
                  topMargin=0, bottomMargin=0)
    head_font = ("BookSans", s["base"] * 0.72)
    folio_font = ("BookSerif", s["base"] * 0.85)

    def on_begin(canvas, d):
        d.page_state = {"section": d.page_state.get("section", "front"), "chapter": d.page_state.get("chapter", ""),
                        "opener": False, "blank": False}

    def on_end(canvas, d):
        st = d.page_state
        if st.get("blank") or st.get("section") != "body":
            return
        recto = d.page % 2 == 1
        canvas.saveState()
        x_in = (inside if recto else outside) * inch
        x_out = (pw * inch - outside * inch) if recto else (pw * inch - inside * inch)
        cx = (x_in + x_out) / 2
        if not st.get("opener"):
            canvas.setFont(*head_font)
            text = (st.get("chapter") if recto else book.get("title")).upper()
            if canvas.stringWidth(text, *head_font) > fw * 0.9:
                while text and canvas.stringWidth(text + "…", *head_font) > fw * 0.9:
                    text = text[:-1]
                text = text.rstrip() + "…"
            y = ph * inch - top * inch + 0.28 * inch
            canvas.drawCentredString(cx, y, text)
        canvas.setFont(*folio_font)
        canvas.drawCentredString(cx, bottom * inch - 0.35 * inch, str(d.page))
        canvas.restoreState()

    recto_frame = Frame(inside * inch, bottom * inch, fw, fh, id="r", leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    verso_frame = Frame(outside * inch, bottom * inch, fw, fh, id="v", leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    rt = PageTemplate("recto", [recto_frame], onPage=on_begin, onPageEnd=on_end, autoNextPageTemplate="verso")
    vt = PageTemplate("verso", [verso_frame], onPage=on_begin, onPageEnd=on_end, autoNextPageTemplate="recto")
    doc.addPageTemplates([rt, vt])

    notes = []
    warnings = []
    conv = Converter(s, fw, fh, book.root, notes, warnings)
    story = [Marker(doc, section="front"), TitlePage(book.get("title"), book.get("subtitle", ""), book.get("author"), s)]
    toc_entries = []
    body = []
    words = 0
    recto_keys = []

    def recto_break(key):
        body.append(PageBreak())
        if key in blanks:
            body.append(BlankPage(doc))
            body.append(PageBreak())
        recto_keys.append(key)

    front = [x for x in sections if x["role"] == "front"]
    rest = [x for x in sections if x["role"] != "front"]
    front_flow = []
    for sec in front:
        title, tree = load_section(sec)
        words += word_count(tree)
        conv.section_path = sec["path"]
        notes.append((title, []))
        front_flow.append(PageBreak())
        if sec["style"] == "small":
            front_flow.append(Spacer(1, fh * 0.35))
            front_flow.extend(conv.blocks(tree, s["small"]))
        else:
            front_flow += [Spacer(1, 0.9 * inch), Paragraph(esc(title), s["chapter"]), Ornament(), Spacer(1, 14)]
            front_flow.extend(conv.blocks(tree))

    # Convert everything first (so all footnotes are known), then emit chapters, Notes, back matter.
    converted = []
    for i, sec in enumerate(rest):
        title, tree = load_section(sec)
        words += word_count(tree)
        conv.section_path = sec["path"]
        notes.append((title, []))
        converted.append((f"s{i}", sec["role"], title, conv.blocks(tree)))

    def emit(key, title, flow):
        recto_break(key)
        body.append(Marker(doc, section="body", chapter=title, opener=True, record=key))
        body.extend([Spacer(1, 1.1 * inch), Paragraph(esc(title), s["chapter"]), Ornament(), Spacer(1, 18)])
        body.extend(flow)
        toc_entries.append((key, title))

    for key, role, title, flow in converted:
        if role == "chapter":
            emit(key, title, flow)
    note_groups = [(t, n) for t, n in notes if n]
    if note_groups:
        flow = []
        for t, items in note_groups:
            flow.append(Paragraph(esc(t), s["notehead"]))
            for j, txt in enumerate(items, 1):
                flow.append(Paragraph(f"{j}.&nbsp;&nbsp;{txt}", s["note"]))
        emit("notes", "Notes", flow)
    for key, role, title, flow in converted:
        if role == "back":
            emit(key, title, flow)

    # Contents page(s)
    toc = [PageBreak()]
    if "toc" in blanks:
        toc += [BlankPage(doc), PageBreak()]
    recto_keys.insert(0, "toc")
    toc += [Marker(doc, record="toc"), Spacer(1, 0.9 * inch), Paragraph("Contents", s["chapter"]), Ornament(),
            Spacer(1, 18)]
    rows = []
    for key, title in toc_entries:
        num = str(toc_numbers.get(key, "000")) if toc_numbers else "000"
        rows.append([Paragraph(esc(title), s["toc"]), Paragraph(num, s["tocnum"])])
    if rows:
        t = Table(rows, colWidths=[fw * 0.85, fw * 0.15])
        t.setStyle(TableStyle(EMBED + [("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        toc.append(t)

    story += front_flow + toc + body
    if pad_end:
        story += [PageBreak(), BlankPage(doc)]
    doc.build(story)
    info = {"pages": doc.page, "starts": dict(doc.starts), "recto_keys": recto_keys, "words": words,
            "warnings": warnings, "toc_keys": [k for k, _ in toc_entries],
            "geometry": {"page_w": pw, "page_h": ph, "inside": inside, "outside": outside, "top": top,
                         "bottom": bottom, "gutter_min": gutter, "bleed": bleed}}
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="path to book.json (or its folder)")
    ap.add_argument("--out", help="output PDF (default: build/interior.pdf)")
    ap.add_argument("--trim", help="trim size, e.g. 6x9 (default: book.json trim)")
    ap.add_argument("--bleed", action="store_true", help="interior has full-bleed images (default: book.json bleed)")
    ap.add_argument("--gutter-extra", type=float, default=0.125, help="inches added to KDP's minimum gutter")
    ap.add_argument("--outside", type=float, default=0.6)
    ap.add_argument("--top", type=float, default=0.7)
    ap.add_argument("--bottom", type=float, default=0.75)
    args = ap.parse_args()

    book = Book(args.book)
    trim = trim_size(args.trim) if args.trim else book.trim()
    bleed = args.bleed or bool(book.get("bleed", False))
    out = Path(args.out) if args.out else book.build_dir / "interior.pdf"
    margins = {"outside": args.outside, "top": args.top, "bottom": args.bottom}
    for k, v in margins.items():
        if v < MIN_OUTSIDE + (0.125 if bleed else 0):
            die(f"{k} margin {v} is below KDP's minimum")
    register_fonts(book.fonts())
    sections = book.sections()

    pages_guess = 100
    blanks, toc_numbers, pad = set(), {}, False
    info = None
    for attempt in range(8):
        gutter = gutter_for(pages_guess)
        info = layout(book, sections, out, trim, bleed, gutter, args.gutter_extra, margins, blanks, toc_numbers, pad)
        changed = False
        # Fix recto starts in one sweep: a blank page before a section shifts every later section by one.
        shift = 0
        new_blanks = set(blanks)
        for key in info["recto_keys"]:
            p = info["starts"][key] + shift
            if p % 2 == 0:
                if key in new_blanks:
                    new_blanks.discard(key)
                    shift -= 1
                else:
                    new_blanks.add(key)
                    shift += 1
        if new_blanks != blanks:
            blanks, changed = new_blanks, True
        final_starts = {k: info["starts"][k] for k in info["toc_keys"]}
        if not changed and final_starts != toc_numbers:
            toc_numbers, changed = final_starts, True
        if not changed and info["pages"] % 2 == 1:
            pad, changed = not pad, True
        if not changed and gutter_for(info["pages"]) != gutter:
            pages_guess, changed = info["pages"], True
        if not changed:
            break
    else:
        die("Layout did not stabilise after 8 passes; check for very long unbreakable elements.")

    bad = [k for k in info["recto_keys"] if info["starts"][k] % 2 == 0]
    report = {
        "file": str(out), "trim": list(trim), "bleed": bleed, "pages": info["pages"], "words": info["words"],
        "gutter_min_for_pages": gutter_for(info["pages"]), "geometry": info["geometry"],
        "chapter_starts": {k: info["starts"][k] for k in info["toc_keys"]}, "even_page_chapter_starts": bad,
        "image_warnings": info["warnings"], "fonts": FONT_CREDITS if not book.fonts() else "custom (see book.json)",
        "passes": attempt + 1,
    }
    write_json(book.build_dir / "interior_report.json", report)
    print(f"Interior PDF written: {out}")
    print(f"  trim {trim[0]}x{trim[1]} in{' + bleed' if bleed else ''}, {info['pages']} pages, {info['words']:,} words,"
          f" gutter {info['geometry']['inside']:.3f} in (KDP min {gutter_for(info['pages'])} for this page count),"
          f" {attempt + 1} layout passes")
    if info["pages"] < MIN_PAGES:
        print(f"  WARNING: {info['pages']} pages is under KDP's {MIN_PAGES}-page paperback minimum; publish as eBook only.")
    for w in info["warnings"]:
        print("  WARNING:", w)
    if bad:
        print("  WARNING: sections starting on left-hand pages:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
