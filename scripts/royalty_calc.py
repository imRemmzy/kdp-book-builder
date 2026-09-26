#!/usr/bin/env python3
"""KDP royalty arithmetic for the upload sheet (Amazon.com, USD). Rates as of September 2026: verify at runtime
(references/kdp_specs.md section 4) and pass overrides if KDP has changed them.

Usage:
    python royalty_calc.py --ebook 4.99 --epub-mb 1.2
    python royalty_calc.py --paperback 12.99 --pages 164 --trim 6x9 [--ink black]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import is_large_trim, trim_size  # noqa: E402


def print_cost(pages, large, ink):
    if ink == "black":
        return (2.84 if large else 2.30) if pages <= 108 else 1.00 + pages * (0.017 if large else 0.012)
    if ink == "standard-color":
        if pages < 72:
            raise SystemExit("Standard colour needs 72+ pages")
        return 1.00 + pages * (0.0402 if large else 0.0255)
    if ink == "premium-color":
        return (4.20 if large else 3.60) if pages <= 40 else 1.00 + pages * (0.08 if large else 0.065)
    raise SystemExit(f"unknown ink {ink}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ebook", type=float, help="eBook list price (USD)")
    ap.add_argument("--epub-mb", type=float, default=1.0, help="converted file size in MB (for delivery cost)")
    ap.add_argument("--delivery-per-mb", type=float, default=0.15)
    ap.add_argument("--band70", default="2.99-12.99", help="list-price range eligible for 70%%")
    ap.add_argument("--public-domain", action="store_true", help="primarily public-domain content (35%% only)")
    ap.add_argument("--paperback", type=float, help="paperback list price (USD)")
    ap.add_argument("--pages", type=int)
    ap.add_argument("--trim", default="6x9")
    ap.add_argument("--ink", default="black", choices=["black", "standard-color", "premium-color"])
    a = ap.parse_args()

    if a.ebook is not None:
        lo, hi = (float(x) for x in a.band70.split("-"))
        r35 = 0.35 * a.ebook
        print(f"eBook at ${a.ebook:.2f}")
        print(f"  35% option: ${r35:.2f} per sale")
        if a.public_domain:
            print("  70% option: not available for public-domain content")
        elif lo <= a.ebook <= hi:
            delivery = a.epub_mb * a.delivery_per_mb
            r70 = 0.70 * a.ebook - delivery
            print(f"  70% option: 0.70 x {a.ebook:.2f} - delivery ({a.epub_mb:.2f} MB x ${a.delivery_per_mb}) = ${r70:.2f}"
                  " per sale (in 70% territories)")
        else:
            print(f"  70% option: not available (price must be ${lo:.2f}-${hi:.2f})")
    if a.paperback is not None:
        if not a.pages:
            raise SystemExit("--pages is required for paperback")
        w, h = trim_size(a.trim)
        large = is_large_trim(w, h)
        cost = print_cost(a.pages, large, a.ink)
        rate = 0.60 if a.paperback >= 9.99 else 0.50
        roy = rate * a.paperback - cost
        print(f"Paperback at ${a.paperback:.2f}, {a.pages} pages, {a.trim} ({'large' if large else 'regular'} trim), {a.ink} ink")
        print(f"  printing cost ${cost:.2f}")
        print(f"  Amazon royalty: {rate:.0%} x {a.paperback:.2f} - {cost:.2f} = ${roy:.2f} per sale")
        print(f"  minimum list price at 50%: ${cost / 0.50:.2f}; at 60% (needs $9.99+): ${max(9.99, cost / 0.60):.2f}")
        print(f"  Expanded Distribution: 40% x {a.paperback:.2f} - {cost:.2f} = ${0.40 * a.paperback - cost:.2f}")
        if roy <= 0:
            print("  WARNING: royalty is zero or negative at this price")


if __name__ == "__main__":
    main()
