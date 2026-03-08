from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Mapping, Any, List

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


def delete_namespace(namespace: str) -> None:
    """
    Delete all vectors in the given namespace (e.g. "owner/repo@branch").
    Only supported for serverless indexes. Irreversible.
    No-op if Pinecone is not configured or the operation is not supported.
    """
    try:
        index = get_index()
        index.delete_namespace(namespace=namespace)
    except Exception:
        # Pod-based indexes or missing config: ignore so cancel still succeeds
        pass


def upsert_records(namespace: str, records: Iterable[Mapping[str, Any]]) -> None:
    """
    Convenience helper that uses the integrated embedding index. Incoming
    records must include:

    - an `id` (or `_id`) field
    - a text field matching `settings.pinecone_text_field`
    - any additional metadata fields you want to filter on later

    Records with empty or whitespace-only text are skipped (embedding API requires non-empty input).
    """
    index = get_index()
    text_field = settings.pinecone_text_field
    payload = [
        r for r in records
        if r and (text_field in r) and str(r.get(text_field) or "").strip()
    ]
    if not payload:
        return
    index.upsert_records(namespace, payload)


# Stable ID for the single "repo card" record per namespace (safe for Pinecone IDs).
REPO_CARD_ID = "repo_card"


def upsert_repo_card(
    namespace: str,
    text: str,
    *,
    owner: str = "",
    repo: str = "",
    branch: str = "",
) -> None:
    """
    Upsert a single searchable record per repo namespace describing why the repo
    was indexed and a short summary. Enables semantic search later (e.g. "repos
    using Next.js", "repos with Supabase auth") and answers "why was this repo
    stored".
    """
    # Embedding API requires non-empty text
    safe_text = (text or "").strip() or "Repository indexed by CodeAtlas."
    record: Mapping[str, Any] = {
        "id": REPO_CARD_ID,
        "text": safe_text,
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "index": get_index_name(),
    }
    upsert_records(namespace, [record])


def search_in_namespace(
    namespace: str,
    query_text: str,
    top_k: int = 12,
) -> List[Mapping[str, Any]]:
    """
    Semantic search within a single namespace (e.g. one analysis run).
    Returns list of matches with score and metadata (text, path, etc.) for chatbot context.
    """
    if not query_text or not query_text.strip():
        return []
    try:
        index = get_index()
        search_result = index.search(
            namespace=namespace,
            query={"inputs": {"text": query_text.strip()}, "top_k": min(top_k, 24)},
        )
    except Exception:
        return []
    if isinstance(search_result, dict):
        matches = search_result.get("matches") or []
    else:
        matches = getattr(search_result, "matches", None) or []
    results: List[Mapping[str, Any]] = []
    for m in matches:
        score = m.get("score")
        if score is None:
            continue
        meta = m.get("metadata") or {}
        text = meta.get(settings.pinecone_text_field) or meta.get("text") or ""
        results.append({
            "score": float(score),
            "text": text[:2000] if isinstance(text, str) else str(text)[:2000],
            "path": meta.get("path"),
            "id": m.get("id"),
        })
    return results


def list_namespaces_for_owner(owner: str) -> List[str]:
    """
    Return all index namespaces that belong to the given owner.
    Namespace format is "owner/repo@branch", so we filter by prefix "owner/".
    """
    stats = describe_index()
    if hasattr(stats, "get"):
        namespaces = stats.get("namespaces") or {}
    else:
        namespaces = getattr(stats, "namespaces", None) or {}
    if not isinstance(namespaces, dict):
        return []
    prefix = f"{owner}/"
    return [ns for ns in namespaces if isinstance(ns, str) and ns.startswith(prefix)]


def search_repos_by_owner(
    owner: str,
    query_text: str,
    top_k: int = 10,
    max_namespaces: int = 50,
) -> List[Mapping[str, Any]]:
    """
    Search only within repos belonging to the given owner. Returns a list of
    matching repos (one per namespace) with score and snippet, sorted by score.
    """
    index = get_index()
    owner_ns = list_namespaces_for_owner(owner)
    if not owner_ns:
        return []

    # Cap to avoid too many API calls
    namespaces_to_search = owner_ns[:max_namespaces]
    results: List[Mapping[str, Any]] = []

    for namespace in namespaces_to_search:
        try:
            # Search within this namespace; get top 1 match to represent this repo
            search_result = index.search(
                namespace=namespace,
                query={
                    "inputs": {"text": query_text},
                    "top_k": 1,
                },
            )
        except Exception:
            continue
        if isinstance(search_result, dict):
            matches = search_result.get("matches") or []
        else:
            matches = getattr(search_result, "matches", None) or []
        if not matches:
            continue
        best = matches[0]
        score = best.get("score")
        if score is None:
            continue
        # Parse namespace "owner/repo@branch"
        parts = namespace.split("@", 1)
        branch = parts[1] if len(parts) == 2 else "main"
        owner_repo = parts[0]
        repo = owner_repo.split("/")[-1] if "/" in owner_repo else owner_repo
        ns_owner = owner_repo.rsplit("/", 1)[0] if "/" in owner_repo else owner
        text_snippet = ""
        if isinstance(best.get("metadata"), dict) and "text" in best["metadata"]:
            raw = best["metadata"]["text"]
            text_snippet = (raw[:300] + "…") if isinstance(raw, str) and len(raw) > 300 else (raw or "")
        results.append({
            "owner": ns_owner,
            "repo": repo,
            "branch": branch,
            "namespace": namespace,
            "score": float(score),
            "snippet": text_snippet,
        })

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]