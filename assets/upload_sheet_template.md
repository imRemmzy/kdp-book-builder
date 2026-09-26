# KDP upload sheet: [Title]

Everything below is ready to paste into the KDP form. Checked against KDP's help pages on [date]; KDP changes limits and rates, so glance at each field's help link as you go. You upload and submit; nothing here has been submitted for you.

## Book details

| Field | Value |
|---|---|
| Language | English |
| Book title | [exactly as on the cover] |
| Subtitle | [exactly as on the cover, or blank] |
| Series | [name and number, or "none"] |
| Edition number | [1, or blank] |
| Author (primary) | [pen name, exactly as on the cover] |
| Contributors | [none unless real people contributed] |

Title + subtitle: [N] characters (limit: under 200).

## Description

Paste into the description box (HTML accepted: `<b> <i> <u> <br> <p> <h4>-<h6> <ul> <ol> <li>`). [N] characters (limit 4,000). No reviews, no quotes, no claims that aren't literally true.

```html
<p>...</p>
```

## Publishing rights
"I own the copyright and I hold the necessary publishing rights." [Or the public-domain option if applicable, with notes.]

## Keywords (7 slots)

Real phrases readers type into Amazon search. No brands, no other authors, no "best"/"new", no words that only repeat the title.

1. 
2. 
3. 
4. 
5. 
6. 
7. 

## Categories

Pick up to [3, verify] in the form. Suggested, most specific first:
1. [Category path] — why
2. 
3. 

## Age and grade range
[Only for children's/young-adult books; otherwise leave blank.]

## AI-generated content disclosure

KDP asks whether the book contains AI-generated text, images, or translations. **Answer honestly: it's required, KDP can block books or suspend accounts over undisclosed AI content, and disclosed AI content is allowed.** KDP counts content as AI-generated even if you edited it substantially afterwards.

| Question | Answer | Why |
|---|---|---|
| Text | [Yes] | [Claude drafted the manuscript; your edits don't change this answer] |
| Images | [Yes / No] | [e.g. cover and interior graphics were designed by Claude and drawn by code] |
| Translations | [No] | [nothing was translated] |

If KDP asks for the tool: [Claude (Anthropic)].

## Paperback settings
| Setting | Value |
|---|---|
| Print ISBN | free KDP ISBN (or your own) |
| Ink and paper | [Black & white interior with white paper] |
| Trim size | [6 x 9 in] |
| Bleed | [No bleed] |
| Cover finish | [Matte / Glossy] — [reason] |
| Manuscript | `build/interior.pdf` ([N] pages) |
| Cover | `build/cover_paperback.pdf` (upload your own cover; built for [N] pages on [white] paper) |

## eBook settings
| Setting | Value |
|---|---|
| Manuscript | `build/[slug].epub` |
| Cover | `build/cover_ebook.jpg` |
| DRM | [your choice; it doesn't stop determined copying and some readers dislike it] |

## Pricing and royalties (Amazon.com)

[Output of royalty_calc.py, with a short explanation.]

- eBook at $[x]: 70% option → $[y] per sale (eligible $2.99–$[12.99, verify]; minus delivery ≈ $0.15/MB). 35% option → $[z].
- Paperback at $[x]: printing $[c]; royalty [50% below $9.99 / 60% at $9.99+] → $[y] per sale; Expanded Distribution → $[z].
- Why this price: [competitor range from Phase 1].

## KDP Select (Kindle Unlimited)

For this book specifically:
- **Pros:** [page-read income from KU readers, promo tools…]
- **Cons:** [90-day eBook exclusivity to Amazon; can't sell the eBook elsewhere…]
- **Suggestion:** [enrol / don't] because [reason].

## Launch checklist (honest version)
- [ ] Open the EPUB in Kindle Previewer and page through it.
- [ ] Order a printed proof copy; check margins, gutter, cover colours and spine alignment with your own eyes.
- [ ] Read the "Personally review before uploading" list in REPORT.md.
- [ ] Ask a few real readers for honest feedback before launch (never pay for or swap reviews).
- [ ] Consider Amazon Ads only after the book page, cover and description are final and a few organic sales show it converts; start with a small daily budget.
- [ ] Release schedule: KDP limits new titles per account (currently [x], verify); plan further books within it.
