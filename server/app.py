from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import threading
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()
from models.pinecone_client import describe_index, ensure_index_exists, search_repos_by_owner
from graphs.ping_graph import build_ping_graph
from job_store import (
    create_job,
    get_job,
    use_redis,
    append_progress,
    complete_job,
    fail_job,
)
from run_analysis import run_analysis


class StartAnalysisRequest(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    github_token: str


class StartAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnalysisReportResponse(BaseModel):
    analysis_id: str
    report: Dict[str, Any]


class RepoSearchRequest(BaseModel):
    query: str
    owner: str
    top_k: Optional[int] = 10


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

    def on_complete(report: Dict[str, Any]) -> None:
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
    )


app = FastAPI()


@app.post("/v1/analyses", response_model=StartAnalysisResponse)
def start_analysis(payload: StartAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    branch = payload.branch or "main"

    create_job(analysis_id, payload.owner, payload.repo, branch)

    if use_redis():
        from tasks import run_analysis_async
        run_analysis_async.delay(
            analysis_id=analysis_id,
            owner=payload.owner,
            repo=payload.repo,
            branch=branch,
            github_token=payload.github_token,
        )
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
    top_k = min(payload.top_k or 10, 50)
    results = search_repos_by_owner(
        owner=payload.owner,
        query_text=payload.query.strip(),
        top_k=top_k,
    )
    return {"owner": payload.owner, "query": payload.query, "matches": results}


@app.get("/v1/pinecone/health")
def pinecone_health():
    ensure_index_exists()
    stats = describe_index()

    namespaces = {}
    if isinstance(stats, dict):
        namespaces = stats.get("namespaces", {})

    return {
        "ok": True,
        "namespaces": namespaces,
    }

ping_graph = build_ping_graph()

@app.post("/v1/graph/ping")
def graph_ping():
    out = ping_graph.invoke({"prompt": "Reply with only: ok", "answer": ""})
    return {"ok": True, "answer": out["answer"]}

@app.get("/v1/bedrock/whoami")
def bedrock_whoami():
    import os
    return {
        "region": os.getenv("AWS_REGION"),
        "model_id": os.getenv("BEDROCK_MODEL_ID"),
    }