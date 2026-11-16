# Progress

Updated: 16 November 2026 (Asia/Calcutta).

## Completion: 100% of the human-in-the-loop IDE demo MVP

This replaces the earlier auto-apply demo scope. Percentage is the sum of
completed weights, not progress toward every research objective in the PDF.

Team ownership is allocated equally: Sharanya owns analysis/detection, Ragul
owns model/repair/validation safeguards, and Arun owns the IDE/application.
Each owns one third, including module tests, documentation and demo coverage.
The detailed handoff and two-repo/two-case allocations are in TEAM_WORK_DIVISION.md.

| Milestone | Weight | Status | Evidence |
| --- | ---: | --- | --- |
| Typed local agent, AST detection, retrieval and candidate validation | 35% | Complete | Five rule types; scope and regression gates |
| Six repositories, six findings, 25 cross-repo tests | 15% | Complete | Baseline: 22 passing tests, 3 intentional failures |
| Backend human approval, rejection, freshness checks and audit | 25% | Complete | Explicit decisions only; no generation-time application |
| IDE frontend, read-only AI chat, highlighted code, diff and review controls | 10% | Complete | Real Ollama question, proposal and browser rejection verified |
| Documentation and walkthrough | 5% | Complete | README and decision records updated |
| Final regression and real-model/browser verification | 10% | Complete | 20/20 agent tests; IDE question/proposal verified; earlier six-fix run passed 25 repo tests |

## Current verification

- 16 Nov IDE update: explorer, file tabs/search, read-only syntax-colored editor,
  source/diff modes, wrapping, bottom Problems/Validation/Pipeline panels and an
  AI side chat. Typed questions call Ollama without edit authority; Propose fix
  forwards the operator's constraints into the existing validated repair flow.
- Full suite: 20/20 tests passed in 47.753 seconds. Added tests cover selected-file
  question context, pending-review preservation, request forwarding, concurrency,
  error recovery and HTTP chat routing. Affected chat/API tests passed again after
  context refinements. Python and JavaScript syntax checks pass.
- Browser check used an isolated copy of the current live workspace. Real model
  question response: 25.621 seconds; SQL proposal preparation: 12.890 seconds,
  with 11 passing gates and 1 disclosed unrelated baseline-failure repo.
- Verified file search/tabs, original highlights, wrapped diff, validation panel,
  Apply disabled outside the pending patch view, and rejection with no application.
  Live workspace fingerprint stayed unchanged. Evidence: docs/ide-workspace.png
  and docs/ide-verification-summary.json. The temporary preview was stopped.
- Source viewing is read-only, not a general code-editing IDE. Desktop layout
  was visually verified; mobile viewport and static type checking were not run.

- 16 Nov detection audit: all 6 planted findings at the expected file/line/rule,
  with no additional findings in the pristine demo. This does not establish
  general detector accuracy. Of 24 independent curated probes, 10 matched the
  expected result: 9 missed-detection cases and 5 false-positive cases remain.
- The current live demo has 5 findings because its invoice path reader has
  already been fixed. Its 25 tests show 23 passes and the 2 expected remaining
  security failures. The existing invoice-reader edit was preserved.
- Discovery is five handwritten AST rules; Ollama explains and repairs the
  supplied findings. General error discovery is not implemented. A syntax error
  currently aborts scanning, and sources larger than 64 KB are silently skipped.
- Reproduce: python scripts/verify_detection.py. Detailed evidence is in
  docs/detection-audit.json. The 100% percentage above is completion of the
  bounded HIL demo, not complete error detection or production readiness.

- Deterministic review tests cover generation without application, explicit
  single-use approvals, rejection with notes, stale IDs, changed workspaces,
  resets, complete test inventories and baseline-aware regression gates.
- Expanded fixture: 25 tests, with three deliberate security failures at baseline.
- HTTP route and action-token checks pass with local socket access enabled.
- Real-model integration passed in 219.891 seconds with simulated reviewer
  decisions in a separate disposable workspace. All six fixes were validated
  and approved there; all 25 repository tests passed before reset.
- Verified rejected proposals never change source, old review IDs are blocked,
  and reset restores six findings while preserving review audit records.
- In the real browser, generated a settings proposal in about 15.4 seconds,
  inspected diagnosis/code/diff/gates, and rejected it with a note. The live demo
  remained byte-for-byte identical to pristine fixtures.
- Earlier real responses with malformed code or incomplete security guards
  were rejected. Complete-function output anchored by the host, function-only
  context, explicit rule guidance and useful retry evidence improved reliability
  without relaxing syntax, signature, scope, test or security gates.
- AI fields separate diagnosis, proposed fix, residual risk and verification plan.
  Actual test results are separate from the model's statements.
- Python compilation and JavaScript syntax checks passed. Verification servers
  and the owned Ollama process were stopped after testing.
- Evidence: RUN_RESULTS.md, docs/hil-verification-summary.json and the two
  docs/hil-review screenshots. Static typing and mobile viewport checks remain
  outside this verification record.

## Scope outside this percentage

General data-flow/call graphs, dependency CVE audits, embeddings, sanitizers,
fuzzing, equivalence proofs, real-CVE benchmarks, CI integration, multi-language
support, and actual human acceptance studies remain future work. Test-time
simulated decisions are not evidence of human acceptance. Static type checking
and mobile viewport testing have not been performed.

## Log

- 12 Nov: Implemented and verified the original two-issue auto-apply demo.
- 13 Nov: User clarified that human-in-the-loop validation is the main purpose.
- 13 Nov: Replaced automatic application with per-proposal approval/rejection,
  added original-code highlighting, structured AI explanations, workspace-bound
  review IDs and a persistent review audit.
- 13 Nov: Expanded to six repos and six findings with 25 tests; disclosed
  unrelated baseline failures instead of blocking all independent proposals.
- 13 Nov: Passed final real-model, deterministic and browser checks. HIL demo
  completion updated to 100%; previous auto-apply behavior is superseded.
- 16 Nov: Audited detector limits, then replaced the dashboard with an IDE-style
  workspace and real model side chat. HIL gates and existing user source preserved.
