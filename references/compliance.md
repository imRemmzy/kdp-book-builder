# Compliance rules in detail

These rules sit above everything else in the skill, including what the user asks for. When a request conflicts with one, explain the rule in plain words, say why it exists (usually: it protects the user's KDP account or exposes them to legal risk), and offer the closest version of the request that does comply. Don't lecture; one or two sentences is enough.

## Contents
1. Truthfulness and sourcing
2. Copyright, trademarks and other people's books
3. Public domain
4. Health, legal, financial and safety topics
5. Real people
6. AI disclosure (KDP)
7. Copyright notice for AI-assisted books
8. Honest metadata, reviews, and author name
9. Quality and volume
10. Things the skill never does

---

## 1. Truthfulness and sourcing

**Why it matters:** readers act on non-fiction. A made-up statistic in a gardening book kills plants; in a health book it can hurt someone. It also gets books pulled and reviewed badly, which ends a pen name's career.

- Never invent facts, statistics, studies, quotes, dates, names or sources. A claim that research didn't verify is cut, or rewritten as clearly labelled opinion ("In my view…", "A common rule of thumb, not a measured figure, is…").
- "Common knowledge" means a typical reader of this book would already know it and no reasonable person would dispute it (water freezes at 0 °C; there are seven days in a week). Everything else gets a citation.
- Citation format: Markdown footnotes (`[^1]`) in each chapter. The EPUB builder puts them at the end of each chapter with back-links; the print builder collects them into numbered endnotes grouped by chapter. Every footnote names the source so a reader could find it: author or organisation, title, publisher or site, year, and URL for web sources.
- Source preference, best first: government and intergovernmental bodies, peer-reviewed papers and systematic reviews, official documentation and standards bodies, university extension services, established reference works, major newspapers and magazines with editorial standards. Avoid content farms, AI-written SEO pages, affiliate "best X" listicles, and forums (forums only for clearly labelled anecdotes, e.g. "one grower on a gardening forum reported…").
- Cross-check numbers, dates, safety information and step-by-step instructions against **two independent** reliable sources. "Independent" means one isn't just repeating the other.
- When reliable sources disagree, say so in the text ("Estimates range from X [^3] to Y [^4]"), rather than silently picking one.
- Time-sensitive facts (prices, laws, statistics, software steps, regulations) get "Information current as of [Month Year]" on the copyright page, and in the text where it matters.

## 2. Copyright, trademarks and other people's books

**Why:** infringement claims get books removed and can close a KDP account; they can also cost money.

- Never reproduce copyrighted text, song lyrics, poems or artwork. Quotes from sources: under 15 words, attributed, and only when the exact wording matters. Paraphrase everything else in original words and structure (not a synonym swap of the source's sentences).
- No trademarked characters, brands, logos or franchises in titles, subtitles, covers, keywords or content used as a selling hook. Mentioning a product generically in passing is fine when it's genuinely needed ("a spreadsheet program such as a free office suite"), but a book about "Minecraft builds" or "Instant Pot recipes" leans on someone else's mark. Offer a generic framing instead ("block-building games", "electric pressure cooker recipes") and tell the user why.
- Never produce "summary of", "workbook for", "study guide to", or "companion to" books based on someone else's book. KDP's content guidelines restrict companion books based on copyrighted works, reader complaints are common, and they invite infringement claims. Offer an original book on the same topic instead.
- No knockoff covers: don't imitate a specific competitor's cover layout, illustration or type treatment closely enough to be confused with it. Matching genre signals (a thriller looks dark and bold) is fine.

## 3. Public domain

- US rule of thumb: works published in the US before 1931 are in the public domain as of 2026 (each 1 January another year's works enter). **Verify the current cutoff at runtime** (search "public domain day [current year]") and note that rules differ outside the US, for unpublished works, and for sound recordings.
- Confirm the status of the specific edition used. A modern translation, annotated edition or newly illustrated edition of an old work has its own copyright.
- Public-domain content must be substantially transformed or annotated to add real value (new introduction, notes, modernised text with commentary, curated selection with context). KDP rejects undifferentiated copies of free public-domain books and may ask for proof of status. Public-domain books only earn the 35% eBook royalty.

## 4. Health, legal, financial and safety topics

**Why:** these books are where readers can be harmed and where KDP and readers are least forgiving.

- Before starting, tell the user this topic needs extra review from them (and ideally from a qualified professional) and get their agreement. Record it in the final report.
- General educational information only. Never give dosing, diagnosis, treatment plans, specific legal strategy for a situation, or investment recommendations (no "buy X", no allocation percentages for the reader).
- Include a clear disclaimer on the copyright page and near the start of the book. Template (adapt to the topic):

  > This book provides general information for educational purposes only. It is not a substitute for advice from a qualified [doctor / lawyer / financial adviser / licensed professional] who knows your situation. Always consult one before acting on anything in this book. The author and publisher are not responsible for any outcome from using the information here. Information is current as of [Month Year].

- Safety information (chemicals, electricity, food preservation, power tools, animals, outdoor survival) comes only from authoritative sources and is quoted as the source states it, never loosened.
- Flag every chapter in this territory in the final report's "Personally review before uploading" list.

## 5. Real people

- Nothing defamatory: no unverified allegations, no speculation presented as fact about identifiable real people.
- Avoid titles or concepts built around a living person (celebrity guides, unofficial biographies) unless the user understands the risk and the content is strictly sourced public record. Ask first.
- Invented anecdotes are labelled as hypothetical ("Imagine you…", "Consider a gardener who…"). Never present an invented story as a real event, and never attach an invented quote to a real person.

## 6. AI disclosure (KDP)

Source: KDP Content Guidelines, https://kdp.amazon.com/en_US/help/topic/G200672390 — re-read at runtime.

KDP's definitions (as of September 2026):
- **AI-generated**: text, images or translations created by an AI-based tool. This still counts as AI-generated **even if the publisher substantially edited it afterwards**.
- **AI-assisted**: content the publisher created themselves, then used AI to edit, refine, error-check or improve; or brainstorming with AI before writing it themselves. KDP does not require disclosure of AI-assisted content.

What this means for books made with this skill:
- **Text:** Claude drafts the manuscript, so the text is AI-generated → answer **Yes** for text. This stays Yes even after the user edits heavily. Only if the user wrote the text themselves and Claude merely edited would it be AI-assisted; don't assume that — ask.
- **Images:** graphics drawn procedurally by the skill's scripts (covers, ornaments, puzzle grids, charts from data) are produced by code Claude wrote to the user's spec, not by an image-generation model. KDP's wording doesn't cleanly cover this case. The honest, lowest-risk answer is **Yes** for images whenever Claude designed them, and say so in the upload sheet with the reason. If a generative image model was used anywhere, it's unambiguously Yes. If the user supplied their own photos or artwork, those are theirs.
- **Translations:** Yes if Claude translated any text; otherwise No.
- The upload sheet must list each answer and the reason. Tell the user plainly: answering honestly is required, KDP can block books or suspend accounts over undisclosed AI content, and disclosed AI content is allowed.
- Never suggest "humanizer" tools, detector-evasion rewriting, or any trick to avoid disclosure. If asked, decline and explain that disclosure is what keeps the account safe.

## 7. Copyright notice for AI-assisted books

Put an accurate copyright page in every book:

```
Copyright © [Year] [Author or pen name]
All rights reserved. [Optional: No part of this book may be reproduced without permission, except brief quotations in reviews.]
[Disclaimer if the topic needs one]
Information current as of [Month Year].
[Font credits, e.g. "Set in STIX (SIL Open Font License) and DejaVu Sans (Bitstream Vera License)."]
[Optional ISBN line if the user has their own ISBN; KDP supplies a free ISBN for paperbacks otherwise]
```

Tell the user (once, in the final report, without drama): under current US law and US Copyright Office guidance, material generated purely by AI generally can't be protected by copyright; human authorship is required. Their own writing, substantive edits, and creative selection and arrangement of material are what can be protected, so the more of the book is genuinely theirs, the stronger their claim. This is general information, not legal advice.

## 8. Honest metadata, reviews and author name

- Title, subtitle, description and keywords must describe the book as it is. No keyword stuffing in the title or subtitle, no promises the book doesn't keep ("master X in 7 days" for a 30-page primer).
- No "bestselling", "award-winning", "#1", "acclaimed" unless literally true and verifiable.
- No reviews, testimonials, "praise for this book" blurbs, or endorsements attributed to anyone. The back cover uses a description of the book, not quotes.
- Pen names are fine. Never add credentials (Dr., PhD, RN, CPA, "certified", "expert", "nutritionist") the user doesn't actually hold, and don't imply expertise in the About the Author. A pen-name bio can be generic and true ("[Name] writes practical guides for beginners who want clear, sourced answers.").

## 9. Quality and volume

- No filler, padding, repetition or thin content written to reach a page count. If research supports 40 good pages, the book is 40 pages. Tell the user, and suggest eBook-only or a lower price, rather than padding. KDP's quality guidelines cover "disappointing content" and it's the fastest route to one-star reviews.
- Guided journals and planners must contain meaningful guidance (prompts, frameworks, instructions), not mostly blank or repeated pages.
- Volume: see `kdp_specs.md` §6. When the user plans a series or multiple books, schedule releases within KDP's current title-creation limit and say so.

## 10. Things the skill never does

- Log in to KDP, create accounts, fill in or submit the KDP form, or upload files. The user does all of that.
- Write reviews, ask for reviews in exchange for anything, or set up review swaps.
- Enrol the user in anything or accept terms on their behalf.
