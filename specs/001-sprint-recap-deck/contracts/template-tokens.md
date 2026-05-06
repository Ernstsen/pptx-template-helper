# Contract: pptx template tokens

The program treats the user's pptx template as read-only and identifies
fill points via **named text tokens** that the user inserts into the
template's text frames once. Token recognition is exact-match on the
literal token strings — no fuzzy matching, no regex inference, no
shape-name conventions (FR-009).

## Token list

| Token | Purpose | Cardinality | Required? |
|---|---|---|---|
| `{{SPRINT_START}}` | Sprint start date, long-form English | ≥ 1 occurrence | Required (FR-009). |
| `{{SPRINT_END}}` | Sprint end date, long-form English | ≥ 1 occurrence | Required (FR-009). |
| `{{RECAP_DATE}}` | Recap-meeting date — same as sprint end (FR-009) | 0 or more | Optional (FR-009 / spec edge case). |
| `{{AGENDA_FINISHED}}` | Bulleted list of finished issue titles | exactly 1 occurrence | Required (FR-010). |
| `{{AGENDA_OPEN}}` | Bulleted list of open issue titles | exactly 1 occurrence | Required (FR-010). |

If `{{AGENDA_FINISHED}}` or `{{AGENDA_OPEN}}` appears more than once,
the program reports an explicit error and aborts (it cannot infer which
occurrence "wins").

If a required token is missing, the program reports a clear error
naming the missing token(s) and does not produce a partial deck
(spec edge case "A required placeholder token … is missing").

## Where each token may live

Tokens are recognized **inside text frames** anywhere in the deck:
slide bodies, slide titles, slide footers, text boxes, table cells,
group-shape descendants. They are NOT recognized inside slide masters
or layouts (the program does not modify masters or layouts), nor
inside speaker notes, nor inside chart text.

## How tokens are filled

### Date tokens (`{{SPRINT_START}}`, `{{SPRINT_END}}`, `{{RECAP_DATE}}`)

- Replacement is at the **paragraph** level: the paragraph that contains
  the token is preserved (formatting kept), and the token substring
  inside it is replaced in-place. Other text in the same paragraph
  surrounding the token is preserved.
- The substituted value uses the long-form English rendering defined
  in research §R5: day with no leading zero, full English month name,
  four-digit year, single spaces (`6 May 2026`).

### Agenda tokens (`{{AGENDA_FINISHED}}`, `{{AGENDA_OPEN}}`)

- The token is expected to be the **sole content** of its text frame
  (the user puts it inside an empty bullet text frame in their
  template). The program clears the frame, then writes one paragraph
  per issue title in the chosen sort order (FR-020).
- Body properties of the text frame (`bodyPr`, including
  `normAutofit` / `spAutoFit`, anchor, margins, word wrap) are NOT
  modified. PowerPoint computes autofit at render time from those
  flags, which is exactly the FR-010 behavior the spec specifies
  ("delegates visual fit to the autofit behaviour of the template's
  text frames").
- The first written paragraph reuses the existing first run's
  formatting (font, size, color, bullet style) where present, so the
  user's chosen bullet appearance carries over. Subsequent paragraphs
  are added with `text_frame.add_paragraph()` and inherit text-frame
  defaults.
- If the user wants extra prose around an agenda token (e.g.
  "Finished items:" above the list), they place that prose in a
  *separate* text frame; the program does not co-mingle.

## Examples (informational)

A typical template slide layout that satisfies the contract:

- A title text frame containing `Sprint {{SPRINT_START}} – {{SPRINT_END}}`.
- An optional subtitle text frame containing
  `Recap meeting: {{RECAP_DATE}}`.
- An "Agenda" slide with two columns: the left column is a bulleted
  text frame whose only content is `{{AGENDA_FINISHED}}`; the right
  column is a bulleted text frame whose only content is
  `{{AGENDA_OPEN}}`.

## Out of scope for v1

- Token-driven image insertion.
- Tokens inside speaker notes or chart text.
- Tokens spread across multiple runs that PowerPoint has split (e.g.
  spell-check or autocorrect inserting a run boundary mid-token). The
  program coalesces a paragraph's runs into the paragraph's plain text
  for substitution and writes the result back as a single run; this
  loses inline formatting *within* the paragraph but preserves
  paragraph-level formatting. This is the documented trade-off; the
  agenda regions and date strings rarely need inline formatting.
