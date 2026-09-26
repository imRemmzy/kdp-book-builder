# Genre playbooks

Pick the playbook in Phase 2 and follow it through drafting and graphics. Each entry gives research depth, a structure template, sample chapter hooks (patterns, not text to copy), the complaints readers leave most often in that genre, and special rules. Complaints come from recurring themes in low-star reviews across these categories; check the actual reviews of the top competitors in Phase 1 for the specific book, because they're the best source of gaps to fill.

## Contents
1. Practical how-to / beginner guide
2. Reference / explainer
3. History / true stories
4. Health / wellness / finance
5. Children's (picture book / early reader)
6. Activity / puzzle books
7. Guided journals / planners
8. Fiction (short novellas, stories)
9. Quick comparison table

---

## 1. Practical how-to / beginner guide

**Research depth:** heavy. Every instruction has to work.

**Structure template:**
1. Introduction: who this is for, what they'll be able to do, what they need (tools, cost, time).
2. Quick win chapter: the smallest complete result the reader can get today.
3. Core chapters, each: problem → why it happens → steps → worked example → common mistakes → troubleshooting.
4. Going further: next skills, when to get professional help.
5. Appendices: checklists, glossary, resource list with sources.

**Sample hooks:**
- Name the exact frustration: "Your first loaf came out flat and dense. Here's the one step most recipes skip."
- Promise the payoff: "By the end of this chapter you'll have a working budget spreadsheet with your real numbers in it."
- A labelled scenario: "Imagine it's Saturday morning and the bathroom tap is dripping…"

**Common reader complaints to avoid:**
- "Too basic / all information I found free online": add the synthesis, decision guides and troubleshooting that free pages lack.
- Steps that skip something or assume knowledge.
- Padding: long motivational intros before any practical content.
- Outdated screenshots or software steps (date-stamp them).
- No pictures where a diagram would have made it obvious.

**Special rules:** walk through every procedure step by step in your head (or with the user) to check nothing is missing and the order is right. Number steps. Put safety warnings before the step they apply to, not after.

## 2. Reference / explainer

**Research depth:** heavy. Accuracy above everything.

**Structure template:**
1. How to use this book (it's for dipping into, not reading cover to cover).
2. Topic-by-topic sections in a logical order (alphabetical, by category, or simple → complex).
3. Each entry: plain definition → why it matters → key facts with sources → related entries.
4. Summary tables, glossary, strong table of contents. An index helps in print (the builders don't generate one; a detailed TOC plus glossary is the practical substitute).

**Sample hooks:**
- A question the reader has actually asked: "What's the difference between a will and a trust, and do you need both?"
- A counter-intuitive verified fact that the entry explains.

**Common complaints:** errors, outdated facts, shallow entries, poor navigation in the eBook (TOC not linked), tiny unreadable tables on Kindle.

**Special rules:** date-stamp facts. Keep tables narrow (3–4 columns) so they survive Kindle reflow. Consistent entry format throughout.

## 3. History / true stories

**Research depth:** very heavy. Primary sources where possible (archives, contemporary newspapers, official records), secondary sources from historians and university presses.

**Structure template:** chronological (setup → rising events → turning point → aftermath → legacy) or thematic (each chapter one theme across the period). Open with a vivid, verified moment, then pull back to context.

**Sample hooks:**
- Start in the middle of a documented event, with verified details (the date, the weather if recorded, what a surviving letter says).
- A question the chapter answers: "Why did the town vote to flood its own valley?"

**Common complaints:** invented dialogue presented as fact, errors that local readers spot instantly, dry list-of-dates writing, no sources, recycled Wikipedia content.

**Special rules:** no invented dialogue or inner thoughts presented as real. Quote documented words only (short, attributed); otherwise narrate. Mark uncertainty ("According to one account…", "Records disagree on…"). Local history: check names and places against local archives or historical society publications, and be careful with living people and their families.

## 4. Health / wellness / finance

**Research depth:** very heavy. Government health agencies, medical societies, systematic reviews, financial regulators and official consumer-finance guidance.

**Structure template:** explanation of how something works → what the evidence says (with its strength) → general practices most people can consider → warning signs that need a professional → resources.

**Sample hooks:** a common, relatable worry ("You read three articles about breakfast and they all disagreed."), a myth the chapter tests against evidence.

**Common complaints:** preachy tone, unsupported claims, one-size-fits-all advice, fear-mongering, hidden product pitches.

**Special rules:** see `compliance.md` §4. Disclaimer, no individual advice (no dosing, diagnosis, specific legal strategy, or investment picks), "consult a qualified professional" notes. Get the user's agreement to the extra review burden before starting and list every such chapter in the review list. Reassuring, clear tone; describe the strength of evidence honestly.

## 5. Children's (picture book / early reader)

**Research depth:** light to medium (age-appropriate vocabulary, reading-level norms, any factual content in non-fiction picture books).

**Structure template:**
- Picture book (usually 24–32 pages): one short idea per spread, a clear arc (problem → tries → solution), a satisfying last page. Text often under 500 words.
- Early reader: short chapters, repeated high-frequency words, sentence length suited to the level.

**Sample hooks:** a character wanting something small and specific; a repeated refrain that the child anticipates.

**Common complaints:** illustrations inconsistent from page to page (a big problem with AI images), text too long or vocabulary too hard for the stated age, preachy morals, low print quality, age range wrong.

**Special rules:** age-appropriate content only; original characters (no franchise characters or lookalikes). Illustration-led books need consistent art; code-drawn art (shapes, simple characters) keeps consistency but tell the user honestly about the style limits. Picture books usually need colour interiors (premium colour costs much more to print; see `kdp_specs.md` §4) and often full bleed. KDP asks for age range and grade level: fill them in honestly.

## 6. Activity / puzzle books

**Research depth:** light (theme vocabulary, clue accuracy, difficulty norms). Crossword clues and trivia are factual claims and must be correct.

**Structure template:** short "how to play" page for each puzzle type → themed sections with a difficulty curve (easy → medium → hard) → answer key at the back, clearly labelled with puzzle numbers. Large print (8.5 × 11 trim, bigger grids) for seniors-focused books.

**Sample hooks:** section intros that set the theme in one or two lines; a "warm-up" puzzle that everyone can finish.

**Common complaints:** unsolvable or ambiguous puzzles, wrong answer keys, print too small, puzzles bleeding into the gutter, repeated puzzles, no difficulty progression, flimsy "bonus" pages.

**Special rules:** generate with `build_puzzles.py`, which verifies every puzzle (unique sudoku solutions, every word-search word found exactly once, mazes solvable, crossword letters consistent). Never hand-write a puzzle grid. Keep grids inside the text block so nothing falls into the gutter.

## 7. Guided journals / planners

**Research depth:** medium, for the introduction and the reasoning behind the prompts (e.g. evidence on gratitude journaling or habit tracking, cited).

**Structure template:** short intro (why this works, how to use it, cited) → sections of prompts or layouts that build on each other → reflection pages at milestones. Prompts vary in type (recall, planning, reflection, list, rating).

**Sample hooks:** each section opens with a short paragraph that explains its purpose.

**Common complaints:** "just blank lines", repetitive prompts, paper too thin for pens (a physical-copy issue: tell the user to check the proof), too few pages for the stated duration, dated pages that go stale.

**Special rules:** must add real value beyond blank pages; KDP's quality guidelines target low-content books with little substance. Use undated layouts unless the user wants a specific year.

## 8. Fiction (short novellas, stories)

**Research depth:** medium (setting, era, jobs, technology, places: whatever the story leans on).

**Structure template:** before drafting, produce a plot outline (inciting incident, escalating stakes, midpoint, crisis, climax, resolution), character sheets (want, need, flaw, voice), and a scene list with each scene's purpose. Chapters end on a question, a turn or a decision.

**Sample hooks:** open in a scene with a character wanting something; an odd, specific detail; a line of dialogue that implies conflict.

**Common complaints:** flat characters, info-dumps, sagging middles, generic prose ("AI voice"), unresolved endings sold as complete, continuity errors.

**Special rules:** original characters and worlds only: no fan fiction, no characters that are recognisable knock-offs. Real places are fine; real living people shouldn't appear as characters. Keep a continuity sheet (names, ages, dates, eye colours) and check against it in Phase 5.

## 9. Quick comparison

| Genre | Research depth | Structure | Engagement focus | Special rules |
|---|---|---|---|---|
| Practical how-to / beginner guide | Heavy | Problem → steps → examples → troubleshooting | Quick wins early, checklists | Test that steps are complete and in order |
| Reference / explainer | Heavy | Topic-by-topic, strong TOC | Clear definitions, summaries, visuals | Accuracy above all; date-stamp facts |
| History / true stories | Very heavy | Chronological or thematic narrative | Narrative tension, vivid verified detail | No invented dialogue presented as real |
| Health / wellness / finance | Very heavy | Explanations + general practices | Reassuring, clear tone | Disclaimers; no individual advice; flag for user review |
| Children's | Light–medium | Short text per page, illustration-led | Rhythm, repetition, age-appropriate vocabulary | Age-appropriate only; original characters |
| Activity / puzzle | Light | Themed sections, difficulty curve, answer keys | Variety, difficulty progression | Verify every puzzle is solvable |
| Guided journals / planners | Medium | Short intro + meaningful prompts/layouts | Prompts that feel personal and purposeful | Genuine value, not blank pages |
| Fiction | Medium | Plot outline, character sheets, scene list | Hooks, stakes, chapter-end pulls | Original characters and worlds only |
