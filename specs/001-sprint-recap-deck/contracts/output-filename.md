# Contract: output filename pattern

Specified verbatim in FR-003. This file pins down the corner cases the
implementation must honour.

## Pattern

```text
<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx
```

- `<template-stem>` = the chosen template file's basename without its
  `.pptx` extension. Case preserved.
- `<sprint-name>` = the YouTrack sprint's `name` field, sanitized for
  filesystems (rules below).
- `<sprint-end-YYYY-MM-DD>` = the sprint's end date in ISO format
  (`{:%Y-%m-%d}`), zero-padded.

## Sanitization rules for `<sprint-name>`

Per research §R4:

1. Replace each character that is not in `[A-Za-z0-9._-]` with `_`.
2. Collapse runs of multiple `_` into a single `_`.
3. Strip leading and trailing `_`.
4. If the result is empty (e.g. the sprint name was nothing but
   non-ASCII punctuation), substitute the sprint's YouTrack
   `idReadable` slug (e.g. `121-318`).

Examples (purely illustrative):

| Sprint name | Sanitized |
|---|---|
| `Sprint 42` | `Sprint_42` |
| `Q2/2026 — Recap` | `Q2_2026_Recap` |
| `R&D — week 18` | `R_D_week_18` |
| `🚀 launch sprint` | `launch_sprint` |
| `🎉🎉🎉` | `<idReadable fallback>` |

## Determinism guarantee

For a fixed `(template, sprint)`, the produced filename MUST be
byte-identical across runs and across operating systems. This is what
lets FR-004's overwrite prompt actually fire on a re-run.

## Sibling log file

The per-run log is `<output-stem>.log` in the same folder, where
`<output-stem>` is everything before the final `.pptx`. The log
filename is therefore equally deterministic.

## Path resolution

The output is always inside the working folder. The program never
writes outside that folder unless the user picks "save under a
different name" at the FR-004 overwrite prompt and explicitly types or
selects a different destination — in which case the program asks
again before writing if that destination already exists, and logs the
final destination.
