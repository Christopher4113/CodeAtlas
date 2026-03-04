from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()
from models.pinecone_client import describe_index, ensure_index_exists
from graphs.ping_graph import build_ping_graph
from graphs.codeatlas_graph import build_codeatlas_graph


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


app = FastAPI()

JOBS: Dict[str, dict] = {}

codeatlas_graph = build_codeatlas_graph()


@app.post("/v1/analyses", response_model=StartAnalysisResponse)
def start_analysis(payload: StartAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    branch = payload.branch or "main"

    base_job = {
        "analysis_id": analysis_id,
        "status": "running",
        "stage": "running",
        "owner": payload.owner,
        "repo": payload.repo,
        "branch": branch,
    }
    JOBS[analysis_id] = base_job

    try:
        result = codeatlas_graph.invoke(
            {
                "owner": payload.owner,
                "repo": payload.repo,
                "branch": branch,
                "github_token": payload.github_token,
            }
        )
    except Exception as exc:
        # Surface the underlying error to the client instead of
        # returning a generic 500 so it is easier to debug.
        error_message = str(exc)
        JOBS[analysis_id] = {
            **base_job,
            "status": "error",
            "stage": "failed",
            "error": error_message,
        }
        return {
            "analysis_id": analysis_id,
            "status": "error",
            "report": None,
            "error": error_message,
        }

    report: Dict[str, Any] = {
        "repo_summary": result.get("repo_summary"),
    }

    JOBS[analysis_id] = {
        **base_job,
        "status": "completed",
        "stage": "completed",
        "report": report,
    }

    # For V1, run synchronously and return the report payload directly.
    return {"analysis_id": analysis_id, "status": "completed", "report": report, "error": None}


@app.get("/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    job = JOBS.get(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    return job


@app.get("/v1/analyses/{analysis_id}/report", response_model=AnalysisReportResponse)
def get_analysis_report(analysis_id: str):
    job = JOBS.get(analysis_id)
    if not job or "report" not in job:
        raise HTTPException(status_code=404, detail="not_found")
    return {"analysis_id": analysis_id, "report": job["report"]}


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