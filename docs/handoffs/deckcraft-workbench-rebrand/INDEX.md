# Hand-off: DeckCraft Workbench rebrand

**Source:** local file, `Deck Craft Design System.zip` (dropped into the project directory
as `design_handoff_deckcraft/`, not pulled via Claude Design sync — no design-system project
UUID). Files preserved here as delivered: `README.md`, `tokens.css`, `deck-themes.json`,
`DeckCraft Brand.dc.html` (the design board prototype), `support.js` (the board's own
rendering runtime — not application code, not ported).

**Date:** 2026-09-11

## Intent

The hand-off's `README.md` covers three things: a brand identity ("Workbench", option `1b`
on the design board), a full hosted "composer" web app (brief → AI-generated deck → PowerPoint
+ a real one-off tip payment flow), and eight new deck output themes with exact palette/type
values (`deck-themes.json`).

## What was implemented

- **Brand identity** — applied to `site/index.html` and the project docs (`README.md`,
  `SKILL.md`): the Workbench palette (charcoal/terracotta/cream), Lora+Sora type pairing,
  the three-bar mark, spacing/radius/shadow rules, and the approved voice, adapted where the
  hand-off's copy assumed the in-browser composer (see below).
- **Eight deck themes** — replaced the previous four in `build.py` (`modern`, `professional`,
  `dark`, `light`, `editorial`, `technical`, `bold`, `warm`), using the exact values from
  `deck-themes.json`. The old theme ids are kept as deprecated aliases so existing decks don't
  break. Shipped as v2.0.0 (breaking change to theme ids).

## What was explicitly NOT implemented

The hand-off's "Composer", "Tip flow", and "Thank-you/receipt" screens — a hosted web app
that generates decks from a text brief via an AI backend, with real one-off payment
processing for tips — were **not built**. Confirmed with the project owner that the actual
product remains the free, offline skill (download, run `build.py` yourself, no accounts, no
backend); the hosted-composer-with-payments concept in the hand-off appears to be a Claude
Design session that designed a larger product than what was asked for. The landing page's
copy and "how it works" steps were adapted to describe the real flow (an AI assistant reads
`SKILL.md` and runs `build.py` locally) rather than the hand-off's literal in-browser
generate button. The "Leave a tip" affordance is kept as an inert, clearly-labelled
placeholder pending a real Buy Me a Coffee link — not a payment flow.

If a hosted composer is wanted in future, treat the "Screens / Views", "Interactions &
Behavior", and "State Management" sections of `README.md` in this folder as the starting
spec — they were not consumed by this round of work.
