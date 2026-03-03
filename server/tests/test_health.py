from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_start_and_get_analysis():
    payload = {
        "owner": "o",
        "repo": "r",
        "branch": "main",
        "github_token": "fake",
    }

    res = client.post("/v1/analyses", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data["status"] == "queued"

    analysis_id = data["analysis_id"]
    res2 = client.get(f"/v1/analyses/{analysis_id}")
    assert res2.status_code == 200
    job = res2.json()
    assert job["analysis_id"] == analysis_id
    assert job["status"] == "queued"


def test_pinecone_health_route_exists():
    res = client.get("/v1/pinecone/health")
    assert res.status_code in (200, 500)

def test_bedrock_health_route_exists():
    res = client.get("/v1/bedrock/whoami")
    assert res.status_code in (200, 500)

def test_graph_health_route_exists():
    res = client.post("/v1/graph/ping")
    assert res.status_code in (200, 500)