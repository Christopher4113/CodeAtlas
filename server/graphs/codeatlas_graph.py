from __future__ import annotations

import json
import uuid
from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph

from models.bedrock_llm import get_llm
from models.github_client import (
    GitHubError,
    fetch_multiple_file_contents,
    fetch_repo_tree,
)
from models.pinecone_client import (
    ensure_index_exists,
    get_index_name,
    upsert_records,
    upsert_repo_card,
)
from settings import settings


class RepoFile(TypedDict):
    path: str
    sha: str
    size: int
    content: str | None


class Chunk(TypedDict):
    id: str
    path: str
    text: str
    start_line: int
    end_line: int


class CodeAtlasState(TypedDict, total=False):
    # Inputs
    owner: str
    repo: str
    branch: str
    github_token: str
    analysis_id: str  # When set, namespace becomes per-run for chatbot/latest tracking

    # Ingest
    repo_tree: list[RepoFile]
    files_content: dict[str, str]
    chunks: list[Chunk]

    # Analysis
    repo_summary: dict[str, Any]
    architecture_mermaid: str
    onboarding_doc: str
    dependency_mermaid: str
    bug_risks: list[str]
    frameworks_summary: str

    # Errors
    error: str


IGNORED_DIR_PREFIXES = (
    "node_modules/",
    "dist/",
    "build/",
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
)

IGNORED_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
)

# To stay within Pinecone's token-per-minute limits for the
# llama-text-embed-v2 integrated embedding model, keep the V1 ingest
# intentionally small.
MAX_FILES_FOR_V1 = 80
MAX_CHUNKS_FOR_V1 = 200


def _should_keep_path(path: str) -> bool:
    for prefix in IGNORED_DIR_PREFIXES:
        if path.startswith(prefix):
            return False
    for ext in IGNORED_EXTENSIONS:
        if path.lower().endswith(ext):
            return False
    return True


def _prioritize_paths(files: list[RepoFile]) -> list[str]:
    """
    Heuristically order files so that README, docs, and configs come
    first, then source code. This lets us stay under embedding limits
    while still getting a good picture of the repo.
    """

    def score(path: str) -> int:
        name = path.split("/")[-1]
        lower_name = name.lower()

        # Highest priority: readmes and main docs.
        if lower_name.startswith("readme"):
            return 0
        if path.startswith(("docs/", "doc/")):
            return 1

        # Important configs / dependency manifests.
        important_files = {
            "package.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "requirements.txt",
            "pyproject.toml",
            "poetry.lock",
            "setup.py",
            "go.mod",
            "Cargo.toml",
            "Gemfile",
            "composer.json",
            "Dockerfile",
            "docker-compose.yml",
        }
        if name in important_files:
            return 2

        # CI / infra / config.
        if path.startswith((".github/", "infra/", "config/")):
            return 3

        # Application and API code.
        if path.startswith(
            (
                "src/",
                "server/",
                "backend/",
                "api/",
                "app/",
                "services/",
                "functions/",
            )
        ):
            return 4

        # Everything else.
        return 10

    # Sort by score, then path for stable ordering.
    return [f["path"] for f in sorted(files, key=lambda f: (score(f["path"]), f["path"]))]


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    text = text.strip()
    try:
        return cast(dict[str, Any] | None, json.loads(text))
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return cast(dict[str, Any] | None, json.loads(text[start : end + 1]))
            except json.JSONDecodeError:
                pass
    return None


def _extract_mermaid(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if "```mermaid" in text:
        start = text.find("```mermaid") + len("```mermaid")
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    return text


def _chunk_file(path: str, text: str, max_chars: int = 2400, overlap: int = 200) -> list[Chunk]:
    """
    Simple line-based chunking. We approximate 400–800 token chunks by
    limiting to ~2.4k characters with a small overlap window.
    """
    chunks: list[Chunk] = []
    if not text:
        return chunks

    lines = text.splitlines()
    start = 0
    while start < len(lines):
        current = []
        current_len = 0
        line_idx = start
        while line_idx < len(lines) and current_len < max_chars:
            line = lines[line_idx]
            current.append(line)
            current_len += len(line) + 1
            line_idx += 1

        if not current:
            break

        chunk_text = "\n".join(current)
        chunk = Chunk(
            id=str(uuid.uuid4()),
            path=path,
            text=chunk_text,
            start_line=start + 1,
            end_line=line_idx,
        )
        chunks.append(chunk)

        if line_idx >= len(lines):
            break

        # Move the start forward with a small overlap.
        start = max(line_idx - int(overlap / 80), start + 1)

    return chunks


def _build_namespace(state: CodeAtlasState) -> str:
    if settings.codeatlas_namespace_mode == "repo":
        base = f"{state['owner']}/{state['repo']}"
    else:
        base = f"{state['owner']}/{state['repo']}@{state['branch']}"
    aid = state.get("analysis_id")
    return f"{base}@{aid}" if aid else base


def node_fetch_repo_tree(state: CodeAtlasState) -> CodeAtlasState:
    try:
        tree = fetch_repo_tree(
            owner=state["owner"],
            repo=state["repo"],
            branch=state["branch"],
            token=state["github_token"],
        )
    except GitHubError as exc:
        return {**state, "error": str(exc)}

    filtered = [f for f in tree if _should_keep_path(f["path"])]
    return {**state, "repo_tree": cast(list[RepoFile], filtered)}


def node_fetch_file_contents(state: CodeAtlasState) -> CodeAtlasState:
    if "repo_tree" not in state:
        return {**state, "error": "repo_tree missing before fetch_file_contents"}

    # For V1 only fetch a capped number of *important* files so we don't
    # blow past Pinecone token limits when embedding.
    ordered_paths = _prioritize_paths(state["repo_tree"])
    paths = ordered_paths[:MAX_FILES_FOR_V1]
    try:
        files = fetch_multiple_file_contents(
            owner=state["owner"],
            repo=state["repo"],
            branch=state["branch"],
            paths=paths,
            token=state["github_token"],
        )
    except GitHubError as exc:
        return {**state, "error": str(exc)}

    return {**state, "files_content": files}


def node_chunk_and_upsert(state: CodeAtlasState) -> CodeAtlasState:
    if "files_content" not in state:
        return {**state, "error": "files_content missing before chunk_and_upsert"}

    ensure_index_exists()

    all_chunks: list[Chunk] = []
    for path, text in state["files_content"].items():
        if len(all_chunks) >= MAX_CHUNKS_FOR_V1:
            break
        file_chunks = _chunk_file(path, text or "")
        remaining = MAX_CHUNKS_FOR_V1 - len(all_chunks)
        if remaining <= 0:
            break
        # Only include chunks with non-empty text (Pinecone embedding API rejects empty input)
        valid = [c for c in file_chunks[:remaining] if (c.get("text") or "").strip()]
        all_chunks.extend(valid)

    namespace = _build_namespace(state)

    # Upsert in small batches to avoid giant payloads. Pinecone's
    # integrated embedding API currently enforces a maximum batch size
    # of 96 records; using 32 keeps each request small and smooths out
    # token-per-minute usage. Skip batches that would have no valid records.
    batch_size = 32
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        records = []
        for ch in batch:
            raw_text = ch.get("text") or ""
            if not raw_text.strip():
                continue
            record: dict[str, Any] = {
                "id": ch["id"],
                "text": raw_text,
                "path": ch["path"],
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "repo": state["repo"],
                "owner": state["owner"],
                "branch": state["branch"],
                "index": get_index_name(),
            }
            records.append(record)
        if records:
            upsert_records(namespace, records)

    return {**state, "chunks": all_chunks}


def node_make_repo_overview(state: CodeAtlasState) -> CodeAtlasState:
    if "files_content" not in state or "repo_tree" not in state:
        return {**state, "error": "repo_tree/files_content missing before overview"}

    llm = get_llm()

    readme = ""
    for name in ("README.md", "readme.md", "README", "Readme.md"):
        if name in state["files_content"]:
            readme = state["files_content"][name]
            break

    tree_summary_lines = [f"- {f['path']}" for f in state["repo_tree"][:200]]
    tree_summary = "\n".join(tree_summary_lines)

    package_snippet = ""
    for candidate in ("package.json", "pyproject.toml", "poetry.lock", "requirements.txt"):
        if candidate in state["files_content"]:
            package_snippet = state["files_content"][candidate][:4000]
            break

    prompt = f"""
You are CodeAtlas, a tool that summarizes GitHub repositories for engineers.

Repository:
- owner: {state["owner"]}
- repo: {state["repo"]}
- branch: {state["branch"]}

README (truncated):
-------------------
{readme[:6000]}

Key dependency/config file (truncated):
---------------------------------------
{package_snippet}

File tree (first {len(tree_summary_lines)} files):
--------------------------------------------------
{tree_summary}

Using this information, produce a concise JSON object describing the repo.

Return ONLY valid JSON with this exact shape:
{{
  "short_overview": "2-4 sentence plain language overview of the repo and its purpose.",
  "how_to_run": "Step-by-step instructions to run the project locally, or 'unknown' if not clear.",
  "main_components": ["short bullet points: APIs, services, frontends, jobs, etc."],
  "stack": ["frameworks, languages, infra and major dependencies you can infer"],
  "notes": ["any other important observations, caveats, or TODOs"]
}}

Do not include backticks, markdown, or any explanation outside of the JSON.
"""

    msg = llm.invoke(prompt)
    _c = msg.content
    raw = (_c if isinstance(_c, str) else "").strip()
    summary = _extract_json(raw)
    if summary is None:
        summary = {
            "short_overview": "Model returned non-JSON output.",
            "how_to_run": "unknown",
            "main_components": [],
            "stack": [],
            "notes": [raw],
        }

    return {**state, "repo_summary": summary}


def node_make_architecture_diagram(state: CodeAtlasState) -> CodeAtlasState:
    if state.get("error"):
        return state
    if "repo_summary" not in state:
        return {**state, "error": "repo_summary missing before architecture_diagram"}

    summary = state["repo_summary"]
    components = summary.get("main_components", []) or []
    stack = summary.get("stack", []) or []
    overview = summary.get("short_overview", "")

    llm = get_llm(max_tokens=1200)
    prompt = f"""You are CodeAtlas. Given this repo summary, produce a SIMPLE architecture
diagram as Mermaid code.

Overview: {overview}
Main components: {", ".join(components) if components else "unknown"}
Stack: {", ".join(stack) if stack else "unknown"}

Output ONLY a Mermaid diagram (flowchart or graph). Keep it simple: 5-10 nodes max
showing high-level layers or components (e.g. Frontend, API, DB, Auth). Use subgraph if helpful.
Example style:
flowchart LR
  subgraph Client
    UI
  end
  subgraph Server
    API
  end
  DB[(Database)]
  UI --> API --> DB

Return ONLY the Mermaid code block, no other text. Start with ```mermaid and end with ```."""

    msg = llm.invoke(prompt)
    _c = msg.content
    raw = (_c if isinstance(_c, str) else "").strip()
    mermaid = _extract_mermaid(raw) or "flowchart LR\n  A[Repo]\n  B[Components]\n  A --> B"
    return {**state, "architecture_mermaid": mermaid}


def node_make_onboarding_doc(state: CodeAtlasState) -> CodeAtlasState:
    if state.get("error"):
        return state
    if "repo_summary" not in state or "files_content" not in state:
        return {**state, "error": "repo_summary/files_content missing before onboarding_doc"}

    summary = state["repo_summary"]
    readme = ""
    for name in ("README.md", "readme.md", "README", "Readme.md"):
        if name in state["files_content"]:
            readme = state["files_content"][name][:8000]
            break

    llm = get_llm(max_tokens=2400)
    prompt = f"""You are CodeAtlas. Create a ONE-PAGE onboarding document (plain text or markdown)
for a new developer joining this repo.

Repo: {state["owner"]}/{state["repo"]} (branch: {state["branch"]})
Overview: {summary.get("short_overview", "")}
How to run: {summary.get("how_to_run", "unknown")}
Main components: {", ".join(summary.get("main_components", []) or [])}
Stack: {", ".join(summary.get("stack", []) or [])}

README excerpt:
---
{readme[:6000]}
---

Write a single page (about 300-500 words) that includes:
1. What this repo does (2-3 sentences)
2. Tech stack and key frameworks
3. How to get started (install, run, env vars if any)
4. Main folders / entry points to know
5. Any gotchas or notes from the README

Output ONLY the onboarding document text. No preamble."""

    msg = llm.invoke(prompt)
    _c = msg.content
    doc = (_c if isinstance(_c, str) else "").strip()
    return {**state, "onboarding_doc": doc}


def node_make_dependency_graph(state: CodeAtlasState) -> CodeAtlasState:
    if state.get("error"):
        return state
    if "repo_summary" not in state or "files_content" not in state:
        return {**state, "error": "repo_summary/files_content missing before dependency_graph"}

    summary = state["repo_summary"]
    stack = summary.get("stack", []) or []
    package_snippet = ""
    for candidate in ("package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"):
        if candidate in state["files_content"]:
            package_snippet = state["files_content"][candidate][:3000]
            break

    llm = get_llm(max_tokens=1000)
    prompt = f"""You are CodeAtlas. Produce a SIMPLE dependency graph as Mermaid code for this repo.

Stack: {", ".join(stack) if stack else "unknown"}

Dependency/config excerpt:
---
{package_snippet}
---

Output ONLY a Mermaid diagram (flowchart or graph) showing key dependencies:
app -> libraries/frameworks (e.g. Next.js -> React, API -> PostgreSQL). 5-12 nodes max.
Return ONLY the Mermaid code block. Start with ```mermaid and end with ```."""

    msg = llm.invoke(prompt)
    _c = msg.content
    raw = (_c if isinstance(_c, str) else "").strip()
    default_mermaid = "flowchart LR\n  App[Application]\n  Deps[Dependencies]\n  App --> Deps"
    mermaid = _extract_mermaid(raw) or default_mermaid
    return {**state, "dependency_mermaid": mermaid}


def node_make_bug_risk_analysis(state: CodeAtlasState) -> CodeAtlasState:
    if state.get("error"):
        return state
    if "repo_summary" not in state:
        return {**state, "error": "repo_summary missing before bug_risk_analysis"}

    summary = state["repo_summary"]
    notes = summary.get("notes", []) or []
    overview = summary.get("short_overview", "")

    llm = get_llm(max_tokens=800)
    prompt = f"""You are CodeAtlas. Based on this repo summary, list potential bug risks
or areas to watch.

Overview: {overview}
Notes from analysis: {chr(10).join(notes) if notes else "None"}

Return a JSON object with a single key "bug_risks" whose value is an array of short strings
(3-8 items), e.g. ["No input validation on API", "Env vars in code"].
If you see no clear risks, return ["No major risks identified from summary."].
Output ONLY valid JSON, no markdown or explanation."""

    msg = llm.invoke(prompt)
    _c = msg.content
    raw = (_c if isinstance(_c, str) else "").strip()
    parsed = _extract_json(raw)
    risks = (parsed or {}).get("bug_risks") if isinstance(parsed, dict) else None
    if not isinstance(risks, list):
        risks = ["Bug risk analysis unavailable."]
    return {**state, "bug_risks": risks}


def node_format_frameworks(state: CodeAtlasState) -> CodeAtlasState:
    if state.get("error"):
        return state
    if "repo_summary" not in state:
        return {**state}
    stack = state["repo_summary"].get("stack") or []
    if not stack:
        return {**state, "frameworks_summary": "Unknown"}
    # Format as readable list, e.g. "Next.js, PostgreSQL with Supabase"
    frameworks_summary = ", ".join(str(s) for s in stack[:15])
    return {**state, "frameworks_summary": frameworks_summary}


def node_upsert_pinecone_reason(state: CodeAtlasState) -> CodeAtlasState:
    """Store a searchable 'reason' record in Pinecone for later discovery."""
    if state.get("error"):
        return state
    if "repo_summary" not in state or "chunks" not in state:
        return {**state}

    summary = state["repo_summary"]
    overview = summary.get("short_overview", "")
    stack = summary.get("stack", []) or []
    components = summary.get("main_components", []) or []

    reason_text = (
        f"Repository {state['owner']}/{state['repo']} (branch {state['branch']}) "
        "indexed by CodeAtlas. "
        f"Purpose: {overview} "
        f"Tech stack: {', '.join(stack)}. "
        f"Main components: {', '.join(components)}. "
        "Indexed for: architecture, onboarding, dependencies, bug risks, frameworks."
    )
    namespace = _build_namespace(state)
    upsert_repo_card(
        namespace,
        reason_text,
        owner=state["owner"],
        repo=state["repo"],
        branch=state["branch"],
    )
    return state


def build_codeatlas_graph():
    """
    Full CodeAtlas pipeline:
    - fetch tree -> fetch contents -> chunk + upsert to Pinecone
    - repo overview -> architecture diagram -> onboarding doc -> dependency graph
    - bug risk analysis -> format frameworks -> upsert Pinecone "reason" card -> END
    """
    g = StateGraph(CodeAtlasState)
    g.add_node("fetch_repo_tree", node_fetch_repo_tree)
    g.add_node("fetch_file_contents", node_fetch_file_contents)
    g.add_node("chunk_and_upsert", node_chunk_and_upsert)
    g.add_node("make_repo_overview", node_make_repo_overview)
    g.add_node("make_architecture_diagram", node_make_architecture_diagram)
    g.add_node("make_onboarding_doc", node_make_onboarding_doc)
    g.add_node("make_dependency_graph", node_make_dependency_graph)
    g.add_node("make_bug_risk_analysis", node_make_bug_risk_analysis)
    g.add_node("format_frameworks", node_format_frameworks)
    g.add_node("upsert_pinecone_reason", node_upsert_pinecone_reason)

    g.set_entry_point("fetch_repo_tree")
    g.add_edge("fetch_repo_tree", "fetch_file_contents")
    g.add_edge("fetch_file_contents", "chunk_and_upsert")
    g.add_edge("chunk_and_upsert", "make_repo_overview")
    g.add_edge("make_repo_overview", "make_architecture_diagram")
    g.add_edge("make_architecture_diagram", "make_onboarding_doc")
    g.add_edge("make_onboarding_doc", "make_dependency_graph")
    g.add_edge("make_dependency_graph", "make_bug_risk_analysis")
    g.add_edge("make_bug_risk_analysis", "format_frameworks")
    g.add_edge("format_frameworks", "upsert_pinecone_reason")
    g.add_edge("upsert_pinecone_reason", END)

    return g.compile()
