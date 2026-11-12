# Progress

Updated: 12 November 2026 (Asia/Calcutta).

## Completion: 100% of the expanded local demo MVP

Percentage is the sum of completed milestone weights. It measures the agreed
local demo, including the frontend/reset extension, not the full research proposal.

| Milestone | Weight | Status | Evidence |
| --- | ---: | --- | --- |
| Typed agent, repo graph, detection, retrieval and Ollama repairs | 60% | Complete | Both planted issues repaired by qwen2.5-coder:7b |
| Frontend with diffs, source, prompt, checks and real event journal | 15% | Complete | Desktop browser walkthrough and screenshot |
| Launcher, automatic clean resets and application of validated fixes | 10% | Complete | Startup, Run button, Reset button and consecutive-run tests |
| Regression tests and real-model verification | 10% | Complete | 10/10 automated tests; 7 repo tests pass after each accepted fix |
| Walkthrough, decisions and run-result records | 5% | Complete | README, DECISIONS, RUN_RESULTS and persistent JSONL history |

## Verified results

- Three visual real-model runs completed: 18.5 s, 10.9 s, and 11.235 s.
- Each repaired security and refactoring in one attempt per issue.
- Final candidates had 0 findings; all 7 repository tests passed after each fix.
- The original security baseline deliberately fails one downstream regression test.
- Final reset restored both findings and the original source files.
- Project-level .peogai/demo-history.jsonl survived the reset.
- 10 automated tests cover retries, preservation, regression rejection, consecutive
  resets, immutable fixtures, event delivery and HTTP request boundaries.
- JavaScript syntax check and Python compilation passed.
- Exact system prompt is a named constant and visible in the dashboard.
- Static type-checking was not run: no type checker was installed.
- Desktop browser flow was visually inspected. Mobile breakpoints are implemented
  but were not separately tested in a mobile viewport.

Detailed evidence and rejected attempts: RUN_RESULTS.md. Generated per-attempt
artifacts are local and intentionally replaced on reset. Checked-in evidence
includes docs/demo-completed.png.

## Research objectives outside this percentage

Dependency CVE scanning, general data-flow/call-graph analysis, embedding retrieval,
sanitizers, fuzzing, equivalence checking, realistic CVE benchmarks, CI integration,
multi-language support, and reviewer studies remain unimplemented.

## Log

- 12 Nov: Read review as reference; selected a small typed stdlib Python core.
- 12 Nov: User narrowed scope to simulated independent repos with planted issues.
- 12 Nov: Core demo completed; 6 agent tests and two real local repairs passed.
- 12 Nov: User expanded scope to a frontend, visible repairs, automatic reset,
  system-prompt inspection, GitHub delivery and run-result logging.
- 12 Nov: Added immutable fixtures, demo orchestrator, local dashboard, launcher,
  real engine events and persistent history. Expanded suite to 10 passing tests.
- 12 Nov: Completed three browser/launcher model runs and verified clean reset.
