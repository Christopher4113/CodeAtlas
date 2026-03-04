from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pinecone_api_key: str
    pinecone_index_name: str = "codeatlas"
    # Pinecone serverless deployment configuration
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    # When using a standalone index this dimension is used; for
    # integrated embedding indexes (like llama-text-embed-v2) the
    # dimension comes from the model configuration in Pinecone.
    pinecone_dimension: int = 1024
    pinecone_metric: str = "cosine"
    # Integrated embedding configuration – matches the Pinecone console
    # setup where the record text field is called "text".
    pinecone_embed_model: str = "llama-text-embed-v2"
    pinecone_text_field: str = "text"


settings = Settings()