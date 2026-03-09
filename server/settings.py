from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pinecone_api_key: str
    pinecone_index_name: str = "codeatlas"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_dimension: int = 1536
    pinecone_metric: str = "cosine"
    pinecone_embed_model: str = "llama-text-embed-v2"
    pinecone_text_field: str = "text"
    codeatlas_namespace_mode: str = "repo"
    # Optional: Redis URL for job state store.
    # If unset, analyses run in-process (thread).
    redis_url: str | None = None
    # Optional: SQS queue URL for Celery broker.
    # When set, Celery uses SQS instead of Redis as broker.
    sqs_queue_url: str | None = None
    # Optional: SQS region (defaults to us-east-1)
    sqs_region: str = "us-east-1"


settings = Settings()  # type: ignore[call-arg]
