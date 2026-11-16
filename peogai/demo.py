"""Resettable demo orchestration shared by the CLI and local dashboard."""
import json
import shutil
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .model import answer, propose
from .review import Review, decide, prepare
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
             reviewer: Callable[[dict[str, Any]], bool] | None = None) -> dict[str, Any]:
    # Caller owns DEMO_LOCK, so reset and the whole run form one operation.
    if not 1 <= attempts <= 3:
        raise ValueError("Attempts must be between 1 and 3")
    started = time.monotonic()
    root = reset_demo(project)
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
        review = prepare(root, issue.id, model, attempts, run_tests, emit, generator)
        if review is None:
            summary = {"status": "rejected", "runs": runs, "remaining_findings": len(scan(root)), **view(root)}
            record_result(summary)
            emit("finished", summary)
            return summary
        runs.append(review.payload["run"])
        emit("awaiting_review", review.payload)
        if reviewer is None:
            return {"status": "awaiting_review", "review": review.payload, "runs": runs, **view(root)}
        approved = reviewer(review.payload)
        decision = decide(project, review, review.id, approved)
        emit("human_decision", decision)
        if not approved:
            continue
        emit("applied", {"issue": asdict(issue), "source": review.after.decode("utf-8"),
                         "remaining_findings": len(scan(root))})
    summary = {"status": "completed" if not scan(root) else "reviewed", "runs": runs, "final_candidate": str(root),
               "remaining_findings": len(scan(root)), **view(root)}
    output = root / ".peogai" / "demo-latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    record_result(summary)
    emit("finished", summary)
    return summary


class DemoController:
    def __init__(self, model: str, attempts: int, project: Path = PROJECT,
                 generator: Callable[..., Proposal] = propose,
                 chatter: Callable[..., str] = answer):
        self.model = model
        self.attempts = attempts
        self.project = project
        self.generator = generator
        self.chatter = chatter
        self.pending: Review | None = None
        self.lock = threading.Lock()
        self.state: dict[str, Any] = {"status": "ready", "model": model, "events": [],
                                     "pending": None, "chat_busy": False, **view(project / "fixtures/demo")}

    def emit(self, kind: str, data: dict[str, Any]) -> None:
        with self.lock:
            events = self.state["events"]
            events.append({"id": len(events), "kind": kind, "time": time.time(), **data})
            if kind == "reset":
                self.state.update({k: data[k] for k in ("repos", "sources", "issues")})
            elif kind == "applied":
                self.state["sources"][data["issue"]["path"]] = data["source"]
                self.state["issues"] = [asdict(i) for i in scan(self.project / "demo")]
            elif kind == "finished":
                self.state.update({"status": data["status"], "summary": data})

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.state))

    def start(self, issue_id: str | None = None, reset: bool = True, request: str = "") -> bool:
        if not DEMO_LOCK.acquire(blocking=False):
            return False
        with self.lock:
            if self.pending is not None or self.state["status"] == "running":
                DEMO_LOCK.release()
                return False
            self.state["status"] = "running"
            if reset:
                self.state["events"] = []
            self.state.pop("summary", None)
        def worker() -> None:
            try:
                root = reset_demo(self.project) if reset else self.project / "demo"
                if reset:
                    self.emit("reset", {"message": "Restored original files; application requires human approval", **view(root)})
                issues = scan(root)
                selected = next((i for i in issues if i.id == issue_id), None) if issue_id else next(iter(issues), None)
                if selected is None:
                    raise ValueError("Choose a current issue")
                self.emit("issue_started", {"issue": asdict(selected)})
                self.emit("user_message", {"text": request or "Explain this finding and propose a minimal fix.",
                                           "path": selected.path, "issue_id": selected.id, "mode": "propose",
                                           "origin": "user" if request else "demo"})
                review = prepare(root, selected.id, self.model, self.attempts, True, self.emit, self.generator, request)
                with self.lock:
                    self.pending = review
                    self.state["pending"] = review.payload if review else None
                    self.state["status"] = "awaiting_review" if review else "rejected"
                if review:
                    self.emit("awaiting_review", review.payload)
            except Exception as exc:
                self.emit("error", {"message": str(exc)})
                with self.lock:
                    self.state["status"] = "error"
            finally:
                DEMO_LOCK.release()
        threading.Thread(target=worker, daemon=True).start()
        return True

    def ask(self, path: str, message: str) -> bool:
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
            raise ValueError("Write a question of 1-2000 characters")
        if not DEMO_LOCK.acquire(blocking=False):
            return False
        with self.lock:
            if path not in self.state["sources"]:
                DEMO_LOCK.release()
                raise ValueError("Select a workspace file")
            self.state["chat_busy"] = True
            history = [{"kind": e["kind"], "text": e.get("text", "")[:2000]}
                       for e in self.state["events"] if e["kind"] in {"user_message", "assistant_message"}
                       and e.get("path") == path][-6:]
            payload = self.pending.payload if self.pending and self.pending.path == path else None
            pending = ({k: payload[k] for k in ("diagnosis", "explanation", "risk", "verification")}
                       | {"diff": payload["diff"][:8000],
                          "checks": [{"name": c["name"], "passed": c["passed"],
                                      "baseline_failures": c.get("baseline_failures", False),
                                      "output": c["output"][:400]} for c in payload["checks"]]}) if payload else None
            context = {"path": path, "source": self.state["sources"][path][:12_000],
                       "issues": [i for i in self.state["issues"] if i["path"] == path],
                       "pending_review": pending, "conversation": history, "repo_graph": self.state["repos"],
                       "recent_decisions": [{"decision": e["decision"], "reason": e.get("reason", "")[:1000]}
                                            for e in self.state["events"] if e["kind"] == "human_decision"
                                            and e.get("issue", {}).get("path") == path][-3:]}
        self.emit("user_message", {"text": message.strip(), "path": path, "mode": "ask"})
        def worker() -> None:
            try:
                response = self.chatter(message.strip(), context, self.model)
                self.emit("assistant_message", {"text": response, "path": path})
            except Exception as exc:
                self.emit("chat_error", {"message": str(exc), "path": path})
            finally:
                with self.lock:
                    self.state["chat_busy"] = False
                DEMO_LOCK.release()
        threading.Thread(target=worker, daemon=True).start()
        return True

    def decision(self, review_id: str, approve: bool, reason: str = "") -> dict[str, Any]:
        if not DEMO_LOCK.acquire(blocking=False):
            raise ValueError("A generation or reset is still running")
        try:
            with self.lock:
                review = self.pending
            if review is None:
                raise ValueError("No proposal is pending review")
            entry = decide(self.project, review, review_id, approve, reason)
            self.emit("human_decision", {**entry, "issue": review.payload["issue"]})
            if approve:
                self.emit("applied", {"issue": review.payload["issue"], "source": review.after.decode("utf-8"),
                                      "remaining_findings": entry["remaining_findings"]})
            with self.lock:
                self.pending = None
                self.state["pending"] = None
                self.state["status"] = "completed" if not self.state["issues"] else "ready"
            return entry
        finally:
            DEMO_LOCK.release()

    def reset(self) -> bool:
        if not DEMO_LOCK.acquire(blocking=False):
            return False
        try:
            with self.lock:
                review = self.pending
            if review:
                decide(self.project, review, review.id, False, "Discarded by workspace reset")
            root = reset_demo(self.project)
            with self.lock:
                self.pending = None
                self.state.update({"status": "ready", "pending": None, "events": [], **view(root)})
                self.state.pop("summary", None)
            return True
        finally:
            DEMO_LOCK.release()
