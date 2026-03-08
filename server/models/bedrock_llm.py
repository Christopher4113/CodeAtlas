import os
from functools import lru_cache

from langchain_aws import ChatBedrock


@lru_cache(maxsize=8)
def get_llm(max_tokens: int = 600) -> ChatBedrock:
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")
    region = os.getenv("AWS_REGION", "us-east-1")

    return ChatBedrock(  # type: ignore[call-arg]
        model_id=model_id,
        region_name=region,
        provider="anthropic",
        model_kwargs={
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
    )
