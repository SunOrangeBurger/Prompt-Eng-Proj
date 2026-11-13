"""Real-model integration check with simulated decisions in a disposable workspace."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peogai.demo import DEMO_LOCK, DemoController, reset_demo
from peogai.engine import test_cases, validate
from peogai.review import fingerprint
from peogai.workspace import scan, snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output = project / ".peogai/hil-verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot(project / "fixtures/demo", output / "fixtures/demo")
    reset_demo(output)
    controller = DemoController(args.model, 2, output)
    started = time.monotonic()
    results: list[dict] = []
    def generate(issue_id: str) -> dict:
        assert controller.start(issue_id, reset=False)
        deadline = time.monotonic() + 520
        while time.monotonic() < deadline:
            state = controller.snapshot()
            if state["status"] != "running" and DEMO_LOCK.acquire(blocking=False):
                DEMO_LOCK.release()
                if state["status"] != "awaiting_review":
                    (output / "failure.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
                    raise AssertionError(f"Generation failed; see {output / 'failure.json'}")
                return state["pending"]
            time.sleep(.1)
        raise TimeoutError("Model preparation exceeded integration-check deadline")
    while issues := scan(output / "demo"):
        issue = issues[0]
        print(f"Preparing {issue.rule} in {issue.repo} ({len(issues)} left)", flush=True)
        original = fingerprint(output / "demo")
        review = generate(issue.id)
        assert fingerprint(output / "demo") == original, "Generation must never apply a fix"
        for key in ("diagnosis", "explanation", "risk", "verification"):
            assert review[key].strip(), key
        if not results:
            controller.decision(review["id"], False, "Automated verification: reject the disposable proposal")
            assert fingerprint(output / "demo") == original
            old_id = review["id"]
            review = generate(issue.id)
            try:
                controller.decision(old_id, True)
                raise AssertionError("Old approval ID was accepted")
            except ValueError:
                pass
        controller.decision(review["id"], True, "Automated integration check; simulated reviewer, disposable workspace only")
        assert len(scan(output / "demo")) == len(issues) - 1
        result = {"rule": issue.rule, "repo": issue.repo, "seconds": review["duration_seconds"],
                  "review_id": review["id"], "checks": review["checks"], "raw_checks": review["raw_checks"],
                  "diagnosis": review["diagnosis"], "explanation": review["explanation"], "risk": review["risk"]}
        results.append(result)
        print(f"Approved test proposal: {issue.rule}", flush=True)
    checks = validate(output / "demo", True)
    assert all(c.passed for c in checks)
    assert len(test_cases(checks)) == 25
    before_reset_history = (output / ".peogai/review-history.jsonl").read_bytes()
    assert controller.reset()
    assert len(scan(output / "demo")) == 6
    assert (output / ".peogai/review-history.jsonl").read_bytes() == before_reset_history
    summary = {"model": args.model, "status": "passed", "seconds": round(time.monotonic() - started, 3),
               "approved_test_proposals": len(results), "final_tests": 25, "final_failures": 0,
               "reset_findings": 6, "rejection_preserved_source": True, "stale_id_blocked": True,
               "simulated_reviewer": True, "results": results}
    destination = output / "results.json"
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PASS: {destination} ({summary['seconds']} s)", flush=True)


if __name__ == "__main__":
    main()
