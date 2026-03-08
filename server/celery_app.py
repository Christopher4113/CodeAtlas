"""
Celery app using Redis as broker. Only configured when REDIS_URL is set.
"""

from celery import Celery

from settings import settings

if settings.redis_url:
    app = Celery(
        "codeatlas",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["tasks"],
    )
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.task_track_started = True
else:
    app = None
