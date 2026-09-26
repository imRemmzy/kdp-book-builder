#!/usr/bin/env python3
"""Inspect a built KDP package and report PASS / WARN / FAIL for each check.

Usage:
    python check_package.py path/to/book.json [--no-previews]

Checks: interior PDF (page size, embedded fonts, text inside KDP margins incl. gutter for the final page count,
chapters on odd pages, page-count limits), EPUB structure, eBook cover size/mode, paperback cover size against
the spine formula for the interior's actual page count, citations (footnote URLs present in
research/sources.md), fact-check log status, banned AI-tell phrases, and the upload sheet's key sections.
Renders preview PNGs of sample interior pages to build/preview/ so they can be looked at.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BLEED, MAX_PAGES, MIN_PAGES, Book, cover_dimensions, gutter_for  # noqa: E402
from build_epub import check_epub  # noqa: E402

BANNED = ["delve", "tapestry", "testament to", "fast-paced world", "ever-evolving", "navigate the complexities",
          "embark on a journey", "unlock the secrets", "unleash", "game-changer", "game changer", "treasure trove",
          "it's important to note", "it’s important to note", "it's worth noting", "it’s worth noting",
          "plays a crucial role", "plays a pivotal role", "a myriad of", "harness the power", "seamlessly",
          "whether you're a beginner", "whether you’re a beginner", "look no further", "deep dive",
          "at the end of the day", "the world of", "in today's", "in today’s", "serves as a reminder",
          "nestled", "bustling", "elevate your"]

results = []


def rec(level, msg):
    results.append((level, msg))


def check_interior(book, build, previews):
    pdf_p = build / "interior.pdf"
    rep_p = build / "interior_report.json"
    if not pdf_p.exists():
        rec("WARN", "no interior.pdf (fine if this is eBook-only)")
        return None
    rep = json.loads(rep_p.read_text(encoding="utf-8")) if rep_p.exists() else {}
    doc = pymupdf.open(pdf_p)
    n = doc.page_count
    tw, th = rep.get("trim") or book.trim()
    bleed = rep.get("bleed", False)
    ew, eh = (tw + (BLEED if bleed else 0)) * 72, (th + (2 * BLEED if bleed else 0)) * 72
    bad_size = [i + 1 for i, p in enumerate(doc) if abs(p.rect.width - ew) > 0.5 or abs(p.rect.height - eh) > 0.5]
    rec("FAIL" if bad_size else "PASS",
        f"interior page size {tw}x{th} in{' + bleed' if bleed else ''}" + (f" wrong on pages {bad_size[:10]}" if bad_size else ""))
    if n < MIN_PAGES:
        rec("FAIL", f"{n} pages is below KDP's {MIN_PAGES}-page paperback minimum (publish eBook-only)")
    elif n > MAX_PAGES:
        rec("FAIL", f"{n} pages is above KDP's {MAX_PAGES}-page maximum")
    else:
        rec("PASS", f"page count {n} within {MIN_PAGES}-{MAX_PAGES}" + (" (even)" if n % 2 == 0 else " (odd)"))

    unembedded, fonts = set(), set()
    for p in doc:
        for f in p.get_fonts(full=True):
            fonts.add(f[3])
            if f[1] in ("n/a", ""):
                unembedded.add(f[3])
    rec("FAIL" if unembedded else "PASS",
        f"fonts embedded ({len(fonts)} font resources)" + (f"; NOT embedded: {sorted(unembedded)}" if unembedded else ""))

    gmin = gutter_for(n) * 72
    omin = (0.25 + (BLEED if bleed else 0)) * 72
    tmin = omin
    worst = []
    for i, p in enumerate(doc):
        recto = (i + 1) % 2 == 1
        W, H = p.rect.width, p.rect.height
        for b in p.get_text("blocks"):
            x0, y0, x1, y1 = b[:4]
            if not b[4].strip():
                continue
            inside = x0 if recto else W - x1
            outside = W - x1 if recto else x0
            probs = []
            if inside < gmin - 0.5:
                probs.append(f"inside {inside / 72:.3f} in < gutter {gmin / 72:.3f}")
            if outside < omin - 0.5:
                probs.append(f"outside {outside / 72:.3f} in")
            if y0 < tmin - 0.5 or H - y1 < tmin - 0.5:
                probs.append("top/bottom margin")
            if probs:
                worst.append(f"page {i + 1}: {', '.join(probs)}")
    rec("FAIL" if worst else "PASS", f"all text inside KDP margins (gutter {gmin / 72} in for {n} pages)"
        + (f"; {len(worst)} problems, e.g. {worst[:3]}" if worst else ""))

    if rep:
        if rep.get("pages") != n:
            rec("FAIL", f"interior_report.json says {rep.get('pages')} pages but PDF has {n}; rebuild")
        bad = rep.get("even_page_chapter_starts") or []
        rec("FAIL" if bad else "PASS", "every chapter starts on a right-hand (odd) page" + (f": {bad}" if bad else ""))
        for w in rep.get("image_warnings", []):
            rec("WARN", "image resolution: " + w)

    if previews:
        pv = build / "preview"
        pv.mkdir(exist_ok=True)
        starts = sorted((rep.get("chapter_starts") or {}).values())
        picks = sorted({1, 2, 3, *(starts[:2]), (starts[0] + 1) if starts else 4, n // 2, n - 1, n} & set(range(1, n + 1)))
        for k in picks:
            doc[k - 1].get_pixmap(dpi=110).save(pv / f"page-{k:03d}.png")
        thumbs = [Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  for pm in (doc[i].get_pixmap(dpi=40) for i in range(min(n, 16)))]
        if thumbs:
            tw_, th_ = thumbs[0].size
            sheet = Image.new("RGB", (8 * (tw_ + 10) + 10, 2 * (th_ + 10) + 10), (200, 200, 200))
            for i, t in enumerate(thumbs):
                sheet.paste(t, (10 + (i % 8) * (tw_ + 10), 10 + (i // 8) * (th_ + 10)))
            sheet.save(pv / "first_pages_sheet.png")
        if starts and starts[0] > 1:
            a, b = doc[starts[0] - 2].get_pixmap(dpi=90), doc[starts[0] - 1].get_pixmap(dpi=90)
            sp = Image.new("RGB", (a.width + b.width, a.height), (255, 255, 255))
            sp.paste(Image.frombytes("RGB", (a.width, a.height), a.samples), (0, 0))
            sp.paste(Image.frombytes("RGB", (b.width, b.height), b.samples), (a.width, 0))
            sp.save(pv / "spread_first_chapter.png")
        rec("INFO", f"preview images in {pv} (pages {picks}); open and look at them")
    return n


def check_epub_file(build):
    epubs = sorted(build.glob("*.epub"))
    if not epubs:
        rec("WARN", "no EPUB in build folder")
        return
    for e in epubs:
        probs = check_epub(e)
        rec("FAIL" if probs else "PASS", f"EPUB structure {e.name}" + (f": {probs[:5]}" if probs else ""))
        mb = e.stat().st_size / 1e6
        rec("INFO", f"EPUB size {mb:.2f} MB (70% royalty delivery cost scales with converted file size)")


def check_covers(book, build, pages):
    eb = build / "cover_ebook.jpg"
    if eb.exists():
        with Image.open(eb) as im:
            ok = im.size == (1600, 2560) and im.mode == "RGB" and im.format == "JPEG"
            rec("PASS" if ok else "FAIL", f"eBook cover {im.size[0]}x{im.size[1]} {im.mode} {im.format}"
                + ("" if ok else " (want 1600x2560 RGB JPEG)"))
    else:
        rec("FAIL", "no cover_ebook.jpg")
    cp = build / "cover_paperback.pdf"
    if pages and cp.exists():
        paper = book.get("paper", "white")
        tw, th = book.trim()
        dims = cover_dimensions(tw, th, pages, paper)
        d = pymupdf.open(cp)
        r = d[0].rect
        ok = abs(r.width / 72 - dims["width"]) < 0.01 and abs(r.height / 72 - dims["height"]) < 0.01
        rec("PASS" if ok else "FAIL",
            f"paperback cover {r.width / 72:.4f} x {r.height / 72:.4f} in vs formula {dims['width']} x {dims['height']}"
            f" for {pages} pages on {paper} (spine {dims['spine']} in)")
        unemb = {f[3] for f in d[0].get_fonts(full=True) if f[1] in ("n/a", "")}
        rec("FAIL" if unemb else "PASS", "cover PDF fonts embedded" + (f"; NOT embedded: {sorted(unemb)}" if unemb else ""))
        imgs = d[0].get_images(full=True)
        if imgs:
            px_w = imgs[0][2]
            dpi = px_w / (r.width / 72)
            rec("PASS" if dpi >= 299 else "FAIL", f"cover resolution {dpi:.0f} DPI")
        rec("INFO", "confirm spine and total width against KDP's cover calculator for the final page count")
    elif pages:
        rec("WARN", "no cover_paperback.pdf; run build_cover.py after the interior is final")


def check_research(book, sections):
    src = book.root / "research" / "sources.md"
    fc = book.root / "research" / "fact_check.md"
    src_text = src.read_text(encoding="utf-8") if src.exists() else ""
    if not src.exists():
        rec("FAIL", "research/sources.md missing")
    if not fc.exists():
        rec("FAIL", "research/fact_check.md missing")
    else:
        t = fc.read_text(encoding="utf-8")
        ok_n, soft_n, cut_n = (t.count(k) for k in ("✅", "⚠", "❌"))
        open_items = len(re.findall(r"\bTODO\b|\bUNVERIFIED\b|\?\?", t))
        rec("FAIL" if open_items else "PASS",
            f"fact-check log: {ok_n} verified, {soft_n} softened, {cut_n} removed"
            + (f", {open_items} open items (TODO/UNVERIFIED)" if open_items else ""))
    missing, no_url, total = [], 0, 0
    for s in sections:
        text = s["path"].read_text(encoding="utf-8")
        for m in re.finditer(r"^\[\^[^\]]+\]:\s*(.+)$", text, re.M):
            total += 1
            urls = re.findall(r"https?://[^\s)>\]]+", m.group(1))
            if not urls:
                no_url += 1
            for u in urls:
                u = u.rstrip(".,;")
                if u not in src_text:
                    missing.append(f"{s['path'].name}: {u}")
    rec("FAIL" if missing else "PASS", f"{total} footnotes; every cited URL is in research/sources.md"
        + (f"; missing: {missing[:5]}" if missing else ""))
    if no_url:
        rec("WARN", f"{no_url} footnotes have no URL; check by hand that each matches a source in sources.md")


def check_style(sections):
    hits = []
    words = 0
    for s in sections:
        for ln, line in enumerate(s["path"].read_text(encoding="utf-8").splitlines(), 1):
            words += len(re.findall(r"[A-Za-z']+", line))
            low = line.lower()
            for b in BANNED:
                if b in low:
                    hits.append(f"{s['path'].name}:{ln} '{b}'")
    rec("WARN" if hits else "PASS", "no banned AI-tell phrases" + (f"; {len(hits)} hits: {hits[:8]}" if hits else ""))
    rec("INFO", f"manuscript word count ~{words:,} (~{words / 275:.0f} pages at 275 words/page, 6x9)")


def check_upload_sheet(book):
    p = book.root / "KDP_upload_sheet.md"
    if not p.exists():
        rec("FAIL", "KDP_upload_sheet.md missing")
        return
    t = p.read_text(encoding="utf-8")
    need = {"AI disclosure": r"AI[- ]generated", "keywords": r"(?i)keyword", "description": r"(?i)description",
            "categories": r"(?i)categor", "pricing": r"(?i)royalt"}
    miss = [k for k, rx in need.items() if not re.search(rx, t)]
    rec("FAIL" if miss else "PASS", "upload sheet has AI disclosure, keywords, description, categories, pricing"
        + (f"; missing {miss}" if miss else ""))
    bad = [w for w in ("bestselling", "best-selling", "award-winning", "#1") if w in t.lower()]
    if bad:
        rec("WARN", f"upload sheet contains {bad}: only allowed if literally true")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--no-previews", action="store_true")
    args = ap.parse_args()
    book = Book(args.book)
    build = book.build_dir
    sections = book.sections()
    pages = check_interior(book, build, not args.no_previews)
    check_epub_file(build)
    check_covers(book, build, pages)
    check_research(book, sections)
    check_style(sections)
    check_upload_sheet(book)
    for level, msg in results:
        print(f"[{level}] {msg}")
    fails = sum(1 for lv, _ in results if lv == "FAIL")
    warns = sum(1 for lv, _ in results if lv == "WARN")
    print(f"\n{fails} FAIL, {warns} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
