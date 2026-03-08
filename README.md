# CodeAtlas

**CodeAtlas** is an API-first code analysis platform that ingests GitHub repositories, builds structured summaries and diagrams, and lets you chat with an AI about the codebase. It uses **LangGraph** for orchestration, **Pinecone** for vector search, and **AWS Bedrock** for LLMs.

---

## Features

- **Repository analysis** – Clone a repo (via GitHub API), chunk and classify files, then run a multi-step pipeline:
  - **Repo summary** – Short overview, stack, main components, how to run
  - **Architecture diagram** – Mermaid diagram of high-level structure
  - **Onboarding doc** – Generated onboarding guide
  - **Dependency graph** – Mermaid diagram of dependencies
  - **Bug risk analysis** – LLM-generated list of potential risks
  - **Frameworks summary** – Detected frameworks and tooling
- **Vector search** – Chunks and repo metadata are embedded and stored in Pinecone (with optional integrated embeddings), so you can search repos by owner and query.
- **Chat** – After an analysis completes, you can ask questions about the codebase; the chat flow uses the analysis report plus retrieval from the run’s Pinecone namespace.
- **Cancel** – Running analyses can be cancelled; the Celery task is revoked and the run’s Pinecone namespace is cleared.
- **Flexible backend** – With no Redis, analysis runs in-process in a thread. With `REDIS_URL` set, jobs are enqueued to **Celery** and the API stays responsive while workers run the pipeline.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI     │────▶│  LangGraph  │
│  (or UI)    │     │  /v1/*       │     │  CodeAtlas  │
└─────────────┘     └──────┬───────┘     └──────┬──────┘
                          │                     │
                          │                     ├── GitHub API
                          │                     ├── Pinecone (vectors)
                          │                     └── AWS Bedrock (LLM)
                          │
                          ▼
                 ┌────────────────┐
                 │ Redis (optional)│  Celery broker + job state
                 └────────────────┘
```

- **Server** – FastAPI app in `server/`. Exposes REST endpoints for health, starting analyses, polling status, report, chat, repo search, and service health (Pinecone, Bedrock, graph).
- **Pipeline** – `server/graphs/codeatlas_graph.py` defines a LangGraph that: fetches repo tree → file contents → chunks → upserts to Pinecone → repo overview → architecture → onboarding → dependency graph → bug risks → frameworks. Progress is reported via callbacks to the job store.
- **Job store** – In-memory when Redis is not configured; otherwise Redis (status, progress, report, task_id). Celery workers read/write the same store.
- **Chat** – Separate LangGraph in `server/graphs/chat_graph.py`: retrieval from the analysis namespace (with fallback) + Bedrock-generated reply, with report summary always injected for “how do I run” style answers.

---

## Requirements

- **Python 3.11**
- **Pinecone** – API key and index (serverless or with integrated embedding model, e.g. `llama-text-embed-v2`)
- **AWS** – Bedrock access (region + model id) for LLM nodes
- **GitHub** – Personal access token for cloning and reading repo contents
- **Redis** (optional) – For Celery broker and job state; without it, analysis runs in-process in a thread

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_ORG/CodeAtlas.git
cd CodeAtlas/server
pip install -r requirements.txt
```

### 2. Environment

Create `server/.env` (or set env vars):

```env
# Required
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=codeatlas

# AWS Bedrock (required for analysis and chat)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Optional: Redis for Celery
REDIS_URL=redis://localhost:6379/0
```

Other optional settings (see `server/settings.py`): `PINECONE_CLOUD`, `PINECONE_REGION`, `PINECONE_DIMENSION`, `PINECONE_METRIC`, `PINECONE_EMBED_MODEL`, `PINECONE_TEXT_FIELD`.

### 3. Run the server

```bash
cd server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- **Health:** `GET http://localhost:8000/v1/health`
- **OpenAPI:** `http://localhost:8000/docs`

### 4. (Optional) Redis and Celery

For a proper job queue instead of in-process threads:

1. Start Redis, e.g.  
   `docker run -d -p 6379:6379 redis:7`
2. Set `REDIS_URL` in the server env.
3. Run a Celery worker from the `server` directory:

   ```bash
   cd server
   celery -A celery_app worker --loglevel=info
   ```

The API enqueues the `codeatlas.run_analysis` task when `REDIS_URL` is set; the worker consumes it and writes progress and results to Redis. Clients poll `GET /v1/analyses/{id}` for status and progress.

---

## Docker

Build and run the API server in a container:

```bash
cd server
docker build -t codeatlas-server .
docker run -p 8000:8000 --env-file .env codeatlas-server
```

Or use the image built by CI/CD (see below):

```bash
docker run -p 8000:8000 --env-file .env ghcr.io/YOUR_ORG/CodeAtlas:latest
```

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/v1/health` | Server health |
| `POST` | `/v1/analyses` | Start analysis (owner, repo, branch, github_token) |
| `GET`  | `/v1/analyses/{id}` | Get job status and progress |
| `POST` | `/v1/analyses/{id}/cancel` | Cancel running analysis |
| `GET`  | `/v1/analyses/{id}/report` | Get analysis report (when completed) |
| `POST` | `/v1/analyses/{id}/chat` | Chat about the analysis (message, optional history) |
| `POST` | `/v1/repos/search` | Search repos by owner and query (Pinecone) |
| `GET`  | `/v1/pinecone/health` | Pinecone index status |
| `POST` | `/v1/graph/ping` | LangGraph ping (Bedrock) |
| `GET`  | `/v1/bedrock/whoami` | AWS region and Bedrock model id |

---

## CI / CD

- **CI** (`.github/workflows/ci.yml`) – On every push and PR: checkout, install deps, **Ruff** (lint + format), **mypy**, **pytest** (from `server/`).
- **CD** (`.github/workflows/cd.yml`) – On push to `main` (and optional `workflow_dispatch`): build the **Docker** image from `server/Dockerfile` and push to **GitHub Container Registry** (`ghcr.io/<owner>/<repo>`). Images are tagged `latest` and with the Git SHA.

To use the published image, pull `ghcr.io/<owner>/CodeAtlas:latest` and run with the same env vars as above.

---

## Project layout

```
CodeAtlas/
├── .github/workflows/
│   ├── ci.yml          # Lint, typecheck, tests
│   └── cd.yml          # Build and push Docker image
├── server/
│   ├── app.py          # FastAPI app and routes
│   ├── run_analysis.py  # Pipeline runner (callbacks, cancellation)
│   ├── job_store.py    # In-memory / Redis job state
│   ├── celery_app.py   # Celery app (when using Redis)
│   ├── tasks.py        # Celery task: run_analysis_async
│   ├── settings.py     # Pydantic settings (Pinecone, Redis)
│   ├── graphs/
│   │   ├── codeatlas_graph.py  # Main analysis LangGraph
│   │   ├── chat_graph.py      # Chat retrieval + LLM
│   │   └── ping_graph.py      # Simple graph health check
│   ├── models/
│   │   ├── pinecone_client.py
│   │   ├── github_client.py
│   │   └── bedrock_llm.py
│   ├── tests/
│   │   └── test_health.py     # API tests
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
└── README.md
```

---

## License

See repository license file.
