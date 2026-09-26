# KDP Book Builder

A [Claude](https://claude.com/claude-code) **skill** that turns a topic idea (or no idea at all) into a complete, honest, upload-ready Amazon KDP package:

- A researched and fact-checked manuscript (10–200 pages)
- A Kindle EPUB
- A print-ready paperback interior PDF
- An eBook cover and a full paperback cover wrap
- Puzzle pages (for activity/puzzle books)
- A metadata/upload sheet with the AI-disclosure answers
- A source list with a fact-check log

The skill runs a one-person, honest publishing operation: pick a book worth writing, research it properly, write it well, design it, and hand over a package you upload to KDP yourself. It never logs in to KDP, creates accounts, or uploads on your behalf.

## Layout

| Path | What's in it |
|------|--------------|
| `SKILL.md` | The skill instructions Claude follows. |
| `references/` | Compliance rules, genre notes, idea scoring, KDP specs, engagement guidance. |
| `scripts/` | Python builders for the EPUB, interior PDF, cover, puzzles, royalty calc, and a package checker. |
| `assets/` | Templates (book JSON, report/upload sheets) and bundled DejaVu/STIX fonts. |

## Installing as a skill

Clone or symlink this repo into your personal skills folder so Claude Code can discover it:

```bash
# Windows (PowerShell)
git clone https://github.com/imRemmzy/kdp-book-builder.git "$env:USERPROFILE\.claude\skills\kdp-book-builder"
```

```bash
# macOS / Linux
git clone https://github.com/imRemmzy/kdp-book-builder.git ~/.claude/skills/kdp-book-builder
```

## Fonts

`assets/fonts/` bundles the DejaVu and STIX font families under their own licenses (`LICENSE_DEJAVU`, `LICENSE_STIX`).
