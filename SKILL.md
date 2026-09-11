---
name: deck-craft
description: >-
  Create a polished presentation (HTML slide deck) from content, in a choice of
  built-in visual themes. Use when the user wants to build/generate a deck,
  slides, presentation, pitch, readout, or review — e.g. "make a deck about
  X", "turn these notes into slides", "build a quarterly review
  presentation", "I need a title/agenda/stats/roadmap slide". Produces one
  self-contained HTML file (double-click to present; arrow keys / on-screen
  buttons to navigate) built from a simple Markdown source via build.py.
  Also use when the user asks for their local deck-craft library, usage
  metrics, or a dashboard of decks they have built. Supports 31 slide types:
  cover, section divider, agenda, bullets, two-col bullets, 3-up & 4-up cards,
  2x2 & 3x2 grids, horizontal & vertical flows, table, big-number stats, quote,
  text+image, full-width image, 2- & 3-column image, timeline/roadmap,
  two-column text, RAG status, bar chart, callout, org chart, statement,
  team grid, feature matrix, glossary, roadmap swimlane, delivery plan, and
  closing.
---

# Deck Craft

Generate a presentation by writing a Markdown source file and running
`build.py`. Output is a single portable `.html` file — no server, no
dependencies (Python 3 standard library only). Fixed 1280×720 canvas scaled to
fit the viewport; every slide carries the theme's top bar and a footer with
the page number and year on the bottom-left plus a classification label on the
bottom-right automatically.
If a slide's content overflows the canvas (e.g. a footnote or the page number
would be clipped off the bottom), it is auto-scaled down slightly at render time
(up to ~2 points) so everything stays visible.

## Workflow

1. **Interpret the prompt first** (see "Interpreting the prompt"), and clarify
   only genuine gaps (see "Clarifying the brief") before drafting. Then draft
   `deck.md` in the target folder using the schema below, choosing the slide TYPE
   that best fits each piece of content (guidance under each type), and picking
   a `theme:` (see "Themes" below).
2. **Show the drafted `deck.md` to the user and get approval before building.**
   Present the full draft, invite edits, and only proceed once the user confirms.
3. **Add images** (optional) to an `assets/` folder next to `deck.md`; reference
   them by filename (e.g. `image: diagram.png`). Missing images render a clearly
   flagged placeholder and print a warning — they never break the build.
4. **Build:** `python3 build.py deck.md` → writes `deck.html` next to it (or
   `python3 build.py deck.md out.html`). Report any `!` warnings to the user.
5. **Open** `deck.html` (double-click) and iterate by editing `deck.md` and
   re-running — never hand-edit the generated HTML. For rapid iteration, run
   `python3 build.py deck.md --watch` to auto-rebuild on every save (Ctrl+C to
   stop); the user just refreshes the browser (⌘R) to see each change. After the
   final build, launch or reuse the local library dashboard with
   `python3 dashboard.py --launch`; this opens the dashboard without starting
   duplicate servers.
6. **Export to PowerPoint or PDF (optional):** the deck has **"↓ PowerPoint"**
   and **"↓ PDF"** buttons next to the nav arrows. Each captures every slide as
   an image and downloads a `.pptx` or `.pdf` (one image per slide/page, 16:9) —
   handy for presenting via a PowerPoint viewer or sharing a fixed PDF without a
   browser. Both are image-per-slide, not editable. To ship a plain deck
   without a button, build with `--no-pptx` and/or `--no-pdf`.

`build.py` lives in this skill folder. Run it from here, or from anywhere with a
full path to the installed skill, e.g.
`python3 ~/.claude/skills/deck-craft/build.py /path/to/deck.md`.
See `example-deck.md` for a complete worked deck using all 31 types, and
`template-deck.md` for a blank fill-in template covering every type.

## Themes

Pick a theme with `theme:` in front matter; it sets the palette, font, panel
treatments, and top-bar style all at once. `accent:` and/or `font:` in front
matter still override just those two tokens on top of whichever theme is
chosen — so a theme is a starting point, not a lock-in.

| theme | look | good for |
|---|---|---|
| `corporate` (default) | clean white deck, blue accent, dark navy cover/section/stats/closing, thin accent top bar | reviews, readouts, most business decks |
| `minimal-mono` | grayscale, flat panels, no top bar | understated, text-forward decks |
| `dark-tech` | dark throughout, indigo/cyan accent, monospace type | engineering reviews, technical deep-dives |
| `warm-editorial` | warm cream background, serif type, terracotta accent | narrative, culture, or story-led decks |

If the user doesn't name a theme, default to `corporate` — ask only if the
occasion clearly calls for a different feel (e.g. "keep it dark and techy" →
`dark-tech`).

## Interpreting the prompt

The user describes a deck in plain language; you turn it into a structured
`deck.md`. Work in this order and *self-serve before you ask*:

1. **Ingest any material the user already has first.** If they reference or paste
   a doc, notes, a ticket, or a URL, extract structure from it before
   asking anything: headings → `section`/slide titles, lists → `bullets`,
   tables → `table`/`matrix`, numbers/KPIs → `stats`/`bar-chart`, sequences →
   `flow-*`/`timeline`, people → `team`/`org-chart`. Content the user supplied is
   the fastest, richest input — prefer it over interrogation.
2. **Infer the essentials, then fill gaps with defaults** (don't stall):
   - **Purpose & audience** → sets tone and which recipe to use.
   - **Length** → default ~8–12 slides for a review, ~6–8 for a proposal.
   - **Look** → `theme` defaults to `corporate`, `classification` defaults to
     Private & Confidential, `accent` follows the chosen theme unless the user
     gives one.
3. **Map content nouns → slide types** (see the cheat table below), choosing for
   meaning not decoration.
4. **Pick a recipe** (below) when the user hasn't specified a structure, then
   adapt it to their content.
5. **Only then clarify** genuine gaps — see "Clarifying the brief".

## Deck recipes

When the user names an intent but not a structure, start from the matching
skeleton and adapt. Add/remove slides to fit their content; always open with
`cover` and usually end with `closing`.

| intent / trigger | skeleton |
|---|---|
| **Leadership / quarterly review** | cover → agenda → section → `status` (RAG) → `stats` or `bar-chart` → `timeline` → `callout` (decision) → closing |
| **Project kickoff** | cover → `statement` (mission) → `cards-3` (goals) → `timeline` → `team` → `callout` (asks) → closing |
| **Proposal / pitch** | cover → `two-col-text` (problem/solution) → `cards-3` (approach) → `matrix` (options) → `stats` (impact) → `callout` (recommendation) → closing |
| **Status update** | cover → `status` (RAG) → `bar-chart` (progress) → `bullets` (risks) → `callout` (next steps) → closing |
| **Retrospective** | cover → `stats` (outcomes) → `grid-2x2` (went well / to improve) → `bullets` (actions) → closing |

If none fit, build a simple arc: **cover → context → body (2–5 content slides
chosen by type) → decision/next-steps → closing.**

## Keyword → slide-type cheat table

Map what the user says to a `type:`. Feature keywords (bottom rows) unlock
specific rendering behaviour.

| user says… | use type |
|---|---|
| "agenda", "running order", "what we'll cover" | `agenda` |
| "key points", "takeaways" | `bullets` / `two-col-bullets` |
| "three/four pillars", "options", "workstreams" | `cards-3` / `cards-4` |
| "quadrants", "SWOT", "2×2" | `grid-2x2` |
| "six features/workstreams" | `grid-3x2` |
| "process", "steps", "stages" | `flow-h` / `flow-v` |
| "roadmap", "milestones", "timeline" | `timeline` |
| "roadmap across quarters by workstream" | `roadmap-swimlane` |
| "delivery plan", "E2E plan", "dev blocks + go-lives by date", "Gantt" | `delivery-plan` |
| "compare", "vs", "comparison table" | `table` |
| "scored comparison", "feature matrix" | `matrix` |
| "KPIs", "metrics", "numbers", "results" | `stats` |
| "chart", "bars", "per quarter/month" | `bar-chart` |
| "RAG", "status", "on-track/at-risk/blocked" | `status` |
| "quote", "testimonial" | `quote` |
| "decision", "recommendation", "the ask" | `callout` |
| "org", "reporting lines", "team structure" | `org-chart` |
| "the team", "who's involved", "people" | `team` |
| "acronyms", "definitions", "glossary" | `glossary` |
| "one big idea", "transition", "manifesto line" | `statement` |
| **"highlight" / "accent" this one** | prefix item with `*` (grids, bar-chart) |
| **"green/amber/red", "on-track/at-risk/blocked"** | sets the `status` dot colour |
| **"dark", "high-impact"** | `variant: dark` on callout; or a dark type |
| **"✓ / ✗ / ~" or "yes/no/partial"** | matrix semantic marks |

## Clarifying the brief (grill only when it helps)

Modelled on the `grill-me` approach — but **bounded for speed**. The goal is a
good deck fast, not exhaustive interrogation.

- **Self-serve first.** If a question can be answered from the prompt or the
  user's supplied material, answer it yourself — don't ask.
- **Ask only real gaps**, one at a time, in this priority order, and **always
  offer a recommended default** so the user can accept-and-go:
  1. **Purpose & audience** — "Who's this for, and what should they do after?"
  2. **Length / depth** — "Roughly how many slides — a tight ~8 or a fuller ~14?"
  3. **Missing content or data** — e.g. "You mentioned KPIs — what are the
     actual numbers?" or "Which workstreams, and their RAG status?"
  4. **Slide-type ambiguity** — e.g. "Compare A vs B as a simple **table**, or a
     scored **matrix** with ✓/✗/~?"
  5. **Images / visuals** — ask whether they want to supply any images, and tell
     them which slides can use them: a **cover logo**, a **text-image** visual,
     dedicated image slides (`image-full`, `image-2col`, `image-3col` for
     screenshots), **card icons** (`cards-3`/`cards-4`), and **team avatars**.
     If yes, have them
     drop files into an `assets/` folder next to `deck.md` and give you the
     filenames; reference each as `image: name.png`. If they'd rather not, note
     that `team` auto-generates initials avatars and other slides simply omit the
     image — the deck never breaks on a missing one.
  6. **Theme / brand/format** — which theme (see "Themes"), and classification
     or accent, only if not inferable.
- **Batch only tightly-related essentials** (e.g. audience + length together);
  otherwise keep to one question at a time with its recommended answer.
- **Know when to stop.** As soon as you can produce a sensible deck, stop asking
  and draft. A clear, content-rich prompt should skip straight to the draft.
- **Then draft and confirm** the `deck.md` per the Workflow's approval step.

## Local library dashboard

Each successful build is recorded **on this machine only** in
`~/.deck-craft/library.json` (no network calls). Open a personal dashboard of
metrics and organised links to every deck you've built:

```bash
python3 dashboard.py                 # serves on the first free port from 8791
python3 dashboard.py --launch        # start/reuse in background, open, then exit
python3 dashboard.py --restart       # force-restart the background server
python3 dashboard.py --stop          # stop the background server
python3 dashboard.py --port 9000     # pin a specific port
python3 dashboard.py --no-open       # serve without launching a browser
python3 dashboard.py --register existing.html [source.md]   # index one prior deck
python3 dashboard.py --import-dir ~/path/to/decks           # scan a folder of decks
python3 dashboard.py --json          # metrics + deck list as JSON
```

A background server started before an update is detected as outdated and
restarted automatically by `--launch`, so you never see stale UI. Use
`--restart` to force it.

`--import-dir` recursively finds Deck Craft HTML under that folder (looks for the
`#stage` + `.slide` markup), pairs each with a sibling `.md` when present, and
indexes them locally. Re-running it refreshes metadata without double-counting
builds. New builds continue to land wherever you write them — still fully local.

If another app already owns the default port, the dashboard moves to the next
free one rather than attaching to that app — it verifies its own `/api/ping`
marker before reusing a server.

The dashboard shows deck count, build count, slides, recent activity, and groups
decks by folder with one-click open. Pass `--no-index` to `build.py` to skip
recording a build. Override the index location with `DECK_CRAFT_HOME` (directory
for `library.json`). LLM cost is not available locally (that would need central
telemetry).

## Source format

Optional front matter first, then one block per slide separated by a line of
`---`. Inside a block: `key: value` fields, `- item` list rows (indent two
spaces for a sub-bullet; `-- item` marks a right-column item), and `| a | b |`
table rows. Inline `**bold**`, `*italic*`, `[text](url)` are supported. Split
compound rows with `::` (e.g. `Title :: description`).

```
---
title: Tech Workstream
subtitle: Quarterly Review · Leadership
theme: corporate
classification: Private & Confidential
transition: fade
---

type: cover
title: Tech Workstream
subtitle: Quarterly Review · Leadership
```

**Front matter keys:** `title`, `subtitle`, `classification` (default
`Private & Confidential`, shown small on the bottom-right of every slide; the
footer's bottom-left carries the page number and year), `theme` (default
`corporate`; see "Themes"), `accent` (hex, overrides the theme's accent),
`font` (CSS font-family string, overrides the theme's font),
`date`, `audience`, `transition` (`fade` (default) or `swipe`). Any slide may
override `classification`. Any slide may also set `footnote:` to add a small
italic footnote — handy for defining a `*` marker used in a label
(e.g. `footnote: * Ongoing iterations`). It pins to the bottom of the slide,
except on `roadmap-swimlane` and `table`, where it sits directly beneath the
table.

## The 31 slide types

Each block starts with `type:`. Fields in **bold**, list rows shown as `-`.

| type | when to use | key content |
|---|---|---|
| `cover` | opening title slide (dark) | `title`, `subtitle`, `logo:`/`image:` |
| `section` | divider between sections (dark) | `number`, `title` |
| `agenda` | numbered running order | `- Item :: 10 min` |
| `bullets` | single-column key points | `- point` + indented `  - sub` |
| `two-col-bullets` | many short points | `- point` (auto-splits L/R) |
| `cards-3` | 3 pillars/options | `- Title :: description [:: img]` |
| `cards-4` | 4 pillars/options/categories | `- Title :: description [:: img]` |
| `grid-2x2` | quadrants / SWOT | `- Label :: insight` (prefix `*` to accent one) |
| `grid-3x2` | 6 features/workstreams | `- Title :: description` |
| `flow-h` | left→right process (≤4 steps) | `- Step :: description` |
| `flow-v` | top→bottom stages | `- Step :: description` |
| `table` | structured comparison | `\| header row \|` then data rows (last col accented) |
| `stats` | big-number KPIs (dark) | `- $3.2M :: Annual Revenue :: +24% YoY` |
| `quote` | pull-quote / testimonial | `quote:`, `author:`, `role:` |
| `text-image` | copy beside a visual | `title`, `image:`, `- point` |
| `image-full` | one full-width image (e.g. screenshot) | `title`, `subtitle`, `image:` |
| `image-2col` | two equal image columns | `title`, `subtitle`, `- a.png`, `- b.png` |
| `image-3col` | three equal image columns | `title`, `subtitle`, `- a.png`, `- b.png`, `- c.png` |
| `timeline` | roadmap / milestones | `- Q1 2025 :: Phase :: detail` |
| `two-col-text` | problem/solution contrast | `left-label:`,`- para`; `right-label:`,`-- para` |
| `status` | RAG workstream tracker | `- Name :: green/amber/red :: summary :: owner` |
| `bar-chart` | single-series bar chart | `- Label :: value` (prefix `*` to accent one) |
| `callout` | decision / recommendation | `label`, `title` (statement), `- reason` |
| `org-chart` | reporting lines / team structure | `lead`, optional `assistant`, `- Name :: role` |
| `statement` | one big idea / transition (dark) | `title` (the sentence), optional `eyebrow` |
| `team` | people / avatars grid | `- Name :: role [:: img]` |
| `matrix` | feature / option comparison | `\| header \|` rows; cells `yes`/`no`/`~` → ✓ ✗ ~ |
| `glossary` | acronyms / definitions | `- Term :: definition` (auto-splits L/R) |
| `roadmap-swimlane` | workstreams × time grid (bars, or `markers: stars` milestones) | `columns:`, `- Name :: 1-2 Phase :: 3-4 Phase` |
| `delivery-plan` | date-driven E2E plan: dev blocks, milestones & go-lives across a calendar | `start:`,`end:`,`teams:`, opt. `density:`; `- phase/bar/milestone/launch :: …` |
| `closing` | thank-you / questions (dark) | `eyebrow`, `title`, `- Name :: contact` |

`callout` also has a **dark variant** — set `variant: dark` (or use
`type: callout-dark`) for a high-emphasis, dark-background decision slide.

Type aliases accepted: `divider`→section, `cards`→cards-3, `2x2`/`3x2`→grids,
`flow`→flow-h, `roadmap`→timeline, `two-col`/`problem-solution`→two-col-text,
`image`→text-image, `screenshot`/`image-fullwidth`→image-full,
`images-2`/`two-image`→image-2col, `images-3`/`three-image`→image-3col,
`rag`→status, `bar`/`chart`→bar-chart,
`decision`/`recommendation`→callout, `org`/`org-tree`/`reporting-line`→org-chart,
`big-idea`/`impact`→statement, `people`/`avatars`→team,
`feature-compare`/`compare`→matrix, `definitions`/`terms`→glossary,
`swimlane`/`roadmap-grid`→roadmap-swimlane,
`delivery`/`delivery-timeline`/`gantt`/`e2e-plan`→delivery-plan,
`thanks`/`close`→closing.

## Rules & tips

- Choose types for meaning, not decoration: sequences → `flow-*`/`timeline`,
  comparisons → `table`/`two-col-text`, metrics → `stats`, options → `cards-*`.
- Keep card/bullet copy to ~2–3 lines; the canvas is fixed, so overly long text
  can overflow. Prefer more slides over cramming one.
- `stats` shows 1–4 numbers best; `cards-3`=3 items, `cards-4`=4, `grid-3x2`=6,
  `timeline`=up to ~5 milestones; `status`=3–6 rows; `bar-chart`=3–7 bars.
- `status` colours the dot from the second field (`green`/`amber`/`red`, or
  `on-track`/`at-risk`/`blocked`); `bar-chart` reads the numeric part of each
  value, so `$204k`, `204`, and `204 pts` all plot the same height.
- `org-chart`: `lead:` is the top box, each `-` row is a direct report
  (`Name :: role`), and the optional `assistant:` (or `pa:`) renders as a
  dashed side-node off the lead. Works at any level, not just Director. Up to
  6 reports sit in one row; 7+ auto-wrap onto two balanced rows so cards stay
  legible (practical ceiling ~10). Use `callout-dark` sparingly for a single
  big decision.
- `statement` is a dark, full-bleed single sentence — use it as a transition or
  to land one idea; unlike `quote` it needs no attribution and unlike `stats`
  it's words, not a number. Keep it to one line or two.
- `team` shows 3–4 people per row (wraps beyond that); omit the image to get an
  auto initials avatar in the accent colour.
- `matrix` cells map `yes`/`y`/`✓`→✓, `no`/`n`/`✗`→✗, `partial`/`~`→~; any other
  text renders as-is, and the last column keeps the accent-highlight convention.
- `table` cells containing a RAG word (`green`/`amber`/`red`, or
  `on-track`/`at-risk`/`blocked`) render as a coloured dot + label — handy for a
  RAG status column in a progress report.
- `roadmap-swimlane`: set `columns:` (pipe-separated periods); each `-` row is a
  workstream whose phases are `start-end Label` (or a single `col Label`), e.g.
  `- Data :: 1-2 Migrate :: 3-4 Tune`. Best with 3–5 rows and 3–6 columns.
  Add `markers: stars` to render milestones as ★ markers with the label beside
  them instead of filled phase bars. In star mode a leading weekday token
  positions each phase on the actual day within its column, and the token also
  selects the shape: a single weekday (or none) is an **exact date** → a ★ on
  that day, e.g. `- Help :: 2 Thu Go live (13 Aug)`; a weekday **range** (e.g.
  `Mon-Fri`) or a multi-column span is a **date range** → a filled block
  covering those days, e.g. `- Peacock :: 1 Mon-Fri Sign off (3–7 Aug)`.
- `delivery-plan`: a **date-driven** Gantt for a whole delivery. Set the span
  with `start:` and `end:` (ISO `2026-03-01`, or `1 Apr`/`Apr 2026`), an optional
  `today:` for a vertical marker, and an optional `teams:` list that assigns
  bar colours (`teams: Client=#2d7bff, Server=#00b8a9, Data`). The month axis is
  drawn automatically across the span. Each `-` row declares its kind first:
  - `- phase :: Phase name :: SIP-2054, SIP-2101` — starts a workstream band; the
    ticket refs are optional and shown under the name in the left rail.
  - `- bar :: Label :: Team :: 7 Apr - 28 Apr` — a dev block, positioned and
    sized by its date range. Multiple bars in a phase stack. Field 3 is the
    **team** by default, or a **status word** when `bars: status` (see below).
  - `- milestone :: Label :: green/amber/red :: 28 Apr` — a status-coloured dot
    with an inline `Label · date` beside it.
  - `- launch :: Go Live :: 30 Jun` — a go-live marker; renders as a green dot
    with an inline `Label · date` (same style as a milestone).
  Bars, milestones and launches attach to the most recent `phase`. Short dates
  (`7 Apr`) inherit the year from `end:`/`start:`. Best with 3–6 phases; keep bar
  labels short. See the **Delivery-plan intake** wizard below for gathering the
  data. To collect a lot of detail interactively, ask the wizard's questions.
  - **Density** — `density:` is an opt-in control that trades chrome for more
    swimlanes; the default is unchanged from a normal plan:
    - `density: comfortable` (default) — roomy bars, keeps the title/subtitle;
      best for ~6–9 lanes.
    - `density: compact` — **hides the title & subtitle**, tightens the bands
      and lets the slide zoom out (~75%) so it auto-scales to any band count;
      fits ~20 lanes. (`dense` is accepted as an alias of `compact`.)
  - **Bar colour mode** — `bars:` chooses what the bar colour means:
    - `bars: team` (default) — colour by owner from `teams:`. Bar field 3 is the
      team name. A **colour→team key** is drawn from the teams actually used by
      bars, so a phase mixing multiple teams stays decodable (the left rail names
      the phase, not the team).
    - `bars: status` — colour by RAG/progress; a **status legend** is shown
      (Complete / On Track / At Risk / Blocked / TBD) because those colour
      meanings appear nowhere else. In the title-less densities it runs as a
      horizontal row across the top; otherwise it sits top-right. Bar field 3 is
      a status word: `complete`/`done`/`blue`→Complete, `in-progress`/`on-track`→
      On Track, `at-risk`/`amber`→At Risk, `blocked`/`red`/`late`→Blocked, and
      `tbd`/`placeholder`/`planned`→TBD (also the fallback for unknown words).
      e.g. `- bar :: Tech tasks :: in-progress :: 1 May - 30 Jun`.
- Dark slides (`cover`, `section`, `stats`, `closing`) are intentional accents —
  don't overuse them back-to-back.
- Always start with a `cover` and usually end with a `closing`.
- After building, surface the output path and any missing-image warnings.

## Delivery-plan intake (wizard)

When the user wants a **delivery plan / E2E timeline** and hasn't handed over a
structured source, gather the shape interactively — but stay bounded (per
"Clarifying the brief"): self-serve from any material first, ask one question at
a time, always offer a sensible default, and stop as soon as you can draft.
Walk this order, then draft the `delivery-plan` block and confirm before
building:

1. **Overall window** — "What's the plan's start and end date?" (sets `start:`
   / `end:`; default to today → +6 months if they're unsure). Add `today:` if
   they want a "we are here" line.
2. **Bar colour mode** — "Should the bars be coloured by **team/owner** or by
   **status** (complete / on-track / at-risk / blocked / TBD)?" (sets `bars:` —
   default `team`). This drives what field 3 of each `- bar ::` means and which
   legend is shown.
3. **Teams / owners** — only if `bars: team`: "Which teams own the work, and do
   you want a colour per team?" (sets `teams:`; default palette is fine — you can
   just list names). Skip this if they chose status colouring.
4. **Phases / workstreams** — "What are the phases or workstreams, top to
   bottom?" For each, ask for a name and any ticket refs.
   Recommend 3–6 phases so it stays legible.
5. **Dev blocks per phase** — for each phase: "What are the development blocks,
   their start→end dates, and — depending on the mode — who owns each (team) or
   its status?" (one `- bar ::` per block).
6. **Milestones** — "Any checkpoints (design complete, signoff, UAT)? What's the
   date and its status (green/amber/red)?" (one `- milestone ::` each).
7. **Launches / go-lives** — "What's the go-live or GA for each phase, and when?"
   (one `- launch ::` each — renders a green dot with an inline `Label · date`).
8. **Confirm** — show the drafted block, invite edits, then build.

Batch tightly-related asks (e.g. a phase's name + refs + its blocks together)
rather than one field at a time, and skip anything already implied by their
material. Keep bar labels short so they don't clip.
