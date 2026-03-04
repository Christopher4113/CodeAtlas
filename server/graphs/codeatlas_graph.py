from __future__ import annotations

import json
import uuid
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, END

from models.bedrock_llm import get_llm
from models.github_client import fetch_repo_tree, fetch_multiple_file_contents, GitHubError
from models.pinecone_client import ensure_index_exists, upsert_records, get_index_name


class RepoFile(TypedDict):
    path: str
    sha: str
    size: int
    content: Optional[str]


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

    # Ingest
    repo_tree: List[RepoFile]
    files_content: Dict[str, str]
    chunks: List[Chunk]

    # Analysis
    repo_summary: Dict[str, Any]

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


def _prioritize_paths(files: List[RepoFile]) -> List[str]:
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


def _chunk_file(path: str, text: str, max_chars: int = 2400, overlap: int = 200) -> List[Chunk]:
    """
    Simple line-based chunking. We approximate 400–800 token chunks by
    limiting to ~2.4k characters with a small overlap window.
    """
    chunks: List[Chunk] = []
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
    # Use a simple namespace so we can re-index different branches
    # independently if needed.
    return f"{state['owner']}/{state['repo']}@{state['branch']}"


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
    return {**state, "repo_tree": filtered}


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

    all_chunks: List[Chunk] = []
    for path, text in state["files_content"].items():
        if len(all_chunks) >= MAX_CHUNKS_FOR_V1:
            break
        file_chunks = _chunk_file(path, text)
        remaining = MAX_CHUNKS_FOR_V1 - len(all_chunks)
        if remaining <= 0:
            break
        all_chunks.extend(file_chunks[:remaining])

    namespace = _build_namespace(state)

    # Upsert in small batches to avoid giant payloads. Pinecone's
    # integrated embedding API currently enforces a maximum batch size
    # of 96 records; using 32 keeps each request small and smooths out
    # token-per-minute usage.
    batch_size = 32
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        records = []
        for ch in batch:
            record: Dict[str, Any] = {
                "id": ch["id"],
                "text": ch["text"],
                "path": ch["path"],
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "repo": state["repo"],
                "owner": state["owner"],
                "branch": state["branch"],
                "index": get_index_name(),
            }
            records.append(record)
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

    tree_summary_lines = [
        f"- {f['path']}" for f in state["repo_tree"][:200]
    ]
    tree_summary = "\n".join(tree_summary_lines)

    package_snippet = ""
    for candidate in ("package.json", "pyproject.toml", "poetry.lock", "requirements.txt"):
        if candidate in state["files_content"]:
            package_snippet = state["files_content"][candidate][:4000]
            break

    prompt = f"""
You are CodeAtlas, a tool that summarizes GitHub repositories for engineers.

Repository:
- owner: {state['owner']}
- repo: {state['repo']}
- branch: {state['branch']}

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
  "main_components": ["short bullet point strings naming the key pieces (APIs, services, frontends, jobs, etc.)"],
  "stack": ["frameworks, languages, infra and major dependencies you can infer"],
  "notes": ["any other important observations, caveats, or TODOs"]
}}

Do not include backticks, markdown, or any explanation outside of the JSON.
"""

    msg = llm.invoke(prompt)
    raw = msg.content.strip()

    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        # Strip markdown code fences if present.
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the first { and last } and parse that.
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return None

    summary = extract_json(raw)
    if summary is None:
        summary = {
            "short_overview": "Model returned non-JSON output.",
            "how_to_run": "unknown",
            "main_components": [],
            "stack": [],
            "notes": [raw],
        }

    return {**state, "repo_summary": summary}


def build_codeatlas_graph():
    """
    Smallest useful slice:
    - fetch tree
    - fetch contents
    - chunk + upsert to Pinecone
    - single analysis node: repo overview
    """
    g = StateGraph(CodeAtlasState)
    g.add_node("fetch_repo_tree", node_fetch_repo_tree)
    g.add_node("fetch_file_contents", node_fetch_file_contents)
    g.add_node("chunk_and_upsert", node_chunk_and_upsert)
    g.add_node("make_repo_overview", node_make_repo_overview)

    g.set_entry_point("fetch_repo_tree")
    g.add_edge("fetch_repo_tree", "fetch_file_contents")
    g.add_edge("fetch_file_contents", "chunk_and_upsert")
    g.add_edge("chunk_and_upsert", "make_repo_overview")
    g.add_edge("make_repo_overview", END)

    return g.compile()

