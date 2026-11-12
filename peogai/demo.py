"""Resettable demo orchestration shared by the CLI and local dashboard."""
import json
import shutil
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .engine import repair
from .model import propose
from .types import EventSink, Proposal
from .workspace import files, is_link, load, resolve, scan, snapshot

PROJECT = Path(__file__).resolve().parents[1]
DEMO_LOCK = threading.Lock()


def reset_demo(project: Path = PROJECT) -> Path:
    """Restore only the explicitly managed PROJECT/demo directory."""
    project = project.resolve()
    target = project / "demo"
    fixture = project / "fixtures" / "demo"
    if is_link(target) or is_link(fixture) or not fixture.is_dir():
        raise ValueError("Demo paths must be ordinary local directories")
    # Verify the final absolute deletion target before recursive removal.
    if target.resolve() != project / "demo" or target.resolve().parent != project:
        raise ValueError("Refusing to reset a path outside the managed demo directory")
    if target.exists():
        shutil.rmtree(target)
    snapshot(fixture, target)
    return target


def view(root: Path) -> dict[str, Any]:
    config = load(root)
    sources: dict[str, str] = {}
    for repo in config["repos"].values():
        for path in files(resolve(root, repo["path"])):
            sources[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return {"repos": config["repos"], "issues": [asdict(i) for i in scan(root)], "sources": sources}


def run_demo(model: str, attempts: int, run_tests: bool, emit: EventSink,
             project: Path = PROJECT, generator: Callable[..., Proposal] = propose,
             already_reset: bool = False) -> dict[str, Any]:
    # Caller owns DEMO_LOCK, so reset and the whole run form one operation.
    if not 1 <= attempts <= 3:
        raise ValueError("Attempts must be between 1 and 3")
    started = time.monotonic()
    root = project.resolve() / "demo" if already_reset else reset_demo(project)
    def record_result(summary: dict[str, Any]) -> None:
        checks: list[dict[str, Any]] = []
        for run_path in summary["runs"]:
            report = json.loads((Path(run_path) / "report.json").read_text(encoding="utf-8"))
            checks.append({"rule": report["issue"]["rule"], "status": report["status"],
                           "attempts": len(report["attempts"]), "seconds": report["duration_seconds"]})
        entry = {"time_utc": datetime.now(timezone.utc).isoformat(), "model": model,
                 "status": summary["status"], "remaining_findings": summary["remaining_findings"],
                 "seconds": round(time.monotonic() - started, 3), "repairs": checks}
        history = project / ".peogai" / "demo-history.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")
    emit("reset", {"message": "Restored all demo files from pristine fixtures", **view(root)})
    issues = scan(root)
    runs: list[str] = []
    for index, issue in enumerate(issues):
        emit("issue_started", {"issue": asdict(issue), "step": index + 1, "total": len(issues)})
        run = repair(root, issue.id, model, attempts, run_tests, generator, emit)
        runs.append(str(run))
        report = json.loads((run / "report.json").read_text(encoding="utf-8"))
        if report["status"] != "validated":
            summary = {"status": "rejected", "runs": runs, "remaining_findings": len(scan(root)), **view(root)}
            record_result(summary)
            emit("finished", summary)
            return summary
        # Apply only the validated target source to the resettable demo copy.
        target = resolve(root, issue.path)
        target.write_bytes(resolve(Path(report["candidate"]), issue.path).read_bytes())
        emit("applied", {"issue": asdict(issue), "source": target.read_text(encoding="utf-8"),
                         "remaining_findings": len(scan(root))})
    summary = {"status": "completed", "runs": runs, "final_candidate": str(root),
               "remaining_findings": len(scan(root)), **view(root)}
    output = root / ".peogai" / "demo-latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    record_result(summary)
    emit("finished", summary)
    return summary


class DemoController:
    def __init__(self, model: str, attempts: int, project: Path = PROJECT):
        self.model = model
        self.attempts = attempts
        self.project = project
        self.lock = threading.Lock()
        self.state: dict[str, Any] = {"status": "ready", "model": model, "events": [],
                                     **view(project / "fixtures/demo")}

    def emit(self, kind: str, data: dict[str, Any]) -> None:
        with self.lock:
            events = self.state["events"]
            events.append({"id": len(events), "kind": kind, "time": time.time(), **data})
            if kind == "reset":
                self.state.update({k: data[k] for k in ("repos", "sources", "issues")})
            elif kind == "applied":
                self.state["sources"][data["issue"]["path"]] = data["source"]
                self.state["issues"] = [i for i in self.state["issues"] if i["id"] != data["issue"]["id"]]
            elif kind == "finished":
                self.state.update({"status": data["status"], "summary": data})

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.state))

    def start(self) -> bool:
        if not DEMO_LOCK.acquire(blocking=False):
            return False
        with self.lock:
            self.state["status"] = "running"
            self.state["events"] = []
            self.state.pop("summary", None)
        def worker() -> None:
            try:
                run_demo(self.model, self.attempts, True, self.emit, self.project)
            except Exception as exc:
                self.emit("error", {"message": str(exc)})
                with self.lock:
                    self.state["status"] = "error"
            finally:
                DEMO_LOCK.release()
        threading.Thread(target=worker, daemon=True).start()
        return True
