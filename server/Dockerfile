# CodeAtlas API server
FROM python:3.11-slim

WORKDIR /app

# Install system deps: git for cloning repos, build tools for pycurl (SQS transport)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Optional: non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
