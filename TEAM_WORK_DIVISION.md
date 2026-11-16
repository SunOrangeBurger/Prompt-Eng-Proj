# Three-person work division

Updated: 16 November 2026.

This assigns ownership, handoff, maintenance and presentation of the completed
implementation. Each teammate receives one third of the project ownership,
including implementation knowledge, tests, documentation and demonstration.
The allocation is by responsibility and complexity, not a measurement of past
hours or Git authorship.

| Teammate | Primary area | Allocation |
| --- | --- | ---: |
| Sharanya N (PES2UG24AM150) | Repository understanding, detection and evaluation fixtures | 1/3 |
| Ragul Rajkumar (PES2UG24AM128) | Local LLM repair, validation and human approval safeguards | 1/3 |
| Arun Hariharan (PES2UG24AM126) | IDE frontend, side chat, application orchestration and delivery | 1/3 |

## Sharanya: analysis and detection

Six responsibility blocks:

1. Workspace representation: the multi-repo manifest, dependency edges, repo
   paths, filesystem containment, ignored files and source snapshots.
2. AST analysis: the five detector rule types, issue localization, stable finding
   IDs and distinction between security findings and refactoring opportunities.
3. Repository context: lexical retrieval, related callers/tests, editable-symbol
   localization and read-only symbol metadata supplied to the repair agent.
4. Scenario design: the six-repository fixture architecture, planted ground truth,
   security regression oracles and producer/consumer contracts across 25 tests.
   Coordinate fixture changes with the other two owners below.
5. Detection evaluation: the independent 24-case audit, missed detections, false
   positives, syntax-error behavior, file-size exclusions and reproducible evidence.
6. Analysis documentation and presentation: explain the problem scope, repository
   graph, detected code and the limits of pattern-based discovery.

Primary files: `peogai/workspace.py`, the Issue definition in `peogai/types.py`,
`fixtures/demo/workspace.json`, `scripts/verify_detection.py`, and
`docs/detection-audit.json`.

Primary fixture ownership: `settings-lib` and `records-lib`, their regression
tests, and their downstream test cases in `shop-service`.

Testing/documentation ownership: detection and path-containment portions of
`tests/test_agent.py`; detection-audit sections of `README.md`, `RUN_RESULTS.md`
and `PROGRESS.md`; workspace/retrieval/detection decisions in `DECISIONS.md`.

Demo cases: unsafe settings evaluation and SQL interpolation. Show the original
code, why it is flagged, and examples the current detector misses.

## Ragul: model, repair and validation

Six responsibility blocks:

1. Local model integration: Ollama loopback requests, selectable models,
   structured outputs, response parsing, bounded context and timeout/error handling.
2. Prompting: repair system prompt, rule guidance, diagnosis/fix/risk/verification
   fields, retry feedback and the separate read-only explanation prompt.
3. Patch generation: host-anchored function replacement, exact edits, preservation
   of signatures/decorators, scope checks and the changed-line budget.
4. Validation: syntax compilation, complete test inventory, preservation of passing
   tests, disclosure of existing failures, targeted security tests and static
   regression checks. Own candidate reports and explanation evidence.
5. Human approval safeguards: immutable reviewed bytes, opaque review IDs,
   whole-workspace fingerprints, stale/duplicate approval rejection, atomic
   application and persistent approval/rejection audit records.
6. Repair evaluation: real-model integration checks, simulated reviewer decisions,
   rejection behavior, final 25-test results and residual-risk documentation.

Primary files: `peogai/model.py`, `peogai/engine.py`, `peogai/review.py`, the
Edit/Proposal/Check definitions in `peogai/types.py`, and `scripts/verify_hil.py`.

Primary fixture ownership: `documents-lib` and `pricing-lib`, their regression
tests, and their downstream contract coverage.

Testing/documentation ownership: repair/validation portions of
`tests/test_agent.py`, `tests/test_review.py`, `docs/hil-verification-summary.json`,
and the model/validation/HIL sections of the shared documentation.

Demo cases: path traversal and pricing refactoring. Explain how a candidate is
generated and why passing a simple static rule alone is insufficient to accept it.

## Arun: IDE, side chat and application

Six responsibility blocks:

1. IDE frontend: dark workspace layout, repository explorer, file search/tabs,
   syntax-colored read-only source, line numbers, problem highlights and wrapping.
2. Review interface: source/diff modes, Problems/Validation/Pipeline panels,
   actual evidence display, pending-patch review card and exact-view Apply guard.
3. AI side-chat experience: selected-file context, typed questions, typed repair
   constraints, conversation rendering, safe Markdown-like display, prompt
   inspection and clear separation of Ask, Propose, Apply and Reject.
4. Local application: HTTP routes, loopback/host/origin/action-token checks,
   request bounds, controller state, worker threads and operation serialization.
   Integrate Ragul's model and approval functions without bypassing their gates.
5. Demo lifecycle: launcher/CLI commands, pristine reset behavior, pending-review
   invalidation, application state, event delivery and result-history integration.
6. Delivery and walkthrough: desktop browser verification, screenshots, packaging,
   Git delivery, startup instructions and progress/decision/result documentation.

Primary files: `peogai/frontend/*`, `peogai/server.py`, `peogai/demo.py`,
`peogai/cli.py`, `peogai/__main__.py`, `run_demo.py`, `pyproject.toml` and `.gitignore`.

Primary fixture ownership: `notifications-lib` and `shop-service`. Coordinate
`shop-service` integration tests with Sharanya and Ragul, who own the relevant
upstream contracts.

Testing/documentation ownership: `tests/test_chat.py`, `tests/test_server.py`,
`tests/test_demo.py`, IDE/browser evidence and screenshots, README startup/demo
instructions, and assembly of the shared progress/decision/run-result records.

Demo cases: notification boolean and empty-list refactoring. Demonstrate a typed
side-chat request, the proposed patch, explicit approval/rejection, and clean reset.

## Integration boundaries and shared duties

| Handoff | Producer | Consumer | Required contract |
| --- | --- | --- | --- |
| Findings and retrieved context | Sharanya | Ragul | Stable issue IDs, file/line/rule, editable function and relevant tests |
| Validated proposal and evidence | Ragul | Arun | Diagnosis, diff, risk, executed checks and a review-bound candidate |
| User question or repair request | Arun | Ragul | Selected-file context, explicit request and no implicit application |
| Human decision | Arun | Ragul | Exact pending review ID and optional reason; backend enforces freshness |
| Demo fixtures and downstream tests | All three, two repos each | Entire pipeline | Reproducible reset and 25-test contract suite |

Every owner maintains the tests and documentation for their module. Arun
assembles the shared documents; Sharanya and Ragul supply and check their sections.
All three participate in integration, review and the final rehearsal equally.

Cross-review rotation: Sharanya reviews Ragul's changes, Ragul reviews Arun's
changes, and Arun reviews Sharanya's changes. Changes spanning modules receive
review from both affected owners.

## Equal presentation and demonstration split

For a 12-minute presentation, allocate approximately four minutes each:

| Speaker | Explain | Show |
| --- | --- | --- |
| Sharanya | Problem, repo graph, detection and honest coverage limits | Findings, source locations, six planted cases and the independent audit |
| Ragul | Ollama prompting, constrained repairs, validation and approval safeguards | Candidate explanation, security-test evidence, scope/signature gates and stale-review protection |
| Arun | IDE integration, side chat, HIL interaction and reproducibility | Ask/Propose in chat, inspect diff, Apply/Reject, result journal and reset |

Each teammate should be able to trace one issue through the whole system, while
leading the explanation of their own module. The six demo cases are allocated
two per teammate; a short live presentation can show one representative case
per person and use the saved run evidence for the others.

## Common evidence and claims

- HIL/IDE demo milestone completion: 100% of the agreed demo scope.
- Latest full automated suite: 20 passing tests; final affected chat/API checks
  also pass. The six-fix real-model evaluation passed all 25 repository tests.
- Detection: all six planted findings are found, but the independent 24-case
  audit has nine missed detections and five false positives. Do not describe
  demo completion as complete detection accuracy.
- Real-model evaluation uses explicitly simulated reviewer decisions; actual
  human acceptance has not been measured.
- Source is read-only in the IDE; application requires an explicit approved
  proposal. Filesystem copies are not OS security sandboxes.

Use `README.md` for running the project, `PROGRESS.md` for scope/percentage,
`DECISIONS.md` for design rationale and `RUN_RESULTS.md` for verification history.
