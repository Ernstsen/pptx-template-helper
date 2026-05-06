# Agent Runtime Guidance — pptx-helper

This file gives agents (Claude, Copilot, etc.) the running context they
need to be productive in this repository. It defers to the project
constitution at `.specify/memory/constitution.md` on any conflict.

## Project at a glance

- **What it is**: A small Python desktop tool that turns a YouTrack
  sprint into a populated pptx recap deck.
- **Constitution**: `.specify/memory/constitution.md` (v1.0.0). Read
  it before suggesting structural changes; it pins the
  iteration-ladder workflow, the minimal-dependency rule, and the
  folder-as-context launch contract.
- **Workflow**: every feature flows through `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` before code lands.

## Active feature

<!-- SPECKIT START -->
- **Branch**: `001-sprint-recap-deck`
- **Spec**: `specs/001-sprint-recap-deck/spec.md`
- **Plan**: `specs/001-sprint-recap-deck/plan.md`
- **Research**: `specs/001-sprint-recap-deck/research.md`
- **Data model**: `specs/001-sprint-recap-deck/data-model.md`
- **Contracts**: `specs/001-sprint-recap-deck/contracts/`
- **Quickstart**: `specs/001-sprint-recap-deck/quickstart.md`
<!-- SPECKIT END -->

## Conventions worth remembering

- **Iteration handoff**: at the end of each iteration the agent stops
  and writes a one-paragraph user-perspective summary; it does NOT
  run or verify the program on the user's behalf.
- **Dependencies**: `requirements.txt` is the single source of
  truth. Adding a dependency requires the two-bar justification from
  Constitution Principle II in the commit message.
- **Token handling**: `YOUTRACK_TOKEN` is read from the environment
  every run. Never write it to settings, logs, errors, or commit
  messages.
- **Folder-as-context**: the program treats the folder it was
  launched from as the working folder. Do not introduce global
  config or hidden working directories.
