"""Immutable, workspace-bound proposals and explicit human decisions."""
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .engine import repair
from .model import propose
from .types import EventSink, Proposal
from .workspace import IGNORED, is_link, load, resolve, scan


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    if is_link(root):
        raise ValueError("Workspace links are not supported")
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in dirs + sorted(names):
            path = Path(folder) / name
            if is_link(path):
                raise ValueError("Workspace changed to include a link")
            if path.is_file():
                digest.update(path.relative_to(root).as_posix().encode() + b"\0")
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


@dataclass(frozen=True)
class Review:
    id: str
    issue_id: str
    path: str
    workspace_hash: str
    before: bytes
    after: bytes
    payload: dict[str, Any]


def prepare(root: Path, issue_id: str, model: str, attempts: int, run_tests: bool,
            emit: EventSink, generator: Callable[..., Proposal] = propose) -> Review | None:
    original_hash = fingerprint(root)
    run = repair(root, issue_id, model, attempts, run_tests, generator, emit)
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    if report["status"] != "validated":
        return None
    if fingerprint(root) != original_hash:
        raise ValueError("Workspace changed while preparing the patch. Generate a new proposal.")
    issue = report["issue"]
    before = resolve(root, issue["path"]).read_bytes()
    after = resolve(Path(report["candidate"]), issue["path"]).read_bytes()
    attempt = report["attempts"][-1]
    repos = load(root)["repos"]
    affected = {issue["repo"]}
    for _ in repos:
        affected |= {name for name, repo in repos.items() if any(dep in affected for dep in repo.get("depends_on", []))}
    review_id = secrets.token_urlsafe(18)
    payload = {"id": review_id, "issue": issue, **attempt["proposal"], "before": before.decode("utf-8"),
               "after": after.decode("utf-8"), "diff": (run / "patch.diff").read_text(encoding="utf-8"),
               "checks": attempt["checks"], "baseline": report["baseline"],
               "raw_checks": attempt["raw_checks"], "affected_repos": sorted(affected),
               "duration_seconds": report["duration_seconds"], "run": str(run), "status": "awaiting_review"}
    return Review(review_id, issue_id, issue["path"], original_hash, before, after, payload)


def decide(project: Path, review: Review, review_id: str, approve: bool, reason: str = "") -> dict[str, Any]:
    if review.id != review_id:
        raise ValueError("This review is stale or no longer pending")
    root = project / "demo"
    if approve:
        if fingerprint(root) != review.workspace_hash:
            raise ValueError("Workspace changed since validation. Reject this proposal and generate a new one.")
        target = resolve(root, review.path)
        if target.read_bytes() != review.before:
            raise ValueError("The original source changed")
        temporary = target.with_name(target.name + ".review-tmp")
        try:
            temporary.write_bytes(review.after)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    try:
        remaining = len(scan(root))
    except (SyntaxError, ValueError, OSError):
        # Rejection/reset must remain possible after an external invalid edit.
        remaining = None
    entry = {"time_utc": datetime.now(timezone.utc).isoformat(), "review_id": review.id,
             "issue_id": review.issue_id, "path": review.path, "decision": "approved" if approve else "rejected",
             "reason": reason[:2000], "patch_sha256": hashlib.sha256(review.after).hexdigest(),
             "remaining_findings": remaining}
    history = project / ".peogai" / "review-history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")
    return entry
