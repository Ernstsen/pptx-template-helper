<!--
SYNC IMPACT REPORT
==================
Version change: (uninitialized template) → 1.0.0
Rationale: Initial ratification. MAJOR baseline established for a fresh project; all
principles, sections, and governance are introduced for the first time.

Modified principles:
- (none → I.) Incremental Delivery with Frequent Feedback (NON-NEGOTIABLE)
- (none → II.) Minimal Dependency Footprint
- (none → III.) Folder-as-Context Execution
- (none → IV.) Conversational Fallback for Ambiguity
- (none → V.) Standard Python Packaging & Portability

Added sections:
- Core Principles (I–V)
- Technology Stack & Runtime Constraints
- Development Workflow
- Governance

Removed sections: none (template was unpopulated).

Templates requiring updates:
- ✅ .specify/templates/constitution-template.md — already aligned (Principle I matches
  the canonical template wording; remaining principles populated below).
- ✅ .specify/templates/plan-template.md — Constitution Check gate is generic
  ("[Gates determined based on constitution file]") and remains compatible; future
  /speckit-plan runs MUST evaluate against Principles I–V explicitly.
- ✅ .specify/templates/spec-template.md — no constitution-specific sections; aligned.
- ✅ .specify/templates/tasks-template.md — Iteration Ladder structure already encodes
  Principle I; no edits required.
- ✅ .specify/templates/checklist-template.md — generic; aligned.
- N/A .specify/templates/commands/*.md — directory does not exist in this project.

Follow-up TODOs: none.
-->

# pptx-helper Constitution

## Core Principles

### I. Incremental Delivery with Frequent Feedback (NON-NEGOTIABLE)

The plan is authored as an ordered ladder of iterations. Each iteration is a small,
vertical slice of user-visible value that runs end-to-end. Iterations are ordered so
that any stopping point leaves a coherent, working product. The next iteration is not
implemented until the current one has been exercised and feedback received; the plan
itself may be refined between iterations when running code reveals something the plan
did not anticipate. At the end of each iteration the agent stops and provides a brief
user-perspective summary of what is now possible; it does not run or verify the
increment itself — that step is the user's.

### II. Minimal Dependency Footprint

Third-party libraries MUST be added only when they meet BOTH of the following bars:

- **Broadly recognized**: the library is widely used in mainstream Python (e.g., on
  PyPI with substantial adoption, present in well-known stacks, documented in
  community references). Niche, abandoned, or single-author packages are disallowed
  unless explicitly justified.
- **High value vs. hand-rolling**: the functionality the library provides would be
  materially harder, riskier, or more error-prone to write directly in the project
  (e.g., parsing a complex binary format, cryptography, GUI toolkits). Convenience
  wrappers around a few lines of standard-library code are NOT sufficient
  justification.

The Python standard library is the default. Every dependency added to
`requirements.txt` MUST be accompanied, in the plan or PR description, by a one-line
justification covering both bars above. **Rationale**: keeps the project auditable,
reduces supply-chain risk, simplifies the double-click runtime, and prevents the slow
accumulation of incidental dependencies.

### III. Folder-as-Context Execution

The program MUST be runnable by double-clicking it inside an arbitrary folder, and
when launched this way it MUST treat the folder that contains it (or that it was
launched from) as its working context — i.e., the source of input files and the
target for outputs, unless the user explicitly redirects it. No prior installation
step, configuration file, or working-directory tweak may be required for the default
flow. **Rationale**: the tool is intended for non-developer users who drop the
executable/script into a working folder; "double-click and it works on this folder"
is the contract.

### IV. Conversational Fallback for Ambiguity

When the program cannot infer a required input from the folder context, it MUST
prompt the user interactively rather than failing or assuming silently. Prompts are
delivered through a simple UI or console interface — whichever is appropriate to the
launch mode — and MUST:

- State plainly what is missing and why it is needed;
- Offer a sensible default where one exists, so the user can accept by pressing
  Enter / clicking OK;
- Never block on unattended runs without making the prompt visible (no silent
  hangs).

Hidden assumptions are forbidden; if behaviour depends on a guess, that guess MUST
be surfaced to the user. **Rationale**: end users will not read source code or
config files to figure out why a run failed; the program itself is the UI.

### V. Standard Python Packaging & Portability

The project is a Python application managed via a virtual environment (`venv`) with
dependencies pinned in `requirements.txt`. The following constraints apply:

- A `requirements.txt` at the repository root is the single source of truth for
  third-party dependencies. No `setup.py`, `pyproject.toml` build backend, Poetry
  lockfile, or alternative manager is introduced unless a future amendment changes
  this rule.
- Setup MUST be reproducible from a clean checkout via documented commands of the
  form: create venv → activate → `pip install -r requirements.txt` → run entry
  point.
- The default entry point MUST be a single-file or clearly-named script that a
  non-developer can launch by double-clicking on the target platform (e.g., `.py`
  associated with Python, or a thin launcher shim if needed).
- Code MUST run on a current, supported Python release (3.11+) and avoid
  platform-specific calls that would prevent the double-click flow on the user's
  primary OS.

**Rationale**: low-friction onboarding for users who are not Python developers, and
a packaging story simple enough that the maintainer can reason about it without
tooling specialists.

## Technology Stack & Runtime Constraints

- **Language**: Python 3.11 or later.
- **Dependency manifest**: `requirements.txt`, with each dependency justified per
  Principle II.
- **Environment**: a project-local `venv/` (gitignored). Global installs are
  discouraged; the README MUST document the venv-based setup as the canonical path.
- **Distribution**: source-level — the user obtains the project folder and runs the
  entry point. Packaging into a single binary (e.g., PyInstaller) is OUT OF SCOPE
  for v1 and requires an amendment to introduce.
- **UI surface**: keep prompts simple. A console prompt is the default; a minimal
  GUI dialog (via the standard library, e.g., `tkinter`) is acceptable when the
  launch context implies it (e.g., double-click on Windows where no console is
  visible). Heavy UI frameworks are disallowed without amendment.
- **Filesystem assumption**: the program operates on the folder it is launched from
  by default. It MUST NOT write outside that folder without explicit user
  confirmation.

## Development Workflow

- **Planning**: every feature MUST go through `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` before implementation. The tasks file MUST follow the Iteration
  Ladder structure mandated by Principle I.
- **Constitution Check**: each plan MUST include a Constitution Check section that
  evaluates the proposed work against Principles I–V and declares either compliance
  or a justified deviation in the plan's Complexity Tracking table.
- **Iteration cadence**: the agent stops at the end of each iteration and hands off
  to the user for verification (Principle I). The agent does NOT run or test the
  product on the user's behalf at iteration boundaries.
- **Dependency reviews**: any change to `requirements.txt` is treated as a
  governance-relevant edit and MUST carry the per-dependency justification in the
  commit message or PR description.
- **Code Health**: per global agent guidance, AI-touched code is held to Code
  Health 10.0 and is safeguarded before commit when CodeScene tooling is available
  in the working environment.

## Governance

- **Authority**: this constitution supersedes ad-hoc preferences and prior
  conventions. Where a plan, spec, task list, or PR conflicts with the
  constitution, the constitution wins unless the conflict is recorded as a
  justified deviation in the plan's Complexity Tracking section.
- **Amendments**: amendments are made by editing this file via the
  `/speckit-constitution` workflow, which MUST regenerate the Sync Impact Report at
  the top of the file and propagate any required edits to the templates listed in
  that report.
- **Versioning policy** (semantic):
  - **MAJOR**: a principle is removed, redefined incompatibly, or governance rules
    change in a way that invalidates prior plans.
  - **MINOR**: a new principle or section is added, or an existing one is
    materially expanded.
  - **PATCH**: clarifications, wording, typo fixes, or non-semantic refinements.
- **Compliance review**: every PR review MUST verify that changes do not violate
  Principles I–V; reviewers reject or request changes when violations are
  unjustified.
- **Runtime guidance**: agent-specific runtime guidance lives alongside this file
  (e.g., `CLAUDE.md`, `AGENTS.md`) when introduced; such files MUST defer to this
  constitution on any conflict.

**Version**: 1.0.0 | **Ratified**: 2026-05-06 | **Last Amended**: 2026-05-06
