# PEOGAI: local repair lab

Typed Python, a local dashboard, Ollama, and three pretend repositories with
cross-dependencies. No cloud model, database, frontend build, or runtime packages.

## Start the visual demo

Requires Python 3.11+ and Ollama. Start Ollama if needed (`ollama serve` or open
its app). From this source checkout:

```powershell
python run_demo.py
```

The script restores `demo/` from `fixtures/demo/`, opens
[the dashboard](http://127.0.0.1:8765), and automatically runs real model repairs.
Keep the terminal running; Ctrl+C stops it. The default model is
`qwen2.5-coder:7b`; if missing, first run `ollama pull qwen2.5-coder:7b`.
No models are downloaded automatically.

The dashboard shows the dependency graph, live events, generated diffs, current
source files, explanations, and expandable test evidence. **Inspect system
prompt** shows the exact `SYSTEM_PROMPT` defined in `peogai/model.py`.

**Reset & run demo** restores the fixtures before every run. **Reset only**
returns to the broken baseline without calling the model. Only validated target
files are applied to `demo/`, so the explorer shows real changes on disk.

The entire disposable `demo/` directory, including per-attempt artifacts, is
replaced on every launch/run/reset. Keep your own work outside it. The canonical
`fixtures/demo/` stays unchanged. Run one demo process at a time.

```powershell
python run_demo.py --no-autostart  # reset and open; wait for the Run button
python run_demo.py --no-open      # don't open another browser tab
python run_demo.py --port 8766
python run_demo.py --model llama3.2:3b
```

## Terminal commands

```powershell
python -m peogai demo --run-tests  # reset, repair both issues, apply validated fixes
python -m peogai scan demo
python -m peogai scan fixtures/demo  # always shows the two original findings
python -m peogai repair demo 47c32d51e5 --run-tests
python -m peogai serve --open --autostart
python -m unittest discover -s tests -v
```

The resettable `demo` command only supports the bundled demo directory. `scan`
and `repair` accept other manifest-based Python workspaces too. Unlike the demo
orchestrator, `repair` leaves its input unchanged and saves a candidate for review.
Without `--run-tests`, a candidate can never receive validated status.

## Repositories and planted issues

`settings-lib` contains unsafe eval; `pricing-lib` contains a redundant boolean
branch. `shop-service` depends on both and supplies integration tests.

The downstream security test intentionally fails at baseline: executable
`dict(discount=90)` must be rejected by a literal-data parser. Normal dictionary
settings and prices must still work. Security is repaired before refactoring,
so all seven repository tests can pass at each gate.

## Evidence

- `RUN_RESULTS.md`: checked-in verification results from development.
- `.peogai/demo-history.jsonl`: appended result of each completed/rejected demo
  run, surviving resets; ignored by Git.
- `demo/.peogai/demo-latest.json`: latest successful run summary.
- `demo/.peogai/runs/<run>/`: context, baseline/candidate copies, attempted diffs,
  validated `patch.diff`, JSON evidence and Markdown explanations.
- Dashboard journal: actual reset, retrieval, generation, validation and apply events.

## Pipeline and limits

Manifest -> AST findings -> bounded caller/test context -> Ollama JSON -> exact
edits in a copy -> syntax/static/scope checks -> all repository tests -> bounded
retry -> apply validated demo change -> evidence.

All repo roots are available on PYTHONPATH, and all repo tests run. Retrieval is
lexical, not embeddings or a resolved call graph. Detection covers direct eval
calls and one boolean smell. There is no dependency audit, general data-flow
analysis, equivalence proof or secure test sandbox. The copy is not an OS sandbox.

One target file and at most 60 changed lines are allowed per candidate. Scope
checks reject unrelated top-level changes; tests cannot prove complete security.
Repository text is untrusted model context. A system prompt alone cannot guarantee
resistance to prompt injection. Use trusted tests when enabling execution.

The frontend binds only to loopback, serves fixed routes, and uses a per-process
request token for actions. Source/model output is rendered as text. Model timeout
is 240 seconds; each repo's tests have a 30-second timeout. Other locally installed
models may be selected; quality and memory requirements vary.

See [progress](PROGRESS.md), [decisions](DECISIONS.md), and [run results](RUN_RESULTS.md).

Ollama references: [structured output API](https://github.com/ollama/ollama/blob/main/docs/api.md),
[default model](https://ollama.com/library/qwen2.5-coder:7b).
