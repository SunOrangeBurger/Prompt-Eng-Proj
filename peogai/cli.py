import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .engine import repair
from .demo import DEMO_LOCK, PROJECT, run_demo
from .workspace import scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Local multi-repository patch experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    scan_parser = sub.add_parser("scan", help="Find planted security and refactoring patterns")
    scan_parser.add_argument("workspace", type=Path)
    scan_parser.add_argument("--json", action="store_true")
    fix = sub.add_parser("repair", help="Propose and validate a patch in a copy")
    fix.add_argument("workspace", type=Path)
    fix.add_argument("issue")
    fix.add_argument("--model", default="qwen2.5-coder:7b")
    fix.add_argument("--attempts", type=int, default=2)
    fix.add_argument("--run-tests", action="store_true", help="Execute trusted repository tests on your machine")
    demo = sub.add_parser("demo", help="Review planted issues sequentially; explicitly approve each patch")
    demo.add_argument("workspace", type=Path, nargs="?", default=Path("demo"))
    demo.add_argument("--model", default="qwen2.5-coder:7b")
    demo.add_argument("--attempts", type=int, default=2)
    demo.add_argument("--run-tests", action="store_true", help="Execute the trusted toy repository tests")
    serve = sub.add_parser("serve", help="Open the resettable local demo dashboard")
    serve.add_argument("--model", default="qwen2.5-coder:7b")
    serve.add_argument("--attempts", type=int, default=2)
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--open", action="store_true", help="Open the dashboard in your default browser")
    serve.add_argument("--autostart", action="store_true", help="Investigate the first issue immediately; application still requires approval")
    args = parser.parse_args()
    try:
        if args.command == "scan":
            issues = scan(args.workspace.resolve())
            if args.json:
                print(json.dumps([asdict(i) for i in issues], indent=2))
            else:
                for i in issues:
                    print(f"{i.id}  {i.kind:8}  {i.path}:{i.line}  {i.rule}")
                print(f"{len(issues)} finding(s)")
        elif args.command == "repair":
            run = repair(args.workspace, args.issue, args.model, args.attempts, args.run_tests)
            status = json.loads((run / "report.json").read_text(encoding="utf-8"))["status"]
            print(f"{status}: {run}")
            if status != "validated":
                raise SystemExit(1)
        elif args.command == "demo":
            if args.workspace.resolve() != PROJECT / "demo":
                raise ValueError("The resettable demo command only supports the bundled demo workspace; use repair for other workspaces")
            def emit(kind: str, data: dict) -> None:
                if kind == "reset":
                    print("Reset demo from pristine fixtures", flush=True)
                elif kind == "issue_started":
                    print(f"Step {data['step']}/{data['total']}: {data['issue']['rule']}", flush=True)
                elif kind == "repair_finished":
                    print(f"{data['status']}: {data['run']}", flush=True)
            with DEMO_LOCK:
                def review(payload: dict) -> bool:
                    print("\nProblem: " + payload["diagnosis"])
                    print("Fix: " + payload["explanation"])
                    print("Risk: " + payload["risk"])
                    print(payload["diff"])
                    for check in payload["checks"]:
                        print(f"{'BASELINE FAILURES REMAIN' if check.get('baseline_failures') else 'PASS' if check['passed'] else 'FAIL'}: {check['name']}")
                    try:
                        return input("Apply this exact validated patch? Type apply to approve: ").strip().lower() == "apply"
                    except EOFError:
                        return False
                summary = run_demo(args.model, args.attempts, args.run_tests, emit, reviewer=review)
            if summary["status"] != "completed":
                raise SystemExit(1)
            print(f"Demo summary: {PROJECT / 'demo/.peogai/demo-latest.json'}")
        else:
            from .server import serve as start_server
            start_server(args.model, args.attempts, args.port, args.open, args.autostart)
    except (ValueError, SyntaxError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
