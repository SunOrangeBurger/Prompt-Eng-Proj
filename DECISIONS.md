# Decisions

## 001 - Demonstration scope

Use three directory-backed pretend repositories with declared dependencies.
No separate Git servers or virtual filesystem package. Ordinary files are easier
to inspect, reset and demonstrate. The repo graph is metadata; all repo roots
are available on PYTHONPATH and all discovered tests run for every candidate.

## 002 - Language and types

Use Python 3.11+ with annotations and dataclasses for issues, edits, proposals
and check results. It provides AST parsing, tests, subprocesses, HTTP and JSON
without runtime packages. Target repositories are Python too. TypeScript was
not assumed from the user's request for types. Configuration remains JSON with
runtime validation. Strict type-checking configuration is included; static
type-checking verification will be recorded separately from runtime tests.

## 003 - Local model

Use installed qwen2.5-coder:7b through Ollama on 127.0.0.1. No cloud calls or
new model downloads. Model is selectable with --model. A smaller 3b variant
can be selected if installed; quality and memory tradeoffs need measurement.

## 004 - Detection before generation

Start with two deliberately narrow AST rules: unsafe eval and redundant boolean
branches. The model repairs a localized finding, rather than discovering arbitrary
problems. Findings are heuristic and can be false positives. No claim of complete
security coverage or semantic analysis.

## 005 - Retrieval without infrastructure

Retrieve a bounded number of files by shared symbol mentions, alongside the
dependency manifest. This supplies callers/tests without embeddings or a vector
database. It is lexical context retrieval, not a resolved call graph.

## 006 - Small patches and review

One finding, one source file, at most four exact-text replacements and 60 changed
lines per candidate. Reject unrelated top-level AST changes; imports may change.
This is a minimality heuristic, not a guarantee against tangled changes inside
the same function. Never edit pristine fixtures or tests automatically. Save a
candidate copy, unified diff, model explanation and validation evidence. The
resettable demo applies only the validated target source to demo/.

## 007 - Validation and trust boundary

Syntax checks, existing rules and all repository tests gate validation. The
downstream service has a deliberately failing harmless security regression test;
baseline failures are recorded, while a validated candidate must pass every check.
A baseline can be red because remediation is the task. No-test or skipped-test
runs never receive validated status. Repository tests execute only with
--run-tests; a filesystem copy is not an OS security sandbox. Trust test code
before running it. The model cannot select commands, paths or change test files.

## 008 - Local evidence and completion

Runs live under WORKSPACE/.peogai/runs; pristine fixtures remain unchanged.
PROGRESS.md uses weighted milestones with evidence and explicitly distinguishes
the small demo from the much larger research proposal. Do not label an
implemented-but-unverified feature complete.

## 009 - Findings from real model verification

The first security response broke indentation and an early refactoring response
also changed an unrelated function. Both were rejected. Add explicit whitespace
guidance, include the failed proposal in retry feedback, and provide the editable
symbol plus read-only symbols in context. Keep validation gates intact. The final
real-model demo completed both repairs in one attempt each. This demonstrates
these two fixtures; it does not establish a general success rate.

## 010 - Local frontend and real progress

Serve buildless HTML/CSS/JavaScript from Python's standard HTTP server on
127.0.0.1. Poll local state rather than adding a websocket framework. Engine
callbacks publish real events, diffs, explanations and validation evidence.
No fake model responses in the visual demo. Render source/model text with
textContent, never HTML. Expose the exact system prompt in an inspector.

## 011 - Reset and application contract

fixtures/demo/ is pristine; demo/ is disposable. Every script launch and every
Run button restores the full demo directory. Verify the final managed deletion
target before recursive removal, reject links, bind the HTTP port before reset,
and serialize actions within the server. Never reset arbitrary workspace paths.
Apply validated target files to demo/ so observers can inspect real changes.
The lower-level repair command stays review-only. Run one demo process at a
time; the in-process guard is not a cross-process lock.

## 012 - Result logging

Record development verification in tracked RUN_RESULTS.md. Append compact
outcomes to project-level .peogai/demo-history.jsonl, outside the reset target,
so results survive clean starts. Ignore generated reports, logs and caches in
Git. Commit the clean planted demo and canonical fixtures.

## 013 - Human-in-the-loop is the primary workflow (13 Nov)

This supersedes automatic demo application in decisions 006 and 011. Generating
or validating a candidate never applies it. The browser prepares one issue and
pauses at awaiting_review. Only an explicit approve action for that opaque review
ID can apply the exact validated bytes. Rejection leaves source unchanged.
The console demo likewise requires apply for every proposal; EOF rejects it.
Reset cancels pending review. Run one demo process at a time.

Bind the review to a fingerprint of the entire source/test/config workspace,
excluding generated state. Block approval after any external edit, even outside
the target file. Capture reviewed bytes in memory, rather than rereading a
mutable candidate directory at application time. Append approval/rejection,
review ID, patch digest and reviewer note outside the reset target. Local
operator actions are not an authenticated multi-user identity system.

## 014 - A larger but inspectable scenario (13 Nov)

Use six repos and six findings: eval, SQL interpolation, unchecked file paths,
two boolean branches and a list-emptiness smell. Add downstream consumers and
25 tests. These are deliberately planted examples, not realistic CVE coverage.
The model receives narrow, rule-specific repair guidance and generates the
actual replacement function and explanation; code is not substituted by a
built-in deterministic fixer. AI explanatory claims remain reviewable statements.

## 015 - Baseline-aware validation (13 Nov)

With multiple vulnerabilities, the pristine baseline has three failing tests.
Preserve every previously passing test and the entire test inventory. A security
proposal must also pass its named security regression test. Allow unrelated
pre-existing failures only if the same test still fails in the same way at the
unittest status level, disclosing raw output as BASELINE FAILURES. This is a
bounded regression heuristic, not semantic equivalence or a security proof.
The final fully approved workspace must pass all 25 tests.

## 016 - Explanation and review evidence (13 Nov)

Require structured diagnosis, proposed change, residual risks and a verification
plan from Ollama. Highlight the original lines separately from the diff, show
transitively affected repositories and actual executed tests. Label model test
claims as a plan. Keep human decisions separate from validation status. Real
integration checks use a disposable workspace and explicitly label their
approval/rejection actions as simulated reviewer choices.

## 017 - Structured replacement boundary (13 Nov)

Real responses exposed fragile old-text matching and whitespace handling. Ask
the model for a complete replacement function, optionally with imports, rather
than requiring it to retype the original anchor. The host anchors that output
to the known editable function. Parse the response, preserve the public signature
and decorators, enforce AST scope and size, and run all validation gates. Supply
existing imports and the editable function instead of repeating the whole target
file. The model still generates the actual fix and explanation; no canned fix
is applied by the host. Rule-specific guidance remains explicit in model.py.
