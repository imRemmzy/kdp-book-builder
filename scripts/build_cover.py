#!/usr/bin/env python3
"""Generate eBook covers, a matching title page, and the full paperback cover wrap, all drawn in code.

Usage:
    python build_cover.py book.json --concepts            # 3 concept covers + comparison sheet, for the user to pick
    python build_cover.py book.json --style band          # final eBook cover + title page (+ wrap if pages known)
    python build_cover.py book.json --style band --wrap --pages 124 --paper white

Spec comes from book.json: title, subtitle, author, trim, paper, and a "cover" block:
    "cover": {"style": "band", "palette": {"background": "#1d3b2f", "accent": "#e2a93b", "text": "#ffffff",
              "light": "#f5f0e6"}, "back_text": "Back-cover description...", "seed": 7}
Page count for the wrap comes from --pages or build/interior_report.json (run build_interior_pdf.py first).
Styles: band, classic, geometric. Outputs go to the book's build folder; build/cover_report.json records the
spine math, dimensions, contrast ratios and thumbnail legibility.
"""
import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BLEED, Book, contrast_ratio, cover_dimensions, die, font_path, hex_to_rgb,  # noqa: E402
                    write_json)

STYLES = ("band", "classic", "geometric")
EBOOK_W, EBOOK_H = 1600, 2560
DPI = 300
DEFAULT_PALETTE = {"background": "#1f3a4d", "accent": "#e8a33d", "text": "#ffffff", "light": "#f4efe4"}


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Fonts:
    def __init__(self, overrides):
        self.o = overrides
        self.cache = {}

    def get(self, family, style, size):
        key = (family, style, int(size))
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(font_path(family, style, self.o), int(size))
        return self.cache[key]


def wrap(text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_w:
            cur = trial
        else:
            if not cur or font.getlength(w) > max_w:
                return None
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(fonts, text, family, style, max_w, max_h, start, minimum, max_lines, spacing=1.12):
    size = start
    while size >= minimum:
        f = fonts.get(family, style, size)
        lines = wrap(text, f, max_w)
        if lines and len(lines) <= max_lines and len(lines) * size * spacing <= max_h:
            return f, lines, size
        size = int(size * 0.95)
    f = fonts.get(family, style, minimum)
    return f, wrap(text, f, max_w) or [text], minimum


def draw_lines(d, lines, font, size, x, y, fill, align="center", spacing=1.12, width=None):
    for i, line in enumerate(lines):
        ly = y + i * size * spacing
        if align == "center":
            d.text((x + width / 2, ly), line, font=font, fill=fill, anchor="ma")
        else:
            d.text((x, ly), line, font=font, fill=fill, anchor="la")
    return y + len(lines) * size * spacing


def ornament(d, cx, y, half, color, thick):
    d.line([(cx - half, y), (cx - thick * 4, y)], fill=color, width=thick)
    d.line([(cx + thick * 4, y), (cx + half, y)], fill=color, width=thick)
    r = thick * 2.6
    d.polygon([(cx, y - r), (cx + r, y), (cx, y + r), (cx - r, y)], fill=color)


def render_front(W, H, safe, spec, style, fonts):
    """Draw a front cover of W x H px. safe = (left, top, right, bottom) px insets for text."""
    pal = {k: hex_to_rgb(v) for k, v in spec["palette"].items()}
    title, subtitle, author = spec["title"], spec.get("subtitle", ""), spec["author"]
    sl, st, sr, sb = safe
    box_w = W - sl - sr
    info = {"style": style}

    if style == "band":
        bg = pal["background"]
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        band_top, band_bot = int(H * 0.60), int(H * 0.73)
        zone_h = band_top - H * 0.07 - st
        f, lines, size = fit(fonts, title, "sans", "bold", box_w, zone_h - H * 0.04, int(W * 0.15),
                             int(W * 0.05), 4)
        y = st + (zone_h - len(lines) * size * 1.12) / 2
        draw_lines(d, lines, f, size, sl, y, pal["text"], width=box_w)
        d.line([(sl + box_w * 0.3, band_top - H * 0.035), (sl + box_w * 0.7, band_top - H * 0.035)],
               fill=pal["accent"], width=max(2, W // 250))
        d.rectangle([0, band_top, W, band_bot], fill=pal["accent"])
        if subtitle:
            sf, sl_, ss = fit(fonts, subtitle, "serif", "italic", box_w * 0.9, (band_bot - band_top) * 0.8,
                              int(W * 0.055), int(W * 0.028), 3, 1.15)
            th = len(sl_) * ss * 1.15
            draw_lines(d, sl_, sf, ss, sl + box_w * 0.05, band_top + (band_bot - band_top - th) / 2 + ss * 0.05,
                       pal["background"], width=box_w * 0.9, spacing=1.15)
            info["subtitle_contrast"] = round(contrast_ratio(pal["background"], pal["accent"]), 2)
        af, al, asz = fit(fonts, author.upper(), "sans", "regular", box_w, H * 0.06, int(W * 0.05),
                          int(W * 0.03), 1)
        draw_lines(d, al, af, asz, sl, H - sb - asz * 1.3, pal["accent"], width=box_w)
        info.update(title_color=pal["text"], title_bg=bg, title_size=size)

    elif style == "classic":
        bg = pal.get("light", hex_to_rgb(DEFAULT_PALETTE["light"]))
        ink = pal["background"]
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        t1 = max(3, W // 160)
        inset_l, inset_t, inset_r, inset_b = sl - W * 0.02, st - W * 0.02, sr - W * 0.02, sb - W * 0.02
        d.rectangle([inset_l, inset_t, W - inset_r, H - inset_b], outline=ink, width=t1)
        g = t1 * 3
        d.rectangle([inset_l + g, inset_t + g, W - inset_r - g, H - inset_b - g], outline=ink, width=max(1, t1 // 3))
        inner_w = box_w * 0.86
        x0 = sl + box_w * 0.07
        f, lines, size = fit(fonts, title, "serif", "bold", inner_w, H * 0.34, int(W * 0.14), int(W * 0.05), 4, 1.08)
        y = st + H * 0.16
        y = draw_lines(d, lines, f, size, x0, y, ink, width=inner_w, spacing=1.08)
        oy = y + H * 0.035
        ornament(d, W / 2, oy, box_w * 0.22, pal["accent"], max(2, W // 300))
        if subtitle:
            sf, sl_, ss = fit(fonts, subtitle, "serif", "italic", inner_w, H * 0.14, int(W * 0.05), int(W * 0.028), 4, 1.2)
            draw_lines(d, sl_, sf, ss, x0, oy + H * 0.04, mix(ink, bg, 0.15), width=inner_w, spacing=1.2)
        af, al, asz = fit(fonts, author.upper(), "sans", "regular", inner_w, H * 0.06, int(W * 0.045), int(W * 0.028), 1)
        draw_lines(d, al, af, asz, x0, H - sb - H * 0.09, ink, width=inner_w)
        info.update(title_color=ink, title_bg=bg, title_size=size)

    elif style == "geometric":
        bg = pal["background"]
        img = Image.new("RGB", (W, H), bg).convert("RGBA")
        rng = random.Random(spec.get("seed", 7))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        shades = [pal["accent"], mix(pal["accent"], bg, 0.45), mix(bg, (255, 255, 255), 0.18), mix(bg, (0, 0, 0), 0.25)]
        zone_top = int(H * 0.58)
        # Whole circles rising from the bottom edge; none may enter the text zone.
        for i in range(10):
            r = rng.randint(int(W * 0.1), int(W * 0.36))
            cx = rng.randint(-int(W * 0.1), int(W * 1.1))
            cy = rng.randint(zone_top + r, max(zone_top + r, int(H + r * 0.4)))
            c = shades[i % len(shades)]
            od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (rng.randint(150, 235),))
        img = Image.alpha_composite(img, overlay).convert("RGB")
        d = ImageDraw.Draw(img)
        af, al, asz = fit(fonts, author.upper(), "sans", "bold", box_w, H * 0.05, int(W * 0.042), int(W * 0.026), 1)
        draw_lines(d, al, af, asz, sl, st + H * 0.01, pal["accent"], align="left")
        f, lines, size = fit(fonts, title, "sans", "bold", box_w, H * 0.33, int(W * 0.15), int(W * 0.05), 4, 1.05)
        y = draw_lines(d, lines, f, size, sl, st + H * 0.1, pal["text"], align="left", spacing=1.05)
        d.rectangle([sl, y + H * 0.015, sl + box_w * 0.18, y + H * 0.015 + max(4, W // 120)], fill=pal["accent"])
        if subtitle:
            sf, sl_, ss = fit(fonts, subtitle, "serif", "italic", box_w * 0.95, zone_top - y - H * 0.06,
                              int(W * 0.052), int(W * 0.028), 4, 1.18)
            draw_lines(d, sl_, sf, ss, sl, y + H * 0.045, mix(pal["text"], bg, 0.12), align="left", spacing=1.18)
        info.update(title_color=pal["text"], title_bg=bg, title_size=size)
    else:
        die(f"Unknown style '{style}'. Use one of {', '.join(STYLES)}.")

    info["title_contrast"] = round(contrast_ratio(info["title_color"], info["title_bg"]), 2)
    info["title_px_at_150"] = round(info["title_size"] * 150 / W, 1)
    return img, info


def ebook_safe():
    return (int(EBOOK_W * 0.07), int(EBOOK_H * 0.05), int(EBOOK_W * 0.07), int(EBOOK_H * 0.05))


def spec_from(book):
    c = book.get("cover") or {}
    pal = dict(DEFAULT_PALETTE)
    pal.update(c.get("palette") or {})
    return {"title": book.get("title"), "subtitle": book.get("subtitle", ""), "author": book.get("author"),
            "palette": pal, "back_text": c.get("back_text", ""), "seed": c.get("seed", 7)}


def legibility_notes(info):
    notes = []
    if info["title_contrast"] < 4.5:
        notes.append(f"title contrast {info['title_contrast']}:1 is low (aim for 4.5:1 or more)")
    if info["title_px_at_150"] < 9:
        notes.append(f"title letters are only ~{info['title_px_at_150']} px tall at 150 px wide; shorten the title "
                     "or use fewer words on the cover")
    return notes


def make_concepts(book, fonts, out_dir):
    spec = spec_from(book)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    tiles = []
    for style in STYLES:
        img, info = render_front(EBOOK_W, EBOOK_H, ebook_safe(), spec, style, fonts)
        p = out_dir / f"concept_{style}.jpg"
        img.save(p, "JPEG", quality=92)
        thumb = img.resize((150, 240), Image.LANCZOS)
        thumb.save(out_dir / f"concept_{style}_thumb150.png")
        results[style] = {"file": str(p), **{k: v for k, v in info.items() if k not in ("title_color", "title_bg")},
                          "notes": legibility_notes(info)}
        tiles.append((style, img.resize((480, 768), Image.LANCZOS), thumb))
    pad = 40
    sheet = Image.new("RGB", (pad + 3 * (480 + pad), 768 + 240 + pad * 4), (236, 236, 236))
    d = ImageDraw.Draw(sheet)
    lab = fonts.get("sans", "bold", 26)
    for i, (style, big, thumb) in enumerate(tiles):
        x = pad + i * (480 + pad)
        d.text((x, pad // 2 - 4), f"{i + 1}. {style}", font=lab, fill=(30, 30, 30))
        sheet.paste(big, (x, pad + 20))
        sheet.paste(thumb, (x, pad * 2 + 768 + 20))
        d.text((x + 165, pad * 2 + 768 + 20), "thumbnail at\n150 px wide", font=fonts.get("sans", "regular", 20),
               fill=(60, 60, 60))
    sheet_p = out_dir / "cover_concepts.png"
    sheet.save(sheet_p)
    write_json(out_dir / "concepts_report.json", results)
    print(f"Concepts written to {out_dir} (comparison sheet: {sheet_p.name})")
    for s, r in results.items():
        print(f"  {s}: title contrast {r['title_contrast']}:1, title ~{r['title_px_at_150']} px tall at 150 px"
              + ("" if not r["notes"] else "  NOTE: " + "; ".join(r["notes"])))


def make_title_page(book, fonts, style, out):
    spec = spec_from(book)
    pal = {k: hex_to_rgb(v) for k, v in spec["palette"].items()}
    W, H = EBOOK_W, EBOOK_H
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ink = pal["background"] if contrast_ratio(pal["background"], (255, 255, 255)) >= 4.5 else (20, 20, 20)
    fam, sty = ("serif", "bold") if style == "classic" else ("sans", "bold")
    box = W * 0.8
    x0 = W * 0.1
    f, lines, size = fit(fonts, spec["title"], fam, sty, box, H * 0.3, int(W * 0.11), int(W * 0.045), 4)
    y = draw_lines(d, lines, f, size, x0, H * 0.2, ink, width=box)
    ornament(d, W / 2, y + H * 0.04, W * 0.18, pal["accent"] if contrast_ratio(pal["accent"], (255, 255, 255)) > 1.8
             else ink, max(2, W // 300))
    if spec["subtitle"]:
        sf, sl_, ss = fit(fonts, spec["subtitle"], "serif", "italic", box * 0.9, H * 0.15, int(W * 0.045),
                          int(W * 0.028), 4, 1.2)
        draw_lines(d, sl_, sf, ss, x0 + box * 0.05, y + H * 0.08, (60, 60, 60), width=box * 0.9, spacing=1.2)
    af, al, asz = fit(fonts, spec["author"].upper(), "sans", "regular", box, H * 0.05, int(W * 0.042), int(W * 0.028), 1)
    draw_lines(d, al, af, asz, x0, H * 0.82, ink, width=box)
    img.save(out)


def make_ebook(book, fonts, style, build):
    spec = spec_from(book)
    img, info = render_front(EBOOK_W, EBOOK_H, ebook_safe(), spec, style, fonts)
    p = build / "cover_ebook.jpg"
    img.save(p, "JPEG", quality=94)
    img.resize((150, 240), Image.LANCZOS).save(build / "cover_ebook_thumb150.png")
    make_title_page(book, fonts, style, build / "title_page.png")
    return p, info


def make_wrap(book, fonts, style, pages, paper, build):
    spec = spec_from(book)
    pal = {k: hex_to_rgb(v) for k, v in spec["palette"].items()}
    tw, th = book.trim()
    dims = cover_dimensions(tw, th, pages, paper)
    Wpx, Hpx = round(dims["width"] * DPI), round(dims["height"] * DPI)
    back_x1 = round((BLEED + tw) * DPI)
    spine_x1 = round((BLEED + tw + dims["spine"]) * DPI)
    back_bg = pal.get("light") if style == "classic" else pal["background"]
    back_ink = pal["background"] if style == "classic" else pal["text"]
    img = Image.new("RGB", (Wpx, Hpx), back_bg)

    q = int(0.25 * DPI)
    b = int(BLEED * DPI)
    front, finfo = render_front(Wpx - spine_x1, Hpx, (q, b + q, b + q, b + q), spec, style, fonts)
    img.paste(front, (spine_x1, 0))

    # Spine
    spine_bg = pal["accent"] if style == "band" else pal["background"]
    d = ImageDraw.Draw(img)
    d.rectangle([back_x1, 0, spine_x1 - 1, Hpx], fill=spine_bg)
    spine_note = "no spine text (KDP allows it only above 79 pages)"
    if dims["spine_text_allowed"]:
        cands = [pal["text"], pal["background"], pal.get("light", (255, 255, 255)), (255, 255, 255), (0, 0, 0)]
        ink = max(cands, key=lambda c: contrast_ratio(c, spine_bg))
        clear = 0.0625 * DPI  # KDP: at least 0.0625" between spine text and each fold
        max_h = (spine_x1 - back_x1) - 2 * clear - 4
        length = Hpx - 2 * (b + int(0.4 * DPI))
        # All caps: only cap height has to fit across the spine, so the type can be larger.
        text = f"{spec['title']}  •  {spec['author']}".upper()
        size = int(max_h * 1.6)
        while size >= 21:  # about 5 pt at 300 DPI
            ft = fonts.get("sans", "bold", size)
            x0, y0, x1, y1 = ft.getbbox(text)
            if y1 - y0 <= max_h and x1 - x0 <= length:
                break
            size = int(size * 0.95)
        if size >= 21:
            ft = fonts.get("sans", "bold", size)
            x0, y0, x1, y1 = ft.getbbox(text)
            strip = Image.new("RGB", (x1 - x0 + 4, y1 - y0 + 4), spine_bg)
            ImageDraw.Draw(strip).text((2 - x0, 2 - y0), text, font=ft, fill=ink)
            strip = strip.rotate(-90, expand=True)
            sx = back_x1 + ((spine_x1 - back_x1) - strip.width) // 2
            sy = (Hpx - strip.height) // 2
            img.paste(strip, (sx, sy))
            spine_note = f"spine text {size / DPI * 72:.1f} pt, contrast {contrast_ratio(ink, spine_bg):.1f}:1"
        else:
            spine_note = "spine too narrow for legible text; left plain"

    # Back cover: description, kept clear of the barcode box
    barcode = (back_x1 - int(0.25 * DPI) - int(2.0 * DPI), Hpx - b - int(0.25 * DPI) - int(1.2 * DPI),
               back_x1 - int(0.25 * DPI), Hpx - b - int(0.25 * DPI))
    bx0, bx1 = b + int(0.5 * DPI), back_x1 - int(0.5 * DPI)
    by0, by1 = b + int(0.6 * DPI), barcode[1] - int(0.3 * DPI)
    tf, tl, tsz = fit(fonts, spec["title"], "sans", "bold", bx1 - bx0, int(0.9 * DPI), int(0.3 * DPI), int(0.14 * DPI), 2)
    y = draw_lines(d, tl, tf, tsz, bx0, by0, back_ink, width=bx1 - bx0)
    y += 0.2 * DPI
    back_text = spec["back_text"].strip()
    if not back_text:
        print("  NOTE: cover.back_text is empty; the back cover will only show the title.")
    paras = [p.strip() for p in back_text.split("\n\n") if p.strip()]
    size = int(0.2 * DPI)
    while size > int(0.1 * DPI) and paras:
        f = fonts.get("serif", "regular", size)
        wrapped = [wrap(p, f, bx1 - bx0) or [p] for p in paras]
        total = sum(len(w) for w in wrapped) * size * 1.3 + (len(paras) - 1) * size * 0.7
        if total <= by1 - y:
            break
        size = int(size * 0.95)
    if paras:
        f = fonts.get("serif", "regular", size)
        for p in paras:
            lines = wrap(p, f, bx1 - bx0) or [p]
            y = draw_lines(d, lines, f, size, bx0, y, back_ink, align="left", spacing=1.3)
            y += size * 0.7
        if y > by1:
            print("  WARNING: back text overflows into the barcode clearance; shorten cover.back_text.")

    pdf_p = build / "cover_paperback.pdf"
    pdfmetrics.registerFont(TTFont("CoverSans", font_path("sans", "regular", book.fonts())))
    c = rl_canvas.Canvas(str(pdf_p), pagesize=(dims["width"] * 72, dims["height"] * 72),
                         initialFontName="CoverSans")  # avoid an unembedded default Helvetica
    c.setTitle(f"{spec['title']} - cover")
    c.drawImage(ImageReader(img), 0, 0, width=dims["width"] * 72, height=dims["height"] * 72)
    c.showPage()
    c.save()

    # Guide overlay for checking (not for upload)
    g = img.copy()
    gd = ImageDraw.Draw(g)
    lw = 6
    gd.rectangle([b, b, Wpx - b, Hpx - b], outline=(255, 0, 0), width=lw)
    for x in (back_x1, spine_x1):
        gd.line([(x, 0), (x, Hpx)], fill=(0, 90, 255), width=lw)
    gd.rectangle([b + q, b + q, back_x1 - q, Hpx - b - q], outline=(0, 170, 0), width=lw)
    gd.rectangle([spine_x1 + q, b + q, Wpx - b - q, Hpx - b - q], outline=(0, 170, 0), width=lw)
    gd.rectangle(barcode, outline=(255, 140, 0), width=lw)
    gd.text((barcode[0] + 20, barcode[1] + 20), "barcode area", font=fonts.get("sans", "bold", 60), fill=(255, 140, 0))
    scale = 1500 / Wpx
    g.resize((1500, int(Hpx * scale)), Image.LANCZOS).save(build / "cover_paperback_guides.png")

    report = {**dims, "pixels": [Wpx, Hpx], "dpi": DPI, "file": str(pdf_p), "spine": dims["spine"],
              "spine_note": spine_note, "front": {k: v for k, v in finfo.items() if k not in ("title_color", "title_bg")},
              "barcode_box_in": [round(v / DPI, 3) for v in barcode],
              "math": f"{BLEED} + {tw} + ({pages} x {dims['spine'] / pages:.6f} = {dims['spine']}) + {tw} + {BLEED}"
                      f" = {dims['width']} in wide; {BLEED} + {th} + {BLEED} = {dims['height']} in tall"}
    return pdf_p, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--concepts", action="store_true", help="render all 3 styles for the user to choose")
    ap.add_argument("--style", choices=STYLES, help="final style (default: book.json cover.style)")
    ap.add_argument("--wrap", action="store_true", help="also build the paperback wrap")
    ap.add_argument("--no-wrap", action="store_true", help="skip the wrap even if the page count is known")
    ap.add_argument("--pages", type=int, help="final interior page count (default: build/interior_report.json)")
    ap.add_argument("--paper", help="white, cream, standard-color, premium-color (default: book.json paper)")
    args = ap.parse_args()

    book = Book(args.book)
    fonts = Fonts(book.fonts())
    build = book.build_dir
    if args.concepts:
        make_concepts(book, fonts, build / "cover_concepts")
        return
    style = args.style or (book.get("cover") or {}).get("style")
    if not style:
        die("Pick a style with --style (or set cover.style in book.json). Run --concepts first to compare.")
    p, info = make_ebook(book, fonts, style, build)
    report = {"style": style, "ebook": {"file": str(p), "size_px": [EBOOK_W, EBOOK_H], "mode": "RGB",
                                        **{k: v for k, v in info.items() if k not in ("title_color", "title_bg")},
                                        "notes": legibility_notes(info)}}
    print(f"eBook cover: {p} ({EBOOK_W}x{EBOOK_H} RGB JPEG), title contrast {info['title_contrast']}:1,"
          f" title ~{info['title_px_at_150']} px tall at 150 px wide")
    for n in legibility_notes(info):
        print("  NOTE:", n)
    print(f"Title page: {build / 'title_page.png'}")

    pages = args.pages
    rep_p = build / "interior_report.json"
    if not pages and rep_p.exists():
        pages = json.loads(rep_p.read_text(encoding="utf-8"))["pages"]
    want_wrap = (args.wrap or pages) and not args.no_wrap
    if want_wrap:
        if not pages:
            die("Wrap needs the page count: pass --pages or build the interior first.")
        paper = args.paper or book.get("paper", "white")
        pdf, wrep = make_wrap(book, fonts, style, pages, paper, build)
        report["paperback"] = wrep
        print(f"Paperback wrap: {pdf}")
        print(f"  {wrep['math']}")
        print(f"  {wrep['spine_note']}; guides: {build / 'cover_paperback_guides.png'}")
    write_json(build / "cover_report.json", report)


if __name__ == "__main__":
    main()
