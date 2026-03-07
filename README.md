# CodeAtlas

## Analysis job queue (Redis + Celery)

Analysis runs in the background. By default (no Redis), jobs run in an in-process thread. For a proper message queue:

1. Set `REDIS_URL` in the server env (e.g. `REDIS_URL=redis://localhost:6379/0`).
2. Start Redis (e.g. `docker run -d -p 6379:6379 redis:7`).
3. Run the Celery worker from the `server` directory:
   ```bash
   cd server && celery -A celery_app worker --loglevel=info
   ```

The API enqueues the `codeatlas.run_analysis` task when `REDIS_URL` is set; the worker consumes it and writes progress and results to Redis. The frontend polls `GET /v1/analyses/{id}` for status and progress.