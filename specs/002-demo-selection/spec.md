# 002 — Demo Selection

## Summary

Replace the two-category agenda classification (Resolved / Unresolved) with
three categories: **Resolved, demo** · **Resolved, no-demo** · **Unresolved**.
After issues are fetched from YouTrack and classified, a mandatory interactive
step lets the user select which resolved issues will be demoed. The selection
UI is a curses TUI in console mode and a checkbox window in tkinter mode.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Template tokens | `{{AGENDA_DEMO}}`, `{{AGENDA_NO_DEMO}}`, `{{AGENDA_OPEN}}` — breaking change, replaces `{{AGENDA_FINISHED}}` | Clean semantics; no backwards-compat complexity |
| Default selection state | All resolved issues default to **unchecked** (no-demo) | Team typically demos a subset; opt-in saves clicks |
| Terminal UI | `curses`-based interactive list (stdlib) | Better UX than numbered input; no new dependency |
| Tkinter UI | Scrollable `Checkbutton` list in a `Toplevel` | Familiar checkbox pattern |
| Selection mandatory | Always shown; no skip flag | Feature is the point of this iteration |
| Architecture | Approach A — picker lives in `prompts.py`, `AgendaPlan` grows `demo`/`no_demo` fields replacing `finished` | Follows existing module responsibilities |

## Model changes — `models.py`

`AgendaPlan` replaces `finished: list[SprintIssue]` with:

```python
@dataclass
class AgendaPlan:
    demo: list[SprintIssue]          # resolved, user selected for demo
    no_demo: list[SprintIssue]       # resolved, not selected
    open: list[SprintIssue]          # unresolved (unchanged)
    unfiltered_count: int = 0
    filtered_count: int = 0
    collapsed_subtask_count: int = 0
```

**Invariant:** `len(demo) + len(no_demo) + len(open) == filtered_count - collapsed_subtask_count`.

## Classification changes — `classify.py`

`build_agenda_plan()` continues to split by `resolved_at` (FR-010). All
resolved issues land in `no_demo`; `demo` is left empty. The orchestrator
populates `demo` after the user interacts with the picker.

```python
return AgendaPlan(
    demo=[],
    no_demo=finished,
    open=open_,
    ...
)
```

Classify remains pure logic with no UI dependency.

## Demo picker — `prompts.py`

New function:

```
prompt_demo_selection(finished: Sequence[SprintIssue]) -> set[str]
```

Returns `id_readable` values the user marked for demo. Both UI variants show
issue titles with their readable IDs for context.

### Tkinter variant

A `Toplevel` window with a scrollable column of `Checkbutton` widgets, one per
resolved issue, all unchecked by default. OK and Cancel buttons. Cancel raises
`ValueError` (abort without writing files — consistent with other cancel
paths).

### Console / curses variant

Full-screen curses pad. Each line: `[ ] PROJ-123  Issue title` (or `[x]` when
toggled). Arrow keys navigate, Space toggles, Enter confirms, `q` cancels
(raises `ValueError`).

### Edge case

If `finished` is empty (nothing resolved), skip the picker and return an empty
set.

## Orchestration — `app.py`

After `classify.build_agenda_plan()`, the orchestrator calls the picker and
splits the lists:

```python
plan = classify.build_agenda_plan(issues, settings.issue_type_filter)

if plan.no_demo:
    demo_ids = prompts.prompt_demo_selection(plan.no_demo)
    plan.demo = [i for i in plan.no_demo if i.id_readable in demo_ids]
    plan.no_demo = [i for i in plan.no_demo if i.id_readable not in demo_ids]
```

`_write_cross_reference` logs three categories: demo, no-demo, open.

## Template token contract — `deck.py`

### Removed

- `{{AGENDA_FINISHED}}` — no longer recognized.

### New / changed

| Token | Purpose | Cardinality | Required |
|---|---|---|---|
| `{{AGENDA_DEMO}}` | Resolved issues selected for demo | exactly 1 | Yes |
| `{{AGENDA_NO_DEMO}}` | Resolved issues not selected for demo | exactly 1 | Yes |
| `{{AGENDA_OPEN}}` | Unresolved issues | exactly 1 | Yes (unchanged) |

Validation: missing required token → error naming it; duplicate agenda token →
error. Same pattern as before.

`_write_agenda` is unchanged — it already accepts a text frame and a list.
Only the token-to-list mapping changes:

```
{{AGENDA_DEMO}}    → plan.demo
{{AGENDA_NO_DEMO}} → plan.no_demo
{{AGENDA_OPEN}}    → plan.open
```

### Migration

Old templates with `{{AGENDA_FINISHED}}` get:
`"Required template tokens missing: {{AGENDA_DEMO}}, {{AGENDA_NO_DEMO}}"`.
The user replaces the single finished text frame with two text frames.

## Test changes

- **`test_classify.py`:** Assertions reference `demo` (empty) and `no_demo`
  instead of `finished`.
- **`test_deck_tokens.py`:** Template fixture uses the new tokens. Validation
  tests cover new names and cardinality.
- **`test_prompts.py`:** New tests for the demo picker — empty-list edge case,
  function contract.
- **`_build_template.py`:** Generates a three-token template.
