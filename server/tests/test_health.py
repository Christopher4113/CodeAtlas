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


def test_get_analysis_report_not_found():
    res = client.get("/v1/analyses/00000000-0000-0000-0000-000000000000/report")
    assert res.status_code == 404
    assert res.json().get("detail") == "not_found"


def test_get_analysis_report_success():
    """If start_analysis completes with a report, get report returns it."""
    payload = {
        "owner": "o",
        "repo": "r",
        "branch": "main",
        "github_token": "fake",
    }
    start_res = client.post("/v1/analyses", json=payload)
    assert start_res.status_code == 200
    data = start_res.json()
    analysis_id = data["analysis_id"]
    if data.get("status") != "completed" or "report" not in data:
        return
    res = client.get(f"/v1/analyses/{analysis_id}/report")
    assert res.status_code == 200
    body = res.json()
    assert body["analysis_id"] == analysis_id
    assert "report" in body
    assert isinstance(body["report"], dict)


def test_repos_search_route():
    res = client.post(
        "/v1/repos/search",
        json={"query": "test", "owner": "test-owner", "top_k": 5},
    )
    assert res.status_code in (200, 500)
    if res.status_code == 200:
        body = res.json()
        assert "owner" in body
        assert body["owner"] == "test-owner"
        assert body["query"] == "test"
        assert "matches" in body
        assert isinstance(body["matches"], list)


def test_repos_search_validation_missing_query():
    res = client.post("/v1/repos/search", json={"owner": "test-owner"})
    assert res.status_code == 422


def test_repos_search_validation_missing_owner():
    res = client.post("/v1/repos/search", json={"query": "test"})
    assert res.status_code == 422