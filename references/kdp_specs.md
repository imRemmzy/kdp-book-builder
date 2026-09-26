# KDP technical specs

Figures below were checked against KDP's help pages in September 2026. KDP changes these without much notice, so **re-check the linked page at runtime** before quoting a number to the user or baking it into a build. If a page disagrees with this file, trust the page and pass the new figure to the scripts with the matching command-line flag.

## Contents
1. Paperback interior (trim, margins, gutter, page counts)
2. Paperback cover (wrap formula, spine, barcode)
3. eBook file and cover
4. Royalties and printing cost
5. Metadata limits
6. Account and title limits

---

## 1. Paperback interior

Source: https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6 (Set trim size, bleed and margins)

**Common trim sizes (inches):** 5 × 8, 5.06 × 7.81, 5.25 × 8, 5.5 × 8.5, 6 × 9 (most common for non-fiction and fiction), 6.14 × 9.21, 6.69 × 9.61, 7 × 10, 7.44 × 9.69, 7.5 × 9.25, 8 × 10, 8.25 × 6, 8.25 × 8.25, 8.5 × 8.5, 8.5 × 11 (activity books, workbooks, large-print puzzle books).

**Large trim** = wider than 6.12" or taller than 9". It costs more to print (see section 4).

**Page count:** 24 minimum, 828 maximum for black ink on white or cream paper (other ink/paper combos have different ranges; check the page). A manuscript under 24 printed pages should be eBook-only.

**Inside margin (gutter) by page count:**

| Page count | Inside margin |
|---|---|
| 24–150 | 0.375" |
| 151–300 | 0.5" |
| 301–500 | 0.625" |
| 501–700 | 0.75" |
| 701–828 | 0.875" |

These are minimums. `build_interior_pdf.py` adds 0.125" of comfort on top by default (`--gutter-extra`) because text that hugs the minimum reads badly near the spine.

**Outside, top and bottom margins:** at least 0.25" without bleed, at least 0.375" with bleed. The script defaults to 0.6" outside, 0.7" top and 0.75" bottom so running heads and page numbers sit comfortably inside the minimums.

**Bleed:** 0.125" added to the top, bottom and outside edges. Use bleed only when an image or colour block must run off the page edge. Choosing bleed changes the page size KDP expects (for 6 × 9 with bleed: 6.125 × 9.25).

**Fonts:** all fonts must be embedded in the PDF. The script only uses TrueType fonts it embeds itself; `check_package.py` fails the build if any font is not embedded.

**Images:** 300 DPI or higher at printed size. Grayscale is safest for black-ink interiors; colour images print as grayscale anyway.

**Blank pages:** KDP allows blank pages but flags long runs of them. The script inserts at most one blank page before a chapter so every chapter opens on a right-hand (odd) page, and pads the final count to an even number.

## 2. Paperback cover

Source: https://kdp.amazon.com/en_US/help/topic/G201953020 (Create a paperback cover). KDP's cover calculator and template generator: https://kdp.amazon.com/cover-calculator

**Formula:**
- Cover width = bleed + back width + spine width + front width + bleed
- Cover height = bleed + trim height + bleed
- Bleed = 0.125"

**Spine width per page:**

| Paper | Inches per page |
|---|---|
| White (black ink) | 0.002252 |
| Cream (black ink) | 0.0025 |
| Standard colour | 0.002252 |
| Premium colour | 0.002347 |

Worked example: 6 × 9, 120 pages, white → spine 0.2702"; width 0.125 + 6 + 0.2702 + 6 + 0.125 = 12.5202"; height 9.25".

**Spine text:** only for books over 79 pages (KDP's own Cover Creator requires 80+). Keep at least 0.0625" between spine text and each spine fold. Spine text reads top-to-bottom (rotated 90° clockwise) for US/UK books.

**Safe zone:** keep text and important art at least 0.125" inside the trim lines (the script uses 0.25" to be safe).

**Barcode:** KDP prints a barcode in the lower right of the back cover if you leave it free. Keep a 2" × 1.2" area clear, 0.25" in from the spine fold and bottom trim edge (verify on the cover page above; KDP has described this box consistently for years).

**File:** a single PDF, 300 DPI minimum, 650 MB maximum (40 MB or less recommended). Front, spine and back in one spread. No crop marks.

Always re-run the numbers against KDP's cover calculator for the **final** page count. The page count changes whenever the manuscript changes, and so does the spine.

## 3. eBook

Sources: https://kdp.amazon.com/en_US/help/topic/G200645690 (eBook cover), https://kdp.amazon.com/en_US/help/topic/G200634390 (supported eBook formats)

**Manuscript:** EPUB is accepted directly (as are DOCX and KPF). Reflowable EPUB 3 with a navigation document is the target. Avoid fixed font sizes in CSS so readers can resize text; use `em` and percentages.

**Cover image:**
- Ideal 2560 px tall × 1600 px wide (1.6:1)
- Minimum 1000 × 625 px; maximum 10,000 px on either side
- JPEG or TIFF, RGB, under 50 MB
- The eBook cover is uploaded separately from the EPUB. The EPUB should still embed a cover image so it displays in readers.

**Preview tool:** Kindle Previewer (free desktop app from Amazon) shows how the EPUB will look on Kindle devices. Recommend the user opens the EPUB in it before uploading.

## 4. Royalties and printing cost

### eBook
Sources: https://kdp.amazon.com/en_US/help/topic/G200644210 (eBook royalties), https://kdp.amazon.com/en_US/help/topic/G200634560 (list price requirements)

- **70% option:** list price $2.99–$12.99 on Amazon.com (the ceiling was $9.99 for years and was raised; confirm on the list-price page), book must not be primarily public-domain content, applies in "70% territories". Royalty = 70% × (list price − VAT) − delivery cost. US delivery cost has long been $0.15 per MB of the converted file (KDP quotes an average of about $0.06 per unit). Verify both on the pricing page.
- **35% option:** list price $0.99 (up to $2.99 for large files) to $200 on Amazon.com; no delivery cost. Public-domain books only get 35%.
- Use `royalty_calc.py` for the arithmetic.

### Paperback
Sources: https://kdp.amazon.com/en_US/help/topic/G201834330 (paperback royalty), https://kdp.amazon.com/en_US/help/topic/G201834340 (printing cost)

- Royalty rate on Amazon marketplaces: **60% of list price for books priced at $9.99 or more; 50% below $9.99** (US figures). Royalty = rate × list price − printing cost.
- Expanded Distribution: 40% − printing cost.

**US printing cost (Amazon.com, USD):**

| Ink | Pages | Regular trim | Large trim |
|---|---|---|---|
| Black | 24–108 | $2.30 flat | $2.84 flat |
| Black | 110–828 | $1.00 + $0.012/page | $1.00 + $0.017/page |
| Standard colour | 72–600 | $1.00 + $0.0255/page | $1.00 + $0.0402/page |
| Premium colour | 24–40 | $3.60 flat | $4.20 flat |
| Premium colour | 42–828 | $1.00 + $0.065/page | $1.00 + $0.08/page |

Minimum list price = printing cost ÷ royalty rate.

## 5. Metadata limits

Sources: https://kdp.amazon.com/en_US/help/topic/G201097560 (title/subtitle), https://kdp.amazon.com/en_US/help/topic/G201298500 (keywords), https://kdp.amazon.com/en_US/help/topic/G200652170 (categories)

- **Title + subtitle:** combined under 200 characters. The subtitle must appear on the cover if entered, and the cover title must match the metadata title.
- **Description:** up to 4,000 characters (the long-standing form limit; the guidelines page doesn't restate it, so check the form). Limited HTML is accepted: `<b>`, `<i>`, `<u>`, `<br>`, `<p>`, `<h4>`–`<h6>`, `<ul>`, `<ol>`, `<li>`. No links, no contact info, no reviews, no time-sensitive promotions.
- **Keywords:** 7 slots (words or short phrases). The form enforces a per-slot character limit, historically 50. Prohibited: other authors' names, brands, quality claims ("best", "bestseller"), time-sensitive words ("new", "on sale"), Amazon program names ("Kindle Unlimited"), quotation marks, misspellings, and words that just repeat the title or category.
- **Categories:** KDP currently lets you choose up to 3 categories per format (verify on the categories page).
- **Author name:** must match the cover. Pen names are allowed. No invented credentials.

## 6. Account and title limits

- KDP limits how many new titles an account can create. Reports have varied: about 3 new titles per day, and KDP has also stated 10 per format per week. Check https://kdp.amazon.com/en_US/help/topic/G200672390 (content guidelines) and KDP's community notices at runtime and plan releases within whatever is current.
- **AI disclosure** is part of the content guidelines on the same page. See `compliance.md`.
