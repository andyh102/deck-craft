# DeckCraft

Turn a plain Markdown file into a polished, presentable slide deck — one
self-contained HTML file, no server, no dependencies beyond Python 3's
standard library. 31 slide types, 8 built-in visual themes, optional
PowerPoint/PDF export, all offline.

**This is a universal AI skill, not a Claude-only plugin.** It's just a folder:
a plain-English instructions file (`SKILL.md`) plus a pure-stdlib Python
script (`build.py`) that does the actual rendering. Any AI assistant that can
read a file and run Python can use it — see "Use it with any AI tool" below.

## Quickstart (no AI required)

```bash
python3 build.py example-deck.md          # writes example-deck.html
python3 build.py template-deck.md my.html # or start from the blank template
```

Open the resulting `.html` file (double-click it) — arrow keys or the on-screen
buttons navigate, and the "↓ PowerPoint" / "↓ PDF" buttons export a copy.

Write your own deck as Markdown (see `SKILL.md` for the full syntax and the
31 slide types), drop any images into an `assets/` folder next to it, then
build the same way.

## Use it with any AI tool

Point your assistant at this folder and ask it to build you a deck — the
instructions in `SKILL.md` are written for an AI to follow, not just a human.

- **Claude Code / Claude Desktop:** copy or symlink this folder into
  `~/.claude/skills/deck-craft` and it's picked up automatically as a skill.
- **Cursor, Windsurf, or any AI-native IDE:** open this folder as (or inside)
  your project and ask: *"Read SKILL.md and build me a deck about ­­­­­\_\_\_."*
- **ChatGPT, Claude.ai, or any chat tool with file upload:** upload the whole
  folder (or this zip) and ask the same thing — the assistant reads
  `SKILL.md`, drafts a `deck.md`, and runs `build.py` for you (or hands you
  the Markdown to run yourself if it can't execute code).
- **Any other agent:** the only requirement is "can read text files and run a
  Python 3 script." That's the whole contract.

No API keys, no accounts, no network calls — everything happens locally.

## Kick-off prompt

Once your assistant can see this folder, paste this in and fill the brackets:

```
Read SKILL.md in this folder, then build me a slide deck.

Topic: [what the deck is about]
Audience: [who it's for, and what they should do after]
Length: [tight ~8 slides, or a fuller ~14]
Style: [a theme name like modern or warm — or describe the mood]

Here's what I have so far:
[paste notes, a doc, or key numbers]
```

It'll draft a `deck.md` for you to review before running `build.py`.

**Tips for a better deck:**

1. **Paste your raw material first** — notes, a doc, data, a ticket. Richer
   input beats a short description; let the assistant structure it.
2. **Say who it's for and what they should do after** — that decides the tone
   and which recipe (review, pitch, kickoff, retro) fits.
3. **Give real numbers, not placeholders** — the assistant can't invent your
   KPIs, dates, or names.
4. **Name a rough length** — "tight" or "fuller" is enough; open-ended briefs
   tend to sprawl.
5. **Describe the mood if you don't know a theme by name** — "dark and techy"
   or "warm and personal" works as well as the theme id.
6. **Review the drafted `deck.md` before building** — it's plain text, so
   tweaking it is faster than regenerating.

## Themes

Set `theme:` in a deck's front matter. `accent:` / `font:` still override just
those two tokens on top of whichever theme you pick.

| theme | look |
|---|---|
| `modern` (default) | dark throughout, one accent blue, greyscale otherwise |
| `professional` | light navy-on-oat, serif headings, gold rule under titles |
| `dark` | dark surface, teal accent, cards lift with fill not shadow |
| `light` | no colour at all, huge margins, light-weight type |
| `editorial` | warm cream, serif display, magazine-style pull quotes |
| `technical` | monospace headings, teal accent, amber for outliers |
| `bold` | pure black, full-bleed yellow-green type, red colour-flip |
| `warm` | warm tan, serif display, terracotta accent, rounded corners |

## What's in here

| file | purpose |
|---|---|
| `SKILL.md` | full instructions — slide types, syntax, themes, workflow |
| `build.py` | the builder (Markdown → HTML). Standard library only. |
| `dashboard.py` | optional local dashboard of decks you've built (`~/.deck-craft/library.json`, never leaves your machine) |
| `library.py` | local build-history index used by the dashboard |
| `example-deck.md` | a complete deck exercising all 31 slide types |
| `template-deck.md` | a blank fill-in-the-blanks starting point |
| `lib/` | vendored MIT-licensed JS (PptxGenJS, jsPDF, html-to-image) for the in-browser export buttons |

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and redistribute,
commercially or otherwise. Bundled third-party JS libraries keep their own
(also MIT-style) licenses — see [lib/THIRD_PARTY_NOTICES.md](lib/THIRD_PARTY_NOTICES.md).

## Support

DeckCraft is free. If it's useful to you, you're welcome to buy me a coffee
— entirely optional, no features are gated behind it.
<!-- TODO: add your Buy Me a Coffee link once the account exists, e.g.
     [buy me a coffee](https://buymeacoffee.com/<your-handle>) -->
