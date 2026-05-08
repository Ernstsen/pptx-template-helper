# 003 — Demo Item Slide Ranges

## Overview

Template authors mark a contiguous range of slides by placing `{{DEMO_ITEM_START}}` in the **speaker notes** of the first slide and `{{DEMO_ITEM_END}}` in the speaker notes of the last slide. For each demo issue, the entire range is cloned, `{{ITEM_TITLE}}` is substituted on every cloned slide, and the original template range is removed.

The feature is fully optional — templates without these tags work exactly as today.

## Tag Placement

Tags live in **slide notes** (the speaker notes pane), not PowerPoint Review-tab comments. python-pptx 1.0.2 has no API for review comments, but has full read/write support for notes via `slide.notes_slide.notes_text_frame.text`.

| Tag                    | Location                               | Purpose           |
| ---------------------- | -------------------------------------- | ----------------- |
| `{{DEMO_ITEM_START}}`  | Speaker notes of first slide in range  | Marks range start |
| `{{DEMO_ITEM_END}}`    | Speaker notes of last slide in range   | Marks range end   |
| `{{ITEM_TITLE}}`       | Any text frame within range slides     | Replaced with issue title |

A range can be a single slide (start and end tags on the same slide) or span multiple slides.

## Processing Order

The expansion runs as a **first pass** inside `render_deck`, before existing token substitution:

1. **Scan** — iterate all slides, read notes, find indices of `{{DEMO_ITEM_START}}` and `{{DEMO_ITEM_END}}`.
2. **Validate** — if neither tag found: skip (silent, backward-compatible). If only one found, or end before start, or multiple ranges: raise an error with a clear message.
3. **Clone** — for each demo issue (in `plan.demo` order), deep-copy the XML of every slide in the range. This includes shapes, text frames, images, layouts, and relationship parts.
4. **Substitute** — in each cloned set, replace `{{ITEM_TITLE}}` with the issue title in all text frames (reusing the existing `_replace_in_paragraph` logic).
5. **Insert** — insert all cloned slide sets at the position of the original range.
6. **Remove** — delete the original template range slides.
7. **Strip tags** — remove `{{DEMO_ITEM_START}}` and `{{DEMO_ITEM_END}}` from the notes of cloned slides so they don't appear in the output.
8. **Continue** — existing date/agenda token substitution runs on the fully expanded slide set.

## Slide Cloning Strategy

`python-pptx` has no built-in slide clone. The implementation will:

- Deep-copy the slide's XML element (`sld` element) via `copy.deepcopy` on the lxml tree.
- Copy associated relationship parts (images, charts, embedded objects) by duplicating the relationship entries and their target parts in the presentation package.
- Preserve the slide layout reference (each clone points to the same `slideLayout`).
- Insert the new slide part into the presentation's `sldIdLst` at the correct position.

This is a known pattern in python-pptx projects and stays within the library's `oxml` layer.

## Edge Cases

| Scenario                                  | Behavior                                                        |
| ----------------------------------------- | --------------------------------------------------------------- |
| No tags in template                       | Silent skip, deck renders as today                              |
| Tags present but `plan.demo` is empty     | Remove the template range entirely (no clones)                  |
| Single-slide range                        | Start and end tags on the same slide's notes — works fine       |
| `{{ITEM_TITLE}}` outside the range        | Left as literal text (not substituted)                          |
| Tags in notes alongside other notes text  | Tags are stripped; surrounding notes text preserved              |
| Multiple ranges                           | Error — only one `{{DEMO_ITEM_START}}`/`{{DEMO_ITEM_END}}` pair allowed |

## Model Changes

None. `AgendaPlan.demo` already contains the ordered list of `SprintIssue` objects. `SprintIssue.title` provides `{{ITEM_TITLE}}`. No new dataclasses needed.

## Module Changes

- **`deck.py`** — new functions: `_find_item_range(slides)` to scan notes for tags, `_clone_slide(presentation, slide)` to deep-copy a slide, `_expand_demo_range(presentation, plan)` to orchestrate the clone/substitute/remove cycle. Called at the top of `render_deck`.
- **`app.py`** — no changes. `plan.demo` is already passed to `render_deck`.
- **Other modules** — no changes.

## Template Token Contract Update

Three new tokens added to the contract:

| Token                  | Location          | Cardinality | Required? |
| ---------------------- | ----------------- | ----------- | --------- |
| `{{DEMO_ITEM_START}}`  | Slide notes       | 0 or 1      | Optional  |
| `{{DEMO_ITEM_END}}`    | Slide notes       | 0 or 1      | Optional  |
| `{{ITEM_TITLE}}`       | Text frames within range | 0 or more | Optional |

## Test Plan

- Template with a 2-slide range and 3 demo issues produces 6 item slides in correct order, titles substituted, tags stripped from notes.
- Template with no range tags renders identically to today.
- Template with only `{{DEMO_ITEM_START}}` (no end) raises a clear error.
- Range present but zero demo issues removes range slides, rest of deck intact.
- Single-slide range works correctly.
- `{{ITEM_TITLE}}` outside range is left as literal text.
- Slide with images/grouped shapes inside range clones correctly.
