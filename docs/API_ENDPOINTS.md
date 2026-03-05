# CodeAtlas API Endpoints

Base URL for the **FastAPI server**: `http://localhost:8000` (or your `FASTAPI_URL`).  
The **Next.js app** proxies some calls; use your app origin (e.g. `http://localhost:3000`) for those.

---

## Analyses (FastAPI)

### Start analysis

Runs the full CodeAtlas pipeline (fetch repo → chunk → Pinecone upsert → repo summary → architecture diagram → onboarding doc → dependency graph → bug risks → frameworks → Pinecone repo card).

- **Method:** `POST`
- **Path:** `/v1/analyses`
- **Body (JSON):**
  ```json
  {
    "owner": "github-username",
    "repo": "repo-name",
    "branch": "main",
    "github_token": "ghp_..."
  }
  ```
  `branch` and `github_token` are required; `branch` defaults to `main` if omitted.

- **Example (curl):**
  ```bash
  curl -X POST "http://localhost:8000/v1/analyses" \
    -H "Content-Type: application/json" \
    -d '{"owner":"myuser","repo":"myrepo","branch":"main","github_token":"YOUR_GITHUB_TOKEN"}'
  ```

- **Response (200):**
  ```json
  {
    "analysis_id": "uuid",
    "status": "completed",
    "report": {
      "repo_summary": { "short_overview": "...", "how_to_run": "...", "main_components": [], "stack": [], "notes": [] },
      "architecture_mermaid": "flowchart LR\n  ...",
      "onboarding_doc": "One-page onboarding text...",
      "dependency_mermaid": "flowchart LR\n  ...",
      "bug_risks": ["risk1", "risk2"],
      "frameworks_summary": "Next.js, PostgreSQL, Supabase"
    },
    "error": null
  }
  ```

---

### Get analysis status

- **Method:** `GET`
- **Path:** `/v1/analyses/{analysis_id}`

- **Example (curl):**
  ```bash
  curl "http://localhost:8000/v1/analyses/YOUR_ANALYSIS_ID"
  ```

- **Response (200):** Full job object including `status`, `stage`, `report` (when completed), `error` (if failed).

---

### Get analysis report

- **Method:** `GET`
- **Path:** `/v1/analyses/{analysis_id}/report`

- **Example (curl):**
  ```bash
  curl "http://localhost:8000/v1/analyses/YOUR_ANALYSIS_ID/report"
  ```

- **Response (200):**
  ```json
  {
    "analysis_id": "uuid",
    "report": { ... }
  }
  ```

---

## Repo search (Pinecone, owner-scoped)

Returns only repos that belong to the given **owner** (no random repos from other users).

- **Method:** `POST`
- **Path:** `/v1/repos/search`
- **Body (JSON):**
  ```json
  {
    "query": "Next.js Supabase",
    "owner": "github-username",
    "top_k": 10
  }
  ```
  `owner` is required. `top_k` is optional (default 10, max 50).

- **Example (curl):**
  ```bash
  curl -X POST "http://localhost:8000/v1/repos/search" \
    -H "Content-Type: application/json" \
    -d '{"query":"Next.js Supabase","owner":"myuser","top_k":10}'
  ```

- **Response (200):**
  ```json
  {
    "owner": "myuser",
    "query": "Next.js Supabase",
    "matches": [
      {
        "owner": "myuser",
        "repo": "myapp",
        "branch": "main",
        "namespace": "myuser/myapp@main",
        "score": 0.89,
        "snippet": "Repository myuser/myapp (branch main) indexed by CodeAtlas. Purpose: ..."
      }
    ]
  }
  ```

---

## Pinecone

### Health / index stats

- **Method:** `GET`
- **Path:** `/v1/pinecone/health`

- **Example (curl):**
  ```bash
  curl "http://localhost:8000/v1/pinecone/health"
  ```

- **Response (200):**
  ```json
  {
    "ok": true,
    "namespaces": { "owner/repo@branch": { "record_count": 123 }, ... }
  }
  ```

---

## Graph / Bedrock (dev)

### Graph ping

- **Method:** `POST`
- **Path:** `/v1/graph/ping`

- **Example (curl):**
  ```bash
  curl -X POST "http://localhost:8000/v1/graph/ping"
  ```

### Bedrock whoami

- **Method:** `GET`
- **Path:** `/v1/bedrock/whoami`

- **Example (curl):**
  ```bash
  curl "http://localhost:8000/v1/bedrock/whoami"
  ```

---

## Next.js API routes (authenticated)

These require a valid Supabase session (cookie). Use the Next.js app origin.

### Start analysis (via Next.js)

- **Method:** `POST`
- **Path:** `/api/analysis/start`
- **Body (JSON):**
  ```json
  { "owner": "myuser", "repo": "myrepo", "branch": null }
  ```
  GitHub token is taken from the session.

- **Example (from browser or with session cookie):**
  ```bash
  curl -X POST "http://localhost:3000/api/analysis/start" \
    -H "Content-Type: application/json" \
    -d '{"owner":"myuser","repo":"myrepo"}' \
    --cookie "sb-...=..."
  ```

### Get analysis (via Next.js)

- **Method:** `GET`
- **Path:** `/api/analysis/{id}`

### Search repos (via Next.js)

- **Method:** `POST`
- **Path:** `/api/repos/search`
- **Body (JSON):**
  ```json
  { "query": "Next.js", "owner": null, "top_k": 10 }
  ```
  If `owner` is omitted, the GitHub username is resolved from the session.

- **Example:**
  ```bash
  curl -X POST "http://localhost:3000/api/repos/search" \
    -H "Content-Type: application/json" \
    -d '{"query":"Next.js"}' \
    --cookie "sb-...=..."
  ```

---

## Quick test checklist

| Action                    | Endpoint                      | Method |
|---------------------------|-------------------------------|--------|
| Health check              | `/v1/pinecone/health`         | GET    |
| Start repo analysis       | `/v1/analyses`                | POST   |
| Get analysis status       | `/v1/analyses/{id}`          | GET    |
| Get analysis report       | `/v1/analyses/{id}/report`    | GET    |
| Search repos (owner-only) | `/v1/repos/search`           | POST   |
| Graph ping                | `/v1/graph/ping`              | POST   |
| Bedrock config            | `/v1/bedrock/whoami`          | GET    |
