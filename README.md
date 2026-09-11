# Deck Craft

Turn a plain Markdown file into a polished, presentable slide deck — one
self-contained HTML file, no server, no dependencies beyond Python 3's
standard library. 31 slide types, 4 built-in visual themes, optional
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

## Themes

Set `theme:` in a deck's front matter. `accent:` / `font:` still override just
those two tokens on top of whichever theme you pick.

| theme | look |
|---|---|
| `corporate` (default) | clean white deck, blue accent, dark navy cover/section/stats/closing |
| `minimal-mono` | grayscale, flat panels, no top bar |
| `dark-tech` | dark throughout, indigo/cyan accent, monospace type |
| `warm-editorial` | warm cream background, serif type, terracotta accent |

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

Deck Craft is free. If it's useful to you, you're welcome to buy me a coffee
— entirely optional, no features are gated behind it.
<!-- TODO: add your Buy Me a Coffee link once the account exists, e.g.
     [buy me a coffee](https://buymeacoffee.com/<your-handle>) -->
