"""
Celery app. Supports SQS as broker (when SQS_QUEUE_URL is set) with Redis as result backend,
or Redis as both broker and backend (legacy mode when only REDIS_URL is set).
"""

from celery import Celery

from settings import settings


def _build_celery_app() -> Celery | None:
    """Build and configure the Celery app based on available settings."""
    if settings.sqs_queue_url and settings.redis_url:
        # SQS broker + Redis result backend
        app = Celery(
            "codeatlas",
            broker="sqs://",
            backend=settings.redis_url,
            include=["tasks"],
        )
        app.conf.broker_transport_options = {
            "region": settings.sqs_region,
            "predefined_queues": {
                "celery": {
                    "url": settings.sqs_queue_url,
                },
            },
        }
        app.conf.task_default_queue = "celery"
        app.conf.task_create_missing_queues = False
    elif settings.redis_url:
        # Legacy: Redis as both broker and backend
        app = Celery(
            "codeatlas",
            broker=settings.redis_url,
            backend=settings.redis_url,
            include=["tasks"],
        )
    else:
        return None

    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.task_track_started = True
    app.conf.broker_connection_retry_on_startup = True
    return app


app = _build_celery_app()
