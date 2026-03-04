from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Mapping, Any

from pinecone import Pinecone, ServerlessSpec

from settings import settings


@lru_cache(maxsize=1)
def get_pinecone() -> Pinecone:
    return Pinecone(api_key=settings.pinecone_api_key)


def ensure_index_exists() -> None:
    """
    Ensure the Pinecone index exists.

    For V1 we assume an integrated embedding index using
    `llama-text-embed-v2`, matching the configuration shown in the
    Pinecone console (record field: `text`).
    """
    pc = get_pinecone()
    name = settings.pinecone_index_name

    existing = {i["name"] for i in pc.list_indexes()}
    if name not in existing:
        # Use the newer helper which configures the index for the
        # specified embedding model so that upsert_records will
        # automatically call the hosted llama-text-embed-v2 model.
        pc.create_index_for_model(
            name=name,
            cloud=settings.pinecone_cloud,
            region=settings.pinecone_region,
            metric=settings.pinecone_metric,
            embed={
                "model": settings.pinecone_embed_model,
                "field_map": {settings.pinecone_text_field: "text"},
            },
        )


def get_index_name() -> str:
    return settings.pinecone_index_name


def get_index():
    pc = get_pinecone()
    return pc.Index(settings.pinecone_index_name)


def describe_index():
    index = get_index()
    return index.describe_index_stats()


def upsert_records(namespace: str, records: Iterable[Mapping[str, Any]]) -> None:
    """
    Convenience helper that uses the integrated embedding index. Incoming
    records must include:

    - an `id` (or `_id`) field
    - a text field matching `settings.pinecone_text_field`
    - any additional metadata fields you want to filter on later
    """
    index = get_index()
    # Pinecone SDK expects a list; convert any iterable just in case.
    payload = list(records)
    if not payload:
        return
    index.upsert_records(namespace, payload)