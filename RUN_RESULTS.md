# Run results

## Human-in-the-loop demo: 13 November 2026

This section supersedes the earlier two-issue demo below. Local model:
qwen2.5-coder:7b via Ollama. The expanded scenario has 6 repos, 6 findings and
25 repository tests. The baseline intentionally has 3 security failures.

| Check | Result |
| --- | --- |
| Final full agent suite | 17/17 passed in 130.968 s |
| Real-model integration with simulated reviewer decisions | Passed in 219.891 s |
| Final repaired test workspace | 25/25 repo tests passed; 0 findings |
| Rejected proposal | Source unchanged |
| Stale/duplicate/wrong approval IDs | Blocked |
| External file edits during review | Application blocked |
| Reset after external invalid code | Restored successfully; old review invalidated |
| Reset after the real-model integration | 6 findings restored; review history retained |
| Browser proposal and rejection | Verified; live demo matches pristine fixture bytes |
| Python compilation / JavaScript syntax | Passed |

### Real-model cases

These are actual model generations with rule-specific repair guidance. Test
approvals/rejections were explicitly simulated in a separate disposable workspace,
not made by a human participant or counted as human acceptance. The first proposal
was rejected and regenerated to exercise that boundary. Timing includes validation.

| Repository / rule | Accepted proposal preparation |
| --- | ---: |
| documents-lib / unchecked-path | 33.422 s |
| records-lib / sql-interpolation | 34.891 s |
| settings-lib / unsafe-eval | 47.984 s |
| notifications-lib / redundant-bool | 21.718 s |
| notifications-lib / empty-list-check | 25.406 s |
| pricing-lib / redundant-bool | 11.422 s |

Security proposals passed 11 gates and refactoring proposals passed 10 gates.
The early path and SQL proposals retained respectively 2 and 1 repositories with
unrelated baseline test failures; those were explicitly disclosed. No previously
passing test could regress and no test could disappear. The targeted security
regression had to pass. After all six test approvals, every repository test passed.

### Browser verification

Generated a real settings-parser proposal in about 15.4 seconds. Inspected the
AI diagnosis, original highlighted lines, proposed diff, residual-risk statement,
verification plan, affected repos, actual gates and baseline-failure labels.
Observed Awaiting review with 6 findings and 0 applied fixes. The Apply this fix
and Reject proposal controls were available. Rejected with an explicit browser
verification note. The source remained identical to fixtures; the audit recorded
rejection. No test approval was applied to the live demo workspace.

Screenshots: docs/hil-review.png and docs/hil-review-full.png. Compact evidence:
docs/hil-verification-summary.json. Full local integration evidence is under
.peogai/hil-verification/20261113T034331Z/results.json (ignored by Git).

### Rejections encountered during development

Initial path proposals had broken indentation. Other responses checked lexical
containment without resolving '..'; syntax or the targeted security regression
rejected them. Earlier eval responses supplied incomplete replacement fragments
or matched already-patched text; they too were rejected without source changes.
The interface was refined to host-anchored complete functions, narrower context,
explicit path-normalization guidance, and concise failing-test retry evidence.
Validation gates stayed intact. A test asserting old prompt wording was updated
to check equality with the actual system prompt. A sandbox-only HTTP check needed
local socket access; the final full suite passed with that access.

This is a bounded demonstration, not a general repair success rate or security
proof. Model risk explanations are reviewable AI claims, not verified guarantees.
Static type checking and mobile viewport testing were not performed. Temporary
verification servers and the owned Ollama/model processes were stopped.

---

## Earlier auto-apply demo: 12 November 2026

Recorded on 12 November 2026. Times below use Asia/Calcutta (IST).
Local model: qwen2.5-coder:7b through Ollama 0.30.7. Python 3.11.14,
Node 24.11.1, Windows. Real demo responses were not mocked.

## Automated verification

| Check | Result |
| --- | --- |
| python -m unittest discover -s tests -v | 10/10 passed; final run 5.531 s |
| node --check peogai/frontend/app.js | Passed |
| python -m compileall -q peogai run_demo.py | Passed |
| Pristine fixture scan | 2 planted findings |
| Repaired demo scan | 0 findings |
| Final reset scan | 2 planted findings restored |

Agent tests exercise invalid responses, path escape rejection, unrelated edits,
bounded retries, source preservation and test-gated acceptance. Demo tests run
two complete simulated-model repairs consecutively, verify each starts with two
findings, preserve pristine fixtures and unrelated files, and confirm history
survives reset. These deterministic tests are separate from real-model runs.
The HTTP test checks page/state delivery, prompt visibility, action-token and
origin rejection, and successful authorized reset.

## Real model runs

| Run | Result | Attempts | Elapsed |
| --- | --- | --- | ---: |
| Core CLI security repair, 09:20 IST | Validated | 1 | 5.910 s |
| Core CLI refactoring, 09:20 IST | Validated | 1 | 6.450 s |
| Frontend Run button, 09:31:55-09:32:13 IST | Both repairs validated | 1 per issue | 18.5 s |
| Frontend repeat, 09:33:10-09:33:21 IST | Both repairs validated | 1 per issue | 10.9 s |
| Restarted launcher with autostart, 09:35:29-09:35:40 IST | Both repairs validated | 1 per issue | 11.235 s |

The final launcher run logged 5.610 s for the security repair and 5.485 s for the
refactoring. Each accepted candidate passed six gates: target removal, static
regression check, syntax, and tests in all three repositories (7 unit/integration
tests total). Baseline security test failed as intended, then passed after repair.
Observed 18 real pipeline events per completed visual run.

## Browser walkthrough

- Observed real generation, proposed diffs and validated fixes in the dashboard.
- Switched between security and refactoring patches.
- Expanded the exact system prompt and downstream service test output.
- Verified the completion screen: 3 repos, 0 open findings, 2 validated fixes.
- Used Reset only: returned to ready state with 2 findings and no applied fixes.
- Restarted the launcher from a fixed workspace: it reset before autostart.
- Confirmed project-level JSONL history survived the final reset.
- Saved docs/demo-completed.png as visual evidence.

The temporary verification server was stopped after testing. Launch your own
session with python run_demo.py. The workspace is committed in its planted state.

## Rejected attempts and corrections

- Initial sandbox test run could not create normal temporary directories. Moved
  test scratch space into ignored project-local .peogai/test-tmp; tests passed.
- Initial Ollama check found no running server. Started the installed local
  server and verified actual requests; no new model download was needed.
- Early security responses broke indentation; syntax validation rejected them.
  Added explicit whitespace guidance and full failed-proposal retry feedback.
- Early refactoring responses also changed a neighboring function; the AST
  scope gate rejected them. Added editable-symbol/read-only-symbol context.
- Validation gates were kept intact. Subsequent reported runs passed.

## Limits

These outcomes establish this two-issue toy demonstration, not a general repair
success rate. Passing tests is not a security proof. Static type checking was
not run because no checker was installed. Responsive CSS exists; visual browser
verification covered the desktop viewport only. Generated runs and machine-local
history are ignored by Git; this log records the observed verification results.
