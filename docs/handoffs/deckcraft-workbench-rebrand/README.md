# Handoff: DeckCraft — brand, website, and deck styles

## Overview
DeckCraft is a tip-funded tool for founders, solo consultants, sole traders and anyone who
pitches often. A user describes the presentation they need, picks one of eight house styles,
and gets a PowerPoint file. It is free to use; a "buy me a coffee"-style tip jar with
open-amount, one-off tips is the only monetisation. There is no paywall, no subscription,
no credits.

This bundle covers three things:
1. **Brand identity** — the "Workbench" direction (option `1b` on the design board).
2. **Website** — the screens that make up the product, specified against that identity.
3. **Deck styles** — the eight output themes the generator can produce.

## About the Design Files
The files here are **design references created in HTML** — prototypes that communicate
intended look, values and behaviour. They are not production code to copy.

The task is to **recreate these designs in the target codebase's existing environment**
(React, Vue, Svelte, Next, whatever is already in place), using its established patterns,
component library and conventions. If no codebase exists yet, choose an appropriate stack
and implement there. `tokens.css` is provided as a convenience starting point — translate
it into whatever token mechanism the codebase already uses (Tailwind theme, CSS variables,
theme object) rather than bolting on a second system.

## Fidelity

- **Brand identity — high fidelity.** Palette, typography, lockup construction, voice and
  the applied hero/tip-button treatment are final. Match hex values, font weights, sizes,
  letter-spacing and radii exactly as documented. Source: `DeckCraft Brand.dc.html`,
  option `1b` ("Workbench").
- **Deck styles — high fidelity on values, not layout.** Each of the eight themes has a
  final palette, type pairing and defining rule (`deck-themes.json`). Slide layouts
  themselves have not been mocked yet — build the theme values into the generator and
  come back for slide masters.
- **Website — specified, not mocked.** The screens below are described precisely in terms
  of the brand system, but no pixel mock exists yet. Treat the layout descriptions as
  binding on structure and tokens, and use judgement on anything not stated. Ask the
  designer for mocks if a screen needs to be pixel-exact.

Options `1a` (Imprint), `2a` (Kiln) and `2b` (Bench) also appear on the board. They are
**rejected explorations** — do not implement them. Only `1b` is live.

---

## Brand identity — Workbench

### Lockup
- Wordmark: **DeckCraft**, one word, capital D and C, no space. Lora 600, letter-spacing
  -0.02em, line-height 1.0. Never in all caps, never letterspaced.
- Mark: three stacked horizontal bars reading as a stack of slides, inside a rounded
  square. Bars are 34×7px with 4px radius, 5px gap, in Cream `#FBF7F1` at 100% / 72% / 45%
  opacity top to bottom; the third bar is 20px wide. Container is 92×92px, 24px radius,
  Terracotta `#C4593B` fill.
- Horizontal lockup: mark, 28px gap, wordmark at 50px optically centred on the mark.
- Tagline (optional, not part of the lockup): "A small tool for people who pitch a lot",
  Sora 400 14px, `#6E6459`.
- Mark works standalone at 32px and above. Clear space around the lockup equals one
  mark-width. Do not redraw, rotate, outline or gradient the mark.

### Palette
| Role | Name | Hex | Use |
|---|---|---|---|
| Ink | Charcoal | `#2B2724` | All headings, dark panels |
| Primary action | Terracotta strong | `#A9472C` | Buttons, 11px uppercase labels, any small text |
| Brand accent | Terracotta | `#C4593B` | Large fills only (the mark, blocks ≥24px type) |
| Action hover | Terracotta deep | `#8E3A22` | Primary button hover |
| Page | Cream | `#FBF7F1` | Page background |
| Surface | Oat | `#EFE4D6` | Cards, hero panels, callouts |
| Surface alt | White | `#FFFFFF` | Inset cards on Oat, form fields |
| Success | Sage | `#5C6B52` | Confirmation states only |
| Border | `#E4DACE` | Card and section borders |
| Border soft | `#EFE4D6` | Inner dividers on white |
| Divider | `#F0E8DE` | Hairlines inside cards |

Text colours: heading `#2B2724`, body `#4A423B`, muted body `#6B5F55`,
captions and eyebrows `#6E6459`, on-dark body `#6B5F55` → use `#FBF7F1` on Charcoal.

**Contrast rule:** every hex above was chosen to clear WCAG AA 4.5:1 at small sizes.
`#C4593B` does **not** clear 4.5:1 for 11–14px text or for white text on a button —
use `#A9472C` there. Reserve `#C4593B` for the mark and for type at 24px and above.

### Typography
Two families, no others.

- **Lora** (serif) — headlines only, 600 weight, letter-spacing -0.015 to -0.02em.
  Italic 400 for subheads and pull quotes. **Never below 20px and never in all caps.**
  - Display: 50px / 1.0 / -0.02em
  - H1: 42px / 1.08 / -0.02em
  - H2: 30px / 1.15 / -0.015em
  - H3: 23px / 1.2 / -0.01em
  - Subhead italic: 22px / 1.3
- **Sora** (sans) — everything functional: body, buttons, labels, form fields, amounts.
  - Body: 16px / 1.68 / 400, max 70 characters per line
  - Body small: 15px / 1.65 / 400
  - Caption: 12px / 1.5 / 400, colour `#6E6459`
  - Label: 11px / 600 / uppercase / letter-spacing 0.16em, colour `#A9472C` or `#6E6459`
  - Button: 14px / 600
  - Numerals and amounts: Sora 500, tabular where available

### Shape and elevation
- Radii: 999px (buttons, chips, pills), 20px (outer cards, hero panels), 16px (inner
  cards), 14px (swatches, thumbnails), 12px (form fields).
- No shadows anywhere. Separation comes from surface colour (Oat on Cream) and 1px borders.
- Borders are always 1px, `#E4DACE` on Cream, `#EFE4D6` on White.

### Voice
Like a maker showing you their bench: warm, first-person, happy to explain the craft
behind a slide. Full sentences. No corporate "we", no growth-speak, no urgency, and no
coffee puns beyond the one in the tip jar itself.

Approved strings:
- Hero: "Tell me about the deck. I'll build it in your style."
- Tip ask: "Free to use. Tips keep the bench lit."
- Longer tip ask: "Use it as much as you like. Tips keep the bench lit."
- Receipt: "Got it, thank you. Go win the room."
- Primary button: "Leave a tip"

---

## Screens / Views

### 1. Landing
**Purpose:** explain the tool in one screen and get the user into the composer.

**Layout:** single column, max-width 1120px, centred, 24px gutters. Vertical rhythm
64px between sections on desktop, 40px on mobile.

- **Header** — 72px tall, Cream background, 1px bottom border `#E4DACE`. Lockup left at
  32px mark height with the wordmark at 22px. Right: text links "Deck styles", "How it
  works" (Sora 400 15px `#4A423B`, hover `#A9472C`) and a "Leave a tip" pill button
  (Terracotta strong `#A9472C`, white 14px/600, 13px × 24px padding, 999px radius,
  hover `#8E3A22`).
- **Hero** — Oat `#EFE4D6` panel, 20px radius, 64px padding. Lora 600 at 42px/1.08,
  max-width 520px: "Tell me about the deck. I'll build it in your style." Below, Sora 400
  16px `#6B5F55`: "Free to use. Tips keep the bench lit." Then the composer entry: a White
  `#FFFFFF` field, 12px radius, 1px `#E4DACE` border, 3 rows, placeholder "A 10-slide
  seed round pitch for a B2B logistics startup…" (Sora 400 16px, placeholder `#9A8F85`
  is too light — use `#6E6459`), with the primary button below it.
- **How it works** — three columns, 24px gap, each a White card with 1px `#EFE4D6`
  border and 16px radius, 28px padding. Each card: 11px uppercase label in `#A9472C`
  ("01 Describe" / "02 Pick a style" / "03 Download"), Lora 600 23px heading, Sora 400
  15px body `#4A423B`. Cards stack full-width below 760px.
- **Style strip** — horizontal scroller of the eight deck-style cards (see screen 2),
  each 320px wide, 24px gap, scroll-snap. Section heading Lora 600 30px; caption Sora
  12px `#6E6459`.
- **Tip band** — Charcoal `#2B2724` panel, 20px radius, 48px padding. Lora 600 30px in
  `#FBF7F1`, body `#EFE4D6` (not `#6B5F55` — too dark on Charcoal), primary button plus
  three preset chips (see Tip flow).
- **Footer** — 40px padding, Cream, 1px top border. Lockup mark at 24px, Sora 12px
  `#6E6459` links.

### 2. Deck styles gallery
**Purpose:** let the user see and pick a house style before or during generation.

**Layout:** responsive grid, `repeat(auto-fill, minmax(380px, 1fr))`, 24px gap.

**Style card anatomy** (this is the one component to get exactly right — it is fully
mocked in `DeckCraft Brand.dc.html`, block `1c`):
- Outer card: 1px `#E0DBD1` border, no radius change from theme — use 16px to match the
  Workbench system.
- **Preview area**: the *theme's own* background colour, 26px × 24px padding. Contains the
  theme's 11px uppercase eyebrow ("01 / Modern") in the theme's accent, a specimen headline
  in the theme's display font at 30px, and a spec line in Sora 14px giving the type pairing.
  The preview area is styled in the **deck theme's** colours and fonts, not the brand's.
- **Swatch strip**: 34px tall, four equal flex children showing the theme's four core
  colours. Any swatch lighter than `#F0F0F0` needs `box-shadow: inset 0 0 0 1px #E0DBD1`
  or it bleeds into the card.
- **Footer**: 18px × 24px padding, Sora 13px/1.6 `#4A443C`, one sentence stating the
  theme's defining rule.
- Selected state: 2px `#A9472C` border and a Terracotta strong check pill top-right.
  Hover: border `#C4593B`.

Card copy and values are in `deck-themes.json`, one object per theme, with `bg`,
`ink`, `accent`, `secondary`, `displayFont`, `bodyFont`, `specimen`, `spec` and `rule`.

### 3. Composer
**Purpose:** where the user writes the brief, picks a style, and generates.

**Layout:** two columns on desktop (`minmax(0,1fr) 380px`, 32px gap), single column
below 900px.
- **Left:** the brief textarea (White, 12px radius, 1px `#E4DACE`, min-height 220px,
  Sora 400 16px/1.68, 20px padding) plus optional chips for length and audience
  (999px pills, 1px `#E0D2C2`, Sora 14px `#4A423B`, selected = `#A9472C` fill + white).
- **Right:** sticky style picker — a vertical list of the eight themes as compact rows
  (48px preview square in the theme's bg + theme name in Lora 600 18px + accent dot),
  16px radius, White surface.
- **Generate button:** primary pill, full width of the left column, 16px/600 Sora,
  label "Build the deck".
- **Generating state:** button disabled at 60% opacity, label "Building…", and a
  progress line 2px tall in `#A9472C` animating left to right on `#EFE4D6`. No spinners.
- **Result:** White card, 16px radius, containing the filename in Sora 500 15px, file
  size in `#6E6459` 13px, a "Download .pptx" primary button and a text link "Build
  another". Immediately below, the tip ask in an Oat panel.

### 4. Tip flow
**Purpose:** one-off tip, any amount. No accounts, no subscription.

- **Entry:** the "Leave a tip" pill, present in the header, the tip band and after every
  successful generation.
- **Tip panel** (modal on desktop, sheet on mobile): Cream `#FBF7F1` surface, 20px
  radius, 1px `#E4DACE`, 40px padding, max-width 460px, centred, backdrop
  `rgba(43,39,36,0.4)`.
  - Heading: Lora 600 30px, "Tips keep the bench lit."
  - Body: Sora 400 15px `#6B5F55`, "DeckCraft is free. If it saved you an evening, leave
    what that's worth."
  - Amount row: three preset chips `$5` / `$15` / `Other`, 999px radius, White fill,
    1px `#E0D2C2`, Sora 500 14px `#4A423B`; selected chip gets `#A9472C` fill, white
    text, no border. "Other" swaps the row for a currency field (White, 12px radius,
    Sora 500 20px, prefix "$" in `#6E6459`).
  - Optional note field: one line, placeholder "Say hi (optional)", 96 char limit.
  - Primary button, full width: "Leave $15" — label reflects the chosen amount.
  - Fine print: Sora 12px `#6E6459`, "One-off payment. No account, no subscription."
- **Validation:** minimum $1, maximum $500, numeric only, two decimal places. Error text
  Sora 12px in `#A9472C` below the field; the field border turns `#A9472C`. Never shake
  or flash.
- **Success:** the panel content is replaced in place (no route change) with the Sage
  `#5C6B52` mark, Lora 600 30px "Got it, thank you.", Sora 400 15px "Go win the room.",
  and a text link "Back to the deck". Auto-dismiss after 6s or on click.
- **Failure:** keep the entered amount, show Sora 14px `#A9472C` "That didn't go through.
  Nothing was charged." and leave the button enabled to retry.

### 5. Thank-you / receipt page
Only needed if the payment provider redirects. Same content as the success state, centred
in a 520px column on Cream, with the lockup above it at 40px mark height.

---

## Interactions & Behavior
- **Transitions:** 160ms `ease-out` on colour, border-colour and opacity. 240ms
  `cubic-bezier(0.2,0,0.2,1)` on the tip panel entrance (fade + 8px rise). Nothing longer
  than 300ms; no bounce, no scale-in.
- **Hover:** primary button darkens `#A9472C` → `#8E3A22`. Outlined chips change border
  to `#C4593B`, fill unchanged. Style cards change border to `#C4593B`. Text links change
  colour to `#A9472C`, no underline appears or disappears on hover.
- **Focus:** 2px `#A9472C` outline at 2px offset on every interactive element. Never
  remove the outline.
- **Style-card scroller** on landing uses scroll-snap; no arrows, no autoplay.
- **Loading:** progress line only (see composer). No skeletons on the marketing page.
- **Responsive:** single breakpoint set at 900px and 640px. Below 640px, page gutters drop
  to 20px, hero padding to 32px, H1 to 32px, Display to 36px. Buttons go full width.
- **Reduced motion:** honour `prefers-reduced-motion` — drop the panel rise and the
  progress animation, keep colour changes.

## State Management
| State | Type | Notes |
|---|---|---|
| `brief` | string | The user's description; required before generate |
| `selectedStyle` | one of the eight theme ids | Default `modern` |
| `options` | `{ slides?: number, audience?: string }` | From the chips; optional |
| `generation` | `idle \| building \| ready \| error` | Drives the composer button and result card |
| `deckFile` | `{ url, filename, sizeBytes }` | Set when `generation === 'ready'` |
| `tipPanel` | `closed \| open \| processing \| success \| error` | Independent of `generation` |
| `tipAmount` | number (cents) | Presets 500 / 1500, or custom; validated 100–50000 |
| `tipNote` | string ≤96 chars | Optional |

No auth state. No persisted user record is required for the core flow; persist nothing
client-side except `selectedStyle` (localStorage) so a returning user keeps their style.

## Design Tokens
See `tokens.css` for the brand tokens and `deck-themes.json` for the eight deck themes.
Spacing scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px. Radii: 12, 14, 16, 20, 999.
Type scale: 11, 12, 13, 14, 15, 16, 17, 22, 23, 30, 42, 50.

## Assets
- **Fonts:** Lora and Sora, both from Google Fonts. Self-host in production
  (Lora 400/500/600 + italic 400, Sora 300/400/500/600). The deck-style previews also use
  Instrument Serif, Spectral, Archivo, Libre Franklin and IBM Plex Mono — these belong to
  the **deck themes**, not the brand, and are only needed where previews render.
- **Mark:** pure CSS/SVG, no image asset. Three bars in a rounded square as specified above.
- **Imagery:** none used. The design deliberately has no photography or illustration;
  the "Warm / handmade" deck theme calls for photography, which is the user's own content.
- **Icons:** none required. Any needed later should be 1.5px stroke, 20px, `#4A423B`.

## Files
| File | What it is |
|---|---|
| `DeckCraft Brand.dc.html` | The design board. Option `1b` = the live brand. `1c` = the eight deck-style cards, fully mocked. `1a`, `2a`, `2b` = rejected explorations, ignore. |
| `tokens.css` | Brand design tokens as CSS custom properties |
| `deck-themes.json` | The eight deck themes, machine-readable |

Open the board in a browser to inspect exact computed values.
