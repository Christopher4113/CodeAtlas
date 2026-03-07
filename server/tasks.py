"""
Celery tasks. The analysis task runs the graph and writes progress/results to the job store.
"""
from __future__ import annotations

from job_store import append_progress, complete_job, fail_job, get_job, use_redis
from run_analysis import run_analysis


def run_analysis_task(
    analysis_id: str,
    owner: str,
    repo: str,
    branch: str,
    github_token: str,
) -> None:
    """
    Celery task: run the analysis and update job state in Redis via job_store.
    """
    job = get_job(analysis_id)
    if not job or job.get("status") != "running":
        return

    def on_progress(step: str, label: str) -> None:
        append_progress(analysis_id, step, label)

    def on_complete(report: dict) -> None:
        complete_job(analysis_id, report)

    def on_error(message: str) -> None:
        fail_job(analysis_id, message)

    run_analysis(
        owner=owner,
        repo=repo,
        branch=branch,
        github_token=github_token,
        on_progress=on_progress,
        on_complete=on_complete,
        on_error=on_error,
    )


# Only register the task when Celery is configured (Redis URL set).
if use_redis():
    from celery_app import app

    @app.task(bind=True, name="codeatlas.run_analysis")
    def run_analysis_async(
        self,
        analysis_id: str,
        owner: str,
        repo: str,
        branch: str,
        github_token: str,
    ) -> None:
        run_analysis_task(
            analysis_id=analysis_id,
            owner=owner,
            repo=repo,
            branch=branch,
            github_token=github_token,
        )
