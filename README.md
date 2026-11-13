# PEOGAI: human-in-the-loop repair lab

A local, typed Python agent with Ollama, a browser dashboard, six connected
pretend repositories, six planted findings, and 25 cross-repository tests.
The model proposes and explains a fix. You decide whether it is applied.
No cloud model, database, frontend build step, or runtime Python packages.

## Start from scratch

Requires Python 3.11+ and Ollama. In one PowerShell terminal:

```powershell
cd "C:\Users\Arun Hariharan\Documents\ChatGPT\PEOGAI"
ollama serve
```

In a second terminal:

```powershell
cd "C:\Users\Arun Hariharan\Documents\ChatGPT\PEOGAI"
python run_demo.py
```

Your installed model is qwen2.5-coder:7b. If absent on another machine, first run
`ollama pull qwen2.5-coder:7b`. The script does not start Ollama or download models.
It resets demo/, opens [the dashboard](http://127.0.0.1:8765), and investigates the
first issue. It stops at **Awaiting human review**. No proposed fix is applied
until you explicitly choose **Apply this fix**.

## Human review walkthrough

1. Select a finding. The original problematic code is highlighted with line numbers.
2. Click **Explain & propose fix**. Ollama returns a diagnosis, a proposed change,
   residual risks, and a verification plan. Tests run on a separate candidate copy.
3. Inspect the diff, affected repos, and actual validation evidence. AI statements
   about tests are labeled as a plan; executed results are listed separately.
4. Choose **Apply this fix** or **Reject proposal**, optionally recording a note.
   Rejection leaves source unchanged. Approval applies only the exact reviewed bytes.
5. Pick another finding and repeat. The six changes are separate review decisions.

The proposal is bound to an opaque review ID and the whole workspace fingerprint.
Missing, old, or duplicate approval IDs are rejected. If any workspace file changes
while you review, application is blocked: reject and generate a fresh proposal.
Reset invalidates the pending review. One proposal may be pending at a time.

**Reset & investigate** restores all fixtures before generating the first proposal.
**Reset only** restores the baseline without calling the model. Every launcher
start restores demo/. Its generated files and per-attempt reports are disposable;
keep your own work outside it. fixtures/demo/ remains the canonical baseline.
Run one demo process at a time. Ctrl+C stops the dashboard server.

## Expanded scenario

| Repo | Role | Planted issue |
| --- | --- | --- |
| settings-lib | Parse customer settings | eval executes input |
| records-lib | Retrieve orders from SQLite | SQL interpolation |
| documents-lib | Read invoices under a root | Unchecked path traversal |
| pricing-lib | Discount policy | Redundant boolean branch |
| notifications-lib | Notification policy; depends on pricing | Boolean branch and empty-list smell |
| shop-service | Downstream consumer of all five libraries | Integration contracts |

These are deliberately small, inspectable cases for a HIL demonstration. They
exercise a dependency graph, security and refactoring, independent approvals,
rejections, and downstream checks. They are not a general repair benchmark.

## Validation with multiple known failures

The baseline has 25 tests: 22 pass and 3 intentionally fail for the security
issues. A proposal must remove its finding, pass its targeted security regression
(where applicable), preserve all previously passing tests, preserve the complete
test inventory, compile, and introduce no extra detected findings.

Unrelated pre-existing failures may remain. They are explicitly shown as
**BASELINE FAILURES**, never as passing tests. Raw baseline/candidate output is
retained. After all six approved fixes, all 25 tests must pass. These gates are
bounded evidence, not proof of security or behavioral equivalence.

## Commands and evidence

```powershell
python run_demo.py --no-autostart  # reset and wait for your issue selection
python run_demo.py --no-open
python run_demo.py --port 8766
python run_demo.py --model llama3.2:3b
python -m peogai demo --run-tests  # interactive: type apply for each approved patch
python -m peogai scan fixtures/demo
python -m peogai scan demo
python -m unittest discover -s tests -v
```

The terminal demo requires an explicit `apply` per patch. Other responses and EOF
reject it. The lower-level `repair` command always saves a proposal without
application. Scan its workspace to get current issue IDs.

- **Inspect system prompt** shows the exact SYSTEM_PROMPT in peogai/model.py.
- `.peogai/review-history.jsonl` records approval/rejection, note, review ID, patch
  digest and remaining findings; it survives reset and stays out of Git.
- `.peogai/demo-history.jsonl` retains console-session summaries.
- `demo/.peogai/runs/<run>/` contains context, baseline/candidate copies, diffs,
  raw tests, gates, AI explanations, JSON and Markdown reports.
- RUN_RESULTS.md records development verification; PROGRESS.md tracks scoped
  percentage completion; DECISIONS.md records the rationale.

Verification walkthrough: `python scripts/verify_hil.py` uses the real model in
a separate ignored workspace with explicitly simulated reviewer decisions.
It tests approval, rejection, stale IDs, final 25-test success and reset. It
does not measure actual human acceptance. A compact checked-in result is in
docs/hil-verification-summary.json; the current review screen is in
[this screenshot](docs/hil-review-full.png).

The dashboard binds only to loopback, restricts routes, and uses an action token
and origin checks. Model/repository content is rendered as text. Approval is a
local operator action, not authenticated multi-user identity. Tests run on your
host; a filesystem copy is not an OS sandbox. Only run trusted tests.

Detection and retrieval are narrow AST/lexical heuristics, not data-flow or call
resolution. No dependency CVE audit, fuzzing, sanitizer suite, equivalence proof,
or real-CVE evaluation is implemented. Model timeout is 240 seconds; each repo's
tests have a 30-second timeout. Maximum patch size is 60 changed lines in one
source file. The prompt does not guarantee resistance to malicious input.
