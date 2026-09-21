# Deck design system — "Deep Teal"

The researcher's preferred deck identity, reverse-engineered from an approved
16:9 deck he wrote himself and confirmed as the house style on 2026-09-17.

**Use this as the default for any new deck** unless he asks for something else.
A reference deck showing every archetype rendered is kept machine-local at
`system/config/local/presentation-templates/` — it is not in the repository,
because a real deck carries real names and real field data.

---

## Why this file exists

The deck's identity is **not in its PowerPoint theme.** The theme is stock Office
(`accent1 #4472C4`, Calibri). Every distinctive thing is hand-built shape by
shape on the slides, and there is exactly one slide layout. So a deck cannot
inherit this look by opening the template and typing — the look has to be
rebuilt from the tokens and archetypes below, on each slide.

That is the whole reason a spec beats a `.potx` here.

---

## Canvas

| Property | Value |
|---|---|
| Slide size | 13.333 × 7.5 in (16:9, 1920 × 1080 px at 144 dpi) |
| Title case | Sentence case for titles. UPPERCASE only for eyebrows and labels. |

## Colour tokens

Deep teal ink with a single amber accent on pale blue-grey surfaces. The amber
is the only warm colour on the page; it is spent on one thing per slide.

| Token | Hex | Role |
|---|---|---|
| `ink` | `#0B3744` | Primary text, dark slide grounds, the dominant colour |
| `ink-deep` | `#16323C` | Deepest ground, section dividers |
| `teal` | `#12566E` | Secondary headings, structural rules |
| `teal-mid` | `#0E4255` | Gradient partner for dark grounds |
| `cyan` | `#2E8FA6` | Active state, the "lit" step in a sequence, links |
| `amber` | `#E3A23A` | THE accent — one use per slide, never decorative |
| `amber-deep` | `#C2811F` | Amber text on light grounds (contrast) |
| `amber-ink` | `#3A2705` | Text sitting on an amber fill |
| `muted` | `#5E7682` | Captions, footers, secondary labels |
| `line` | `#8FAEB7` | Hairline rules, table borders |
| `line-soft` | `#AFD0D9` | Card borders on tinted grounds |
| `tint-1` | `#F6F9FA` | Lightest surface |
| `tint-2` | `#EAF1F3` | Default card fill |
| `tint-3` | `#DCEAEE` | Raised / emphasised card |
| `tint-4` | `#D5E0E4` | Table header row |
| `tint-cool` | `#EAFBFD` | Cool highlight, used sparingly |
| `paper` | `#FFFFFF` | Slide ground |

**Rule:** the amber is the loudest thing on the slide. If two things are amber,
neither is emphasised. Semantic status colours are not part of this palette — if
a slide needs good/warning/critical, derive them and say so, do not repurpose the
amber.

## Typography

| Role | Face | Sizes used |
|---|---|---|
| Display / headings | **Trebuchet MS** | 26–50 pt |
| Body / data | **Calibri** | 9–15 pt |

The real type scale in use, in points:
`9 · 10 · 11 · 12 · 13 · 14 · 15 · 16 · 18 · 20 · 26 · 30 · 36 · 40 · 44 · 50`

Most text lives at **10–14 pt** — this is a dense, read-at-the-table deck, not a
stand-and-deliver deck. Do not inflate body text to 18 pt "for legibility"; it
breaks the archetypes below, which assume a lot of content fits.

Eyebrows are uppercase, letter-spaced, 9–10 pt, in `muted` or `cyan`.

---

## Slide archetypes

Seven shapes. A new deck should be assembled from these, not invented.

### 1 · Title
Dark `ink` ground. Uppercase eyebrow in `amber` · big title · one-line
sub-title in `cyan` · a lede paragraph of 1–2 sentences setting the question the
deck answers · byline and affiliation at the foot in `muted`.

### 2 · Part divider
Dark ground. `PART n OF m` eyebrow · part title · one-sentence lede. Then the
full agenda as numbered items `1 2 3 4`, with the **current part lit in amber**
and the rest in `muted`. The same agenda block repeats on every divider, so the
reader always knows where they are.

### 3 · Content
White ground. Uppercase eyebrow in `muted` · sentence-case title · the content
block · footer rule with deck name left and slide number right.

The content block is one of: a row of 2–4 cards (`tint-2` fill, `line-soft`
border), a two-column compare, or a left-to-right flow of steps with arrows.

### 4 · Indicator
A numbered badge (e.g. `4.1`) in `amber` sits beside the title. Below it, a
tiered milestone table — rows are years, columns are **Minimum / Expected /
Optimal**, ambition increasing left to right, header row in `tint-4`.
Then a `WHERE WE ARE` panel in `tint-3` giving the honest current state.

The pairing is the point: the plan and the reality sit on the same slide.

### 5 · Evidence
A single big figure set in Trebuchet at 36–50 pt in `ink`, with its denominator
directly beneath it in `muted` — a count never appears without what it is out of.
Supporting counts run beside it as small chips on `tint-2`.

### 6 · Compare
Two columns under a shared question, e.g. two strategies or two chemistries. Each
column gets a heading, 3–5 bullets, and a one-line verdict. Neither column is
styled as the winner; the verdict line carries the judgement.

### 7 · Closing
Dark ground, a short list of what the work delivers — statements, not bullets of
nouns — and one closing sentence that names the decision the audience now faces.

---

## Standing habits in this deck style

- **A `Key message` strip** closes most content slides: one sentence, on
  `tint-2`, stating what the slide proves. Not a summary of the slide — the
  claim the slide earns.
- **Footers** carry the deck name and slide number, in `muted`, 9 pt, under a
  hairline in `line`.
- **Numbers carry their denominator.** `78 / 969` not `8%` alone; where a
  percentage is given, the count follows it.
- **Honest status.** Where a milestone is not met, the slide says so in the
  `WHERE WE ARE` panel rather than omitting it. This deck style is built for
  reporting to funders and partners who will check.
