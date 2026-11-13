# Progress

Updated: 13 November 2026 (Asia/Calcutta).

## Completion: 100% of the human-in-the-loop demo MVP

This replaces the earlier auto-apply demo scope. Percentage is the sum of
completed weights, not progress toward every research objective in the PDF.

| Milestone | Weight | Status | Evidence |
| --- | ---: | --- | --- |
| Typed local agent, AST detection, retrieval and candidate validation | 35% | Complete | Five rule types; scope and regression gates |
| Six repositories, six findings, 25 cross-repo tests | 15% | Complete | Baseline: 22 passing tests, 3 intentional failures |
| Backend human approval, rejection, freshness checks and audit | 25% | Complete | Explicit decisions only; no generation-time application |
| Frontend diagnosis, highlighted code, diff and review controls | 10% | Complete | Real browser proposal and rejection verified |
| Documentation and walkthrough | 5% | Complete | README and decision records updated |
| Final regression and real-model/browser verification | 10% | Complete | 17/17 agent tests; six real model fixes; 25/25 final repo tests |

## Current verification

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
