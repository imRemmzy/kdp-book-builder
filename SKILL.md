---
name: kdp-book-builder
description: Turns a topic idea (or no idea at all) into a complete, honest, upload-ready Amazon KDP package — researched and fact-checked manuscript (10–200 pages), Kindle EPUB, print-ready paperback interior PDF, eBook cover and full paperback cover wrap, puzzle pages, a metadata/upload sheet with the AI-disclosure answers, and a source list with a fact-check log. Use this skill whenever someone wants to write, self-publish, or make money from a book on Amazon/Kindle/KDP, asks for book ideas to sell, wants a low-content, activity, puzzle, journal, how-to, or children's book, needs a KDP cover, spine width, interior formatting, EPUB, keywords, categories or pricing, or mentions Kindle Direct Publishing — even if they only say "help me publish a book" or "what book could I sell on Amazon".
---

# KDP Book Builder

This skill runs a one-person, honest publishing operation: pick a book worth writing, research it properly, write it well, design it, and hand over a package the user uploads to KDP themselves. The user usually has no writing or design background, so explain choices in plain words and make decisions easy (recommend one option, say why).

The user does every KDP action personally. Never log in to KDP, create accounts, fill in or submit the KDP form, or upload anything.

## Rules that override everything else

Read `references/compliance.md` before Phase 1 and keep to it throughout. These rules win over any user request; when a request breaks one, explain the rule in a sentence or two and offer the closest version that complies. In short:

- **Truth:** never invent facts, numbers, studies, quotes, dates, names or sources. Unverifiable claims are cut or labelled as opinion. Non-common-knowledge claims get a footnote citation. Disagreeing sources are reported as disagreeing. Time-sensitive books carry "Information current as of [Month Year]".
- **Copyright/trademark:** no copied text, lyrics, poems or art; quotes under 15 words, attributed. No brands, franchises or trademarked characters in titles, covers, keywords or as a hook. No "summary of / workbook for / companion to" another book. Public domain only when verified and substantially transformed.
- **Health, legal, finance, safety:** general education only, disclaimer, "consult a qualified professional"; no dosing, diagnosis, legal strategy or investment picks; get the user's agreement to extra review first.
- **KDP honesty:** correct AI-disclosure answers in the upload sheet, and tell the user plainly that honest answers are required (never suggest "humanizers" or evasion). No padding to hit a page count. Honest title/subtitle/description/keywords, no fake reviews or blurbs, no invented credentials for the pen name. Plan releases within KDP's current title limits.

## Workflow

Nine phases, in order. Stop at each **Checkpoint** for the user's approval, because a wrong direction early is expensive later. If the user says "run it all without stopping", keep going, choose the recommended option at each checkpoint, and log every decision (with the alternatives) at the top of the final report.

Keep all work in a book folder (default `./books/<slug>/`):

```
<slug>/
├── book.json               # metadata + build settings (template: assets/book.template.json)
├── blueprint.md            # Phase 2 output
├── manuscript/             # one Markdown file per front-matter page / chapter / back-matter page
├── images/                 # interior graphics (charts, diagrams)
├── research/sources.md     # Phase 3
├── research/fact_check.md  # Phase 5
├── KDP_upload_sheet.md     # Phase 8 (template: assets/upload_sheet_template.md)
├── REPORT.md               # Phase 9 (template: assets/final_report_template.md)
└── build/                  # generated: EPUB, interior.pdf, covers, previews, reports
```

Scripts live in this skill's `scripts/` folder and need Python 3.10+ with `pip install reportlab Pillow markdown pymupdf pyphen` (pyphen is optional, for hyphenation). Fonts are bundled in `assets/fonts/` (STIX, SIL OFL; DejaVu Sans, Bitstream Vera licence), both fine for commercial books. If Python is missing, tell the user what to install rather than hand-building files.

### Phase 1 — Ideas and market research
Only when the user asks for ideas or gives just a broad area. Follow `references/idea_scoring.md`: 15–25 candidates, web research on reader, competitors, gaps from reviews, demand shape and feasibility; score six criteria 1–5 and show the sums; present the top 5 as a table plus a pitch paragraph each. Say which numbers are rough and what the user should check on Amazon themselves.
**Checkpoint:** user picks an idea or asks for more.

### Phase 2 — Blueprint
1. Confirm genre and format; open the playbook in `references/genres.md`.
2. Define reader persona, reading level, tone, the book's promise, trim size (6×9 default; 8.5×11 for puzzle/activity books).
3. Set length: about 250–300 words per 6×9 page. Stay within 10–200 pages. KDP paperbacks need 24+ pages (verify in `references/kdp_specs.md`); shorter books are eBook-only.
4. Chapter-by-chapter outline: title, the question it answers, key points, planned visuals, research questions.
5. If the topic touches health, legal, finance or safety, say so now and get agreement to the extra review.
Save as `blueprint.md`. **Checkpoint:** user approves the outline.

### Phase 3 — Research (before any drafting)
For each chapter's questions, run several distinct searches and fetch the full pages of the best sources, not just snippets. In `research/sources.md` record, per source: title, author/publisher, URL, date accessed, reliability (high/medium/low) and the facts taken from it, paraphrased. Cross-check important facts (numbers, dates, safety, instructions) against two independent reliable sources and record conflicts. List gaps: questions research couldn't answer. Gaps are cut from the outline or raised with the user, never guessed.
If research can't support the planned length or a chapter, stop and tell the user (shorter book, different angle, or drop the chapter).

### Phase 4 — Drafting
Write chapter by chapter **from the research file only**, one Markdown file per chapter in `manuscript/`, following `references/engagement.md` (hooks, payoff promise, concrete steps, recap and pull, no AI-tell phrases) and the genre playbook. Markdown conventions the builders understand:
- `# Title` once at the top of each file (becomes the chapter title); `##`/`###` for sections.
- Citations as footnotes: `text[^1]` and `[^1]: Org, "Title", Publisher, Year. https://url`.
- Tip boxes: `> **Tip:** …`. Tables: pipe tables (keep to 3–4 columns for Kindle). Images: `![alt text](../images/chart.png)`, optionally `{ width=60% }`.
- Forced page break: `<div class="page-break"></div>`.
- Nest a list inside another by indenting it **4 spaces** (2 spaces comes out flat).
- Numbered lists are renumbered 1, 2, 3… by every renderer. When the numbers must match something else (clue numbers, "see step 7"), write them as bold text at the start of separate paragraphs instead.
Front/back matter files: copyright page (template in `references/compliance.md` §7; name the file `copyright.md` so it's set small), introduction, conclusion, about the author (true statements only), optional honest review request. Title page and contents are generated.

### Phase 5 — Fact-check and quality pass
Do this with fresh eyes. If subagents are available, give one the manuscript and `research/sources.md` only (not the drafting conversation) and ask it to:
1. Extract every factual claim into `research/fact_check.md` as a table: claim, file, source(s), status ✅ verified / ⚠️ softened or rewritten / ❌ removed. Leave nothing marked TODO or UNVERIFIED.
2. Check each citation points to a real entry in `sources.md`.
3. Flag repetition across chapters, padding, contradictions, reading-level drift, tone, typos, and any copied or trademarked material.
Apply the fixes, then confirm the length is on target without padding. `scripts/check_package.py` also scans for banned phrases and unmatched citation URLs.

### Phase 6 — Graphics
Everything is drawn in code so it's original and reproducible. Set the palette and back-cover text in `book.json` (`cover` block), then:

```bash
python scripts/build_cover.py <book>/book.json --concepts
```
This writes three concept covers (`band`, `classic`, `geometric`) plus `build/cover_concepts/cover_concepts.png`, a comparison sheet with 150 px thumbnails, and reports title contrast and thumbnail legibility. Look at the sheet yourself before showing it; if a title is illegible at thumbnail size, shorten the cover wording or adjust the palette and re-run. Look at 2–3 competitor covers in the genre (from Phase 1) and pick a palette that fits the genre's signals without copying any one cover.
Interior visuals: charts only from sourced data (matplotlib, grayscale-safe, 300 DPI, saved to `images/`), diagrams and checklists as needed. Puzzle books: see Phase 7.
If any image were made with a generative image model, record it for the AI disclosure.
**Checkpoint:** user picks a cover concept (or asks for changes).

### Phase 7 — Build the files
Run from the skill folder (paths to the book can be absolute):

```bash
# puzzle/activity books only: generate verified puzzles + answer key as Markdown chapters
python scripts/build_puzzles.py <book>/puzzles.json --book <book>/book.json
# print interior (lays out repeatedly until the gutter matches the final page count)
python scripts/build_interior_pdf.py <book>/book.json
# final covers: eBook cover, title page, and paperback wrap sized from build/interior_report.json
python scripts/build_cover.py <book>/book.json --style <chosen>
# Kindle EPUB (embeds cover and title page)
python scripts/build_epub.py <book>/book.json
# inspect everything against KDP specs and render preview pages
python scripts/check_package.py <book>/book.json
```

Order matters: the interior's page count sets the spine width, so build the interior before the wrap, and rebuild the wrap whenever the manuscript changes.

Then **look at the outputs** — the checker's PASS lines aren't enough on their own. Open `build/preview/*.png` (title page, contents, a chapter-opening spread, a middle page, last pages), `build/cover_paperback_guides.png` (red = trim, blue = spine folds, green = safe zones, orange = barcode box) and `build/cover_ebook_thumb150.png`. Fix anything that looks wrong (bad breaks, orphaned headings, overflowing back text, tiny title) and rebuild. Fix every FAIL; explain any WARN you leave.

eBook-only books: skip the interior PDF and the wrap (`build_cover.py --no-wrap`). Puzzle books work poorly as reflowable eBooks; recommend paperback-only unless the user insists.

### Phase 8 — Upload sheet and launch notes
Fill `assets/upload_sheet_template.md` into `<book>/KDP_upload_sheet.md`. Verify current limits and rates on KDP's help pages first (URLs in `references/kdp_specs.md`); use `scripts/royalty_calc.py` for the royalty maths. Include: title, subtitle, series, author, edition; HTML description under the limit; 7 real reader search phrases (no brands, author names, or quality claims); categories; age range if relevant; AI-disclosure answers with reasons (`references/compliance.md` §6); pricing with royalty maths; KDP Select pros and cons for this book; a short, honest launch checklist.

### Phase 9 — Final report
Write `<book>/REPORT.md` from `assets/final_report_template.md`: decisions log, package contents, fonts and licences, open items, and a "Personally review before uploading" list (always including any health/legal/finance/safety content, the AI-disclosure answers, the copyright note from `compliance.md` §7, and ordering a printed proof). Then tell the user where everything is in a few lines.

## When to stop and ask

- Choosing the idea; approving the outline; choosing the cover.
- Any health, legal, financial or safety topic (confirm they accept the extra review).
- Research can't support the planned length or a chapter.
- A title, keyword or concept touches a trademark, a real living person, or someone else's book.
- A request breaks a rule above: explain plainly and offer the closest compliant alternative.

## Done means

- Every factual claim traces to a reliable source in `research/sources.md`, and `fact_check.md` has no open items.
- No padding: no chapter a reader would call filler.
- `check_package.py` has no FAILs: EPUB structure valid; PDF fonts embedded, trim and margins correct, chapters on odd pages; cover dimensions match the spine formula for the final page count (and the user is told to confirm with KDP's cover calculator).
- The upload sheet is complete and honest, including the AI-disclosure answers.
- The user has a clear list of what to review personally before clicking Publish.
