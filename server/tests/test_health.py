from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health():
    res = client.get("/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert "message" in data


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


def test_cancel_analysis_not_found():
    res = client.post("/v1/analyses/00000000-0000-0000-0000-000000000000/cancel")
    assert res.status_code == 404
    assert res.json().get("detail") == "not_found"


def test_cancel_analysis_not_running():
    """Second cancel on same analysis returns 400 (job already cancelled)."""
    payload = {"owner": "o", "repo": "r", "branch": "main", "github_token": "fake"}
    start_res = client.post("/v1/analyses", json=payload)
    assert start_res.status_code == 200
    analysis_id = start_res.json()["analysis_id"]
    first = client.post(f"/v1/analyses/{analysis_id}/cancel")
    assert first.status_code == 200
    second = client.post(f"/v1/analyses/{analysis_id}/cancel")
    assert second.status_code == 400
    assert second.json().get("detail") == "not_running"


def test_cancel_analysis_success():
    payload = {"owner": "o", "repo": "r", "branch": "main", "github_token": "fake"}
    start_res = client.post("/v1/analyses", json=payload)
    assert start_res.status_code == 200
    analysis_id = start_res.json()["analysis_id"]
    res = client.post(f"/v1/analyses/{analysis_id}/cancel")
    assert res.status_code == 200
    assert res.json().get("status") == "cancelled"
    assert res.json().get("analysis_id") == analysis_id


def test_chat_analysis_not_found():
    res = client.post(
        "/v1/analyses/00000000-0000-0000-0000-000000000000/chat",
        json={"message": "hello"},
    )
    assert res.status_code == 404
    assert res.json().get("detail") == "not_found"


def test_chat_analysis_not_completed():
    """Chat on a running (not yet completed) analysis returns 400."""
    payload = {"owner": "o", "repo": "r", "branch": "main", "github_token": "fake"}
    start_res = client.post("/v1/analyses", json=payload)
    assert start_res.status_code == 200
    analysis_id = start_res.json()["analysis_id"]
    res = client.post(
        f"/v1/analyses/{analysis_id}/chat",
        json={"message": "How do I run this?"},
    )
    assert res.status_code == 400
    assert res.json().get("detail") == "analysis_not_completed"


def test_chat_message_required():
    """Chat with empty message returns 400."""
    payload = {"owner": "o", "repo": "r", "branch": "main", "github_token": "fake"}
    start_res = client.post("/v1/analyses", json=payload)
    assert start_res.status_code == 200
    analysis_id = start_res.json()["analysis_id"]
    res = client.post(
        f"/v1/analyses/{analysis_id}/chat",
        json={"message": "   "},
    )
    assert res.status_code == 400
    assert res.json().get("detail") == "message_required"


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