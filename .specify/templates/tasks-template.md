---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped into an ordered **Iteration Ladder**. Each iteration is a vertical slice of user-visible value that runs end-to-end. Iteration 1 is the smallest user-visible slice and absorbs whatever bootstrap is required to run it; each subsequent iteration adds one user story on top. Stopping at any iteration leaves a working product.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3).
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  CRITICAL STRUCTURAL RULES:

  1. Iterations form an ordered ladder. Each iteration is a vertical slice
     of user-visible value that runs end-to-end. There is no separate
     "scaffolding" iteration — bootstrap work is absorbed into the first
     iteration that needs it, in service of delivering the first user-visible
     slice.

  2. Each iteration MUST correspond to exactly one user story (in priority
     order: P1 → P2 → P3 → ...) and MUST end with that story working
     end-to-end on top of the previous iteration.

  3. Every iteration ends with the project in a running state with the new
     story exercisable end-to-end. Never leave the project in a non-runnable
     state between iterations.

  4. The final task of every iteration is a brief user-perspective summary:
     the agent states in plain language what the user can now do with the
     product. The agent does NOT run the product itself — the user drives
     verification.

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Iteration 1: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

**Exit criterion**: User Story 1 works end-to-end. The project runs. This iteration absorbs whatever bootstrap is required to make it runnable.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T001 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T002 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1

- [ ] T003 Create project structure per implementation plan
- [ ] T004 Initialize [language] project with [framework] dependencies
- [ ] T005 [P] Configure linting and formatting tools
- [ ] T006 Setup foundational infrastructure required to run User Story 1 (e.g. routing, entry point, base layout, database connection)
- [ ] T007 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T008 [P] [US1] Create [Entity2] model in src/models/[entity2].py
- [ ] T009 [US1] Implement [Service] in src/services/[service].py (depends on T007, T008)
- [ ] T010 [US1] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T011 [US1] Add validation and error handling
- [ ] T012 [US1] Provide a brief user-perspective summary of what the user can now do end-to-end. Do not run the project — the user drives verification.

**Checkpoint**: User Story 1 works end-to-end. The user exercises Iteration 1 and decides whether to continue, adjust, or stop.

---

## Iteration 2: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

**Exit criterion**: The project runs end-to-end with User Story 2 exercisable on top of Iteration 1.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T013 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T014 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T015 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T016 [US2] Implement [Service] in src/services/[service].py
- [ ] T017 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T018 [US2] Integrate with User Story 1 components (if needed)
- [ ] T019 [US2] Provide a brief user-perspective summary of what the user can now do end-to-end. Do not run the project — the user drives verification.

**Checkpoint**: User Stories 1 and 2 are exercisable end-to-end. The user exercises Iteration 2 and decides whether to continue.

---

## Iteration 3: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

**Exit criterion**: The project runs end-to-end with User Story 3 exercisable on top of Iteration 2.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T020 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T021 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T022 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T023 [US3] Implement [Service] in src/services/[service].py
- [ ] T024 [US3] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T025 [US3] Provide a brief user-perspective summary of what the user can now do end-to-end. Do not run the project — the user drives verification.

**Checkpoint**: All three user stories are exercisable end-to-end. The user exercises Iteration 3 and decides whether to continue.

---

[Add more user-story iterations as needed, following the same pattern — one user story per iteration, always running end-to-end at the end.]

---

## Final Iteration: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories. Only run after all user-story iterations are done.

**Exit criterion**: All improvements applied; the project still runs end-to-end.

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Provide a brief user-perspective summary of what the user can now do end-to-end. Do not run the project — the user drives verification.

---

## Dependencies & Execution Order

### Iteration Dependencies

- **Iteration 1 (P1 / MVP)**: No prior iteration dependencies. Absorbs bootstrap. Must run end-to-end with User Story 1 exercisable.
- **Iteration 2 (P2)**: Depends on Iteration 1. Adds User Story 2. Project still runs end-to-end.
- **Iteration 3 (P3)**: Depends on Iteration 2. Adds User Story 3. Project still runs end-to-end.
- **Final Iteration (Polish)**: Depends on all desired user-story iterations being complete.

### Within Each Iteration

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- The final task of every iteration MUST be a brief user-perspective summary of what the user can now do with the product
- The user, not the agent, runs and verifies the product between iterations
- Do not move to the next iteration until the user has exercised the current one

### Parallel Opportunities

- Tasks marked [P] within a single iteration can run in parallel
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Iterations themselves are sequential — do not parallelize across iterations (each iteration builds on the previous)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First

1. Complete Iteration 1: smallest user-visible slice including bootstrap → runs end-to-end (MVP!)
2. **STOP and EXERCISE**: user runs Iteration 1, confirms it works, decides whether to continue or refine the plan

### Incremental Delivery

1. Complete Iteration 1 → user exercises it (MVP)
2. Complete Iteration 2 → user exercises it
3. Complete Iteration 3 → user exercises it
4. Each iteration adds a vertical slice without breaking the previous ones. Stop at any iteration and you still have a working product with one or more user stories exercisable.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Every iteration runs end-to-end; the user can exercise all user stories up to and including N
- Verify tests fail before implementing (if tests are used)
- Commit after each task or logical group
- Stop at any iteration checkpoint; the user exercises it and decides the next move
- Avoid: vague tasks, same-file conflicts, cross-iteration dependencies that leave the project non-runnable between iterations
