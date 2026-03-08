"""
Core analysis runner: streams graph steps and reports progress via callbacks.
Used by both the in-process thread and the Celery task.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from graphs.codeatlas_graph import build_codeatlas_graph
from job_store import is_job_cancelled

NODE_LABELS: dict[str, str] = {
    "fetch_repo_tree": "Cloning repository",
    "fetch_file_contents": "Ingesting files",
    "chunk_and_upsert": "Classifying file types",
    "make_repo_overview": "Summarizing code structure",
    "make_architecture_diagram": "Building architecture diagram",
    "make_onboarding_doc": "Writing onboarding doc",
    "make_dependency_graph": "Mapping dependencies",
    "make_bug_risk_analysis": "Detecting bug risks",
    "format_frameworks": "Formatting frameworks",
    "upsert_pinecone_reason": "Finalizing",
}


def run_analysis(
    owner: str,
    repo: str,
    branch: str,
    github_token: str,
    on_progress: Callable[[str, str], None],
    on_complete: Callable[[dict[str, Any]], None],
    on_error: Callable[[str], None],
    analysis_id: str | None = None,
) -> None:
    """
    Run the CodeAtlas graph; call on_progress(step, label) per node,
    on_complete(report) on success, on_error(message) on failure.
    If analysis_id is set, checks for cancellation and calls on_error("Cancelled") if cancelled.
    """
    graph = build_codeatlas_graph()
    initial_input: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "github_token": github_token,
    }
    if analysis_id:
        initial_input["analysis_id"] = analysis_id

    try:
        last_state: dict[str, Any] = {}
        for mode, chunk in graph.stream(
            initial_input, stream_mode=["updates", "values"]
        ):
            if analysis_id and is_job_cancelled(analysis_id):
                on_error("Cancelled")
                return
            if mode == "updates" and chunk:
                node_name = next(iter(chunk.keys()), None)
                if node_name:
                    label = NODE_LABELS.get(
                        node_name, node_name.replace("_", " ").title()
                    )
                    on_progress(node_name, label)
            elif mode == "values" and isinstance(chunk, dict):
                last_state = chunk

        report: dict[str, Any] = {
            "repo_summary": last_state.get("repo_summary"),
            "architecture_mermaid": last_state.get("architecture_mermaid"),
            "onboarding_doc": last_state.get("onboarding_doc"),
            "dependency_mermaid": last_state.get("dependency_mermaid"),
            "bug_risks": last_state.get("bug_risks"),
            "frameworks_summary": last_state.get("frameworks_summary"),
        }
        on_complete(report)
    except Exception as exc:
        on_error(str(exc))
