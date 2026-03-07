"""
Job state store: Redis when REDIS_URL is set, otherwise in-memory.
Used by FastAPI (read/write) and Celery task (write progress and result).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from settings import settings

_IN_MEMORY: Dict[str, dict] = {}

REDIS_KEY_PREFIX = "codeatlas:job:"
KEY_STATUS = "status"
KEY_STAGE = "stage"
KEY_OWNER = "owner"
KEY_REPO = "repo"
KEY_BRANCH = "branch"
KEY_PROGRESS = "progress"
KEY_REPORT = "report"
KEY_ERROR = "error"
KEY_TASK_ID = "task_id"


def _redis_client():
    if not settings.redis_url:
        return None
    import redis
    return redis.from_url(settings.redis_url, decode_responses=True)


def job_key(analysis_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}{analysis_id}"


def create_job(analysis_id: str, owner: str, repo: str, branch: str) -> None:
    payload = {
        "analysis_id": analysis_id,
        KEY_STATUS: "running",
        KEY_STAGE: "running",
        KEY_OWNER: owner,
        KEY_REPO: repo,
        KEY_BRANCH: branch,
        KEY_PROGRESS: [],
        KEY_REPORT: None,
        KEY_ERROR: None,
    }
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        r.hset(key, mapping={
            KEY_STATUS: "running",
            KEY_STAGE: "running",
            KEY_OWNER: owner,
            KEY_REPO: repo,
            KEY_BRANCH: branch,
            KEY_PROGRESS: json.dumps([]),
            KEY_REPORT: json.dumps(None),
            KEY_ERROR: "",
        })
        r.expire(key, 86400 * 7)  # 7 days TTL
    else:
        payload["progress"] = []
        _IN_MEMORY[analysis_id] = payload


def get_job(analysis_id: str) -> Optional[Dict[str, Any]]:
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        raw = r.hgetall(key)
        if not raw:
            return None
        progress = json.loads(raw.get(KEY_PROGRESS, "[]"))
        report_raw = raw.get(KEY_REPORT) or "null"
        report = json.loads(report_raw) if report_raw else None
        return {
            "analysis_id": analysis_id,
            "status": raw.get(KEY_STATUS, "running"),
            "stage": raw.get(KEY_STAGE, "running"),
            "owner": raw.get(KEY_OWNER, ""),
            "repo": raw.get(KEY_REPO, ""),
            "branch": raw.get(KEY_BRANCH, "main"),
            "progress": progress,
            "report": report,
            "error": raw.get(KEY_ERROR) or None,
            "task_id": raw.get(KEY_TASK_ID) or None,
        }
    job = _IN_MEMORY.get(analysis_id)
    if job is not None and isinstance(job, dict):
        job = {**job, "task_id": job.get("task_id")}
    return job


def append_progress(analysis_id: str, step: str, label: str) -> None:
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        job = get_job(analysis_id)
        if not job:
            return
        progress: List[Dict[str, Any]] = list(job.get("progress") or [])
        progress.append({"step": step, "label": label, "status": "done"})
        r.hset(key, KEY_PROGRESS, json.dumps(progress))
    else:
        if analysis_id in _IN_MEMORY:
            _IN_MEMORY[analysis_id].setdefault("progress", []).append(
                {"step": step, "label": label, "status": "done"}
            )


def complete_job(analysis_id: str, report: Dict[str, Any]) -> None:
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        r.hset(key, mapping={
            KEY_STATUS: "completed",
            KEY_STAGE: "completed",
            KEY_REPORT: json.dumps(report),
            KEY_ERROR: "",
        })
    else:
        if analysis_id in _IN_MEMORY:
            _IN_MEMORY[analysis_id].update(
                status="completed", stage="completed", report=report, error=None
            )


def fail_job(analysis_id: str, error_message: str) -> None:
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        r.hset(key, mapping={
            KEY_STATUS: "error",
            KEY_STAGE: "failed",
            KEY_ERROR: error_message,
        })
    else:
        if analysis_id in _IN_MEMORY:
            _IN_MEMORY[analysis_id].update(
                status="error", stage="failed", error=error_message
            )


def set_task_id(analysis_id: str, task_id: str) -> None:
    """Store Celery task id so we can revoke it on cancel."""
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        r.hset(key, KEY_TASK_ID, task_id)
    else:
        if analysis_id in _IN_MEMORY:
            _IN_MEMORY[analysis_id]["task_id"] = task_id


def is_job_cancelled(analysis_id: str) -> bool:
    """Return True if the job has been requested to cancel."""
    job = get_job(analysis_id)
    return job is not None and job.get("status") == "cancelled"


def cancel_job(analysis_id: str) -> None:
    """Mark job as cancelled and clear progress/report. Does not delete Pinecone data (caller does that)."""
    r = _redis_client()
    if r:
        key = job_key(analysis_id)
        r.hset(key, mapping={
            KEY_STATUS: "cancelled",
            KEY_STAGE: "cancelled",
            KEY_PROGRESS: json.dumps([]),
            KEY_REPORT: json.dumps(None),
            KEY_ERROR: "Cancelled",
        })
    else:
        if analysis_id in _IN_MEMORY:
            _IN_MEMORY[analysis_id].update(
                status="cancelled",
                stage="cancelled",
                progress=[],
                report=None,
                error="Cancelled",
            )


def use_redis() -> bool:
    return bool(settings.redis_url)
