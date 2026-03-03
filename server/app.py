from pydantic import BaseModel
from typing import Optional, Dict
import uuid
from fastapi import FastAPI, HTTPException
from typing import Dict
from models.pinecone_client import describe_index, ensure_index_exists

class StartAnalysisRequest(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    github_token: str


class StartAnalysisResponse(BaseModel):
    analysis_id: str
    status: str


app = FastAPI()

JOBS: Dict[str, dict] = {}


@app.post("/v1/analyses", response_model=StartAnalysisResponse)
def start_analysis(payload: StartAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    JOBS[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "queued",
        "stage": "queued",
        "owner": payload.owner,
        "repo": payload.repo,
        "branch": payload.branch or "main",
    }

    # TODO: enqueue to SQS here (analysis_id)
    return {"analysis_id": analysis_id, "status": "queued"}


@app.get("/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    job = JOBS.get(analysis_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    return job


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