from __future__ import annotations

from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec

from settings import settings


@lru_cache(maxsize=1)
def get_pinecone() -> Pinecone:
    return Pinecone(api_key=settings.pinecone_api_key)


def ensure_index_exists() -> None:
    pc = get_pinecone()
    name = settings.pinecone_index_name

    existing = {i["name"] for i in pc.list_indexes()}
    if name not in existing:
        pc.create_index(
            name=name,
            dimension=settings.pinecone_dimension,
            metric=settings.pinecone_metric,
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )


def describe_index():
    pc = get_pinecone()
    index = pc.Index(settings.pinecone_index_name)
    return index.describe_index_stats()