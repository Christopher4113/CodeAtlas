import os
import threading
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

# Env must be loaded before first-party imports that use settings (E402 acceptable here)
from graphs.ping_graph import build_ping_graph  # noqa: E402, I001
from job_store import (  # noqa: E402, I001
    append_progress,
    cancel_job,
    complete_job,
    create_job,
    fail_job,
    get_job,
    set_task_id,
    use_redis,
)
from settings import settings  # noqa: E402, I001
from models.pinecone_client import (  # noqa: E402, I001
    delete_namespace as pinecone_delete_namespace,
    describe_index,
    ensure_index_exists,
    search_repos_by_owner,
)
from run_analysis import run_analysis  # noqa: E402, I001


class StartAnalysisRequest(BaseModel):
    owner: str
    repo: str
    branch: str | None = None
    github_token: str


class StartAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    report: dict | None = None
    error: str | None = None


class AnalysisReportResponse(BaseModel):
    analysis_id: str
    report: dict[str, Any]


class RepoSearchRequest(BaseModel):
    query: str
    owner: str
    top_k: int | None = 10


class ChatRequest(BaseModel):
    message: str
    # [{ "role": "user"|"assistant", "content": "..." }]
    history: list[dict[str, str]] | None = None


def _run_analysis_in_process(
    analysis_id: str,
    owner: str,
    repo: str,
    branch: str,
    github_token: str,
) -> None:
    """Run analysis in-process (thread) and update job_store (in-memory)."""

    def on_progress(step: str, label: str) -> None:
        append_progress(analysis_id, step, label)

    def on_complete(report: dict[str, Any]) -> None:
        complete_job(analysis_id, report)

    def on_error(message: str) -> None:
        fail_job(analysis_id, message)

    run_analysis(
        owner=owner,
        repo=repo,
        branch=branch,
        github_token=github_token,
        on_progress=on_progress,
        on_complete=on_complete,
        on_error=on_error,
        analysis_id=analysis_id,
    )


app = FastAPI()


@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "CodeAtlas server is running"}


@app.post("/v1/analyses", response_model=StartAnalysisResponse)
def start_analysis(payload: StartAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    branch = payload.branch or "main"

    create_job(analysis_id, payload.owner, payload.repo, branch)

    if use_redis():
        from tasks import run_analysis_async

        result = run_analysis_async.delay(
            analysis_id=analysis_id,
            owner=payload.owner,
            repo=payload.repo,
            branch=branch,
            github_token=payload.github_token,
        )
        set_task_id(analysis_id, result.id)
    else:
        thread = threading.Thread(
            target=_run_analysis_in_process,
            kwargs={
                "analysis_id": analysis_id,
                "owner": payload.owner,
                "repo": payload.repo,
                "branch": branch,
                "github_token": payload.github_token,
            },
            daemon=True,
        )
        thread.start()

    return {"analysis_id": analysis_id, "status": "running", "report": None, "error": None}


@app.get("/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    job = get_job(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    return job


@app.post("/v1/analyses/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str):
    """
    Cancel a running analysis: revoke Celery task (if any), delete Pinecone
    namespace for this repo, and mark the job as cancelled.
    """
    job = get_job(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    if job.get("status") != "running":
        raise HTTPException(
            status_code=400,
            detail="not_running",
        )
    task_id = job.get("task_id")
    if use_redis() and task_id:
        from celery_app import app as celery_app

        celery_app.control.revoke(task_id, terminate=True)
    namespace, _, _ = _analysis_namespace(analysis_id)
    try:
        pinecone_delete_namespace(namespace)
    except Exception:
        pass
    cancel_job(analysis_id)
    return {"analysis_id": analysis_id, "status": "cancelled"}


def _analysis_namespace(analysis_id: str) -> tuple[str | None, str | None, dict | None]:
    """Return (namespace, fallback_namespace, job) or (None, None, None) if not found."""
    job = get_job(analysis_id)
    if not job:
        return None, None, None
    owner = job.get("owner") or ""
    repo = job.get("repo") or ""
    branch = job.get("branch") or "main"
    if settings.codeatlas_namespace_mode == "repo":
        base = f"{owner}/{repo}"
    else:
        base = f"{owner}/{repo}@{branch}"
    namespace = f"{base}@{analysis_id}"
    fallback = base
    return namespace, fallback, job


def _format_report_for_chat(report: dict | None) -> str:
    """Build a short text summary of the analysis report for the chatbot context."""
    if not report:
        return ""
    parts = []
    summary = report.get("repo_summary") or {}
    if isinstance(summary, dict):
        if summary.get("short_overview"):
            parts.append(f"Overview: {summary['short_overview']}")
        if summary.get("how_to_run") and str(summary.get("how_to_run")).lower() != "unknown":
            parts.append(f"How to run: {summary['how_to_run']}")
        stack = summary.get("stack")
        if stack:
            parts.append(f"Stack: {', '.join(str(s) for s in stack[:15])}")
        components = summary.get("main_components")
        if components:
            parts.append(f"Main components: {', '.join(str(c) for c in components[:10])}")
    fw = report.get("frameworks_summary")
    if fw and str(fw).strip() != "Unknown":
        parts.append(f"Frameworks: {fw}")
    return "\n".join(parts) if parts else ""


@app.post("/v1/analyses/{analysis_id}/chat")
def chat_for_analysis(analysis_id: str, payload: ChatRequest):
    """
    Chat about this analysis using Pinecone namespace and stored report.
    LangGraph: retrieve (with fallback) -> generate reply. Report summary is always
    injected so "how do I run" etc. can be answered when Pinecone returns nothing.
    """
    namespace, fallback, job = _analysis_namespace(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="analysis_not_completed")
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message_required")
    report_context = _format_report_for_chat(job.get("report"))
    from graphs.chat_graph import build_chat_graph

    graph = build_chat_graph()
    result = graph.invoke(
        {
            "namespace": namespace or "",
            "fallback_namespace": fallback or "",
            "query": message,
            "history": payload.history or [],
            "report_context": report_context,
        }
    )
    reply = result.get("reply") or ""
    return {"reply": reply, "analysis_id": analysis_id}


@app.get("/v1/analyses/{analysis_id}/report", response_model=AnalysisReportResponse)
def get_analysis_report(analysis_id: str):
    job = get_job(analysis_id)
    if not job or "report" not in job:
        raise HTTPException(status_code=404, detail="not_found")
    return {"analysis_id": analysis_id, "report": job["report"]}


@app.post("/v1/repos/search")
def search_repos(payload: RepoSearchRequest):
    """
    Search repos in Pinecone scoped to a single owner. Returns only repos belonging
    to the given owner (use the authenticated user's GitHub username as owner).
    """
    try:
        top_k = min(payload.top_k or 10, 50)
        results = search_repos_by_owner(
            owner=payload.owner,
            query_text=payload.query.strip(),
            top_k=top_k,
        )
        return {"owner": payload.owner, "query": payload.query, "matches": results}
    except Exception as err:
        raise HTTPException(status_code=500, detail="search_failed") from err


@app.get("/v1/pinecone/health")
def pinecone_health():
    try:
        ensure_index_exists()
        stats = describe_index()

        namespaces = {}
        if isinstance(stats, dict):
            namespaces = stats.get("namespaces", {})

        return {
            "ok": True,
            "namespaces": namespaces,
        }
    except Exception:
        return {"ok": False, "namespaces": {}}


ping_graph = build_ping_graph()


@app.post("/v1/graph/ping")
def graph_ping():
    try:
        out = ping_graph.invoke({"prompt": "Reply with only: ok", "answer": ""})
        return {"ok": True, "answer": out["answer"]}
    except Exception:
        return {"ok": False, "answer": ""}


@app.get("/v1/bedrock/whoami")
def bedrock_whoami():
    return {
        "region": os.getenv("AWS_REGION"),
        "model_id": os.getenv("BEDROCK_MODEL_ID"),
    }
