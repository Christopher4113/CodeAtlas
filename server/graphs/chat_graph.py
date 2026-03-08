"""
LangGraph flow for the run-page chatbot. Retrieves context from Pinecone
(namespace for this analysis run) then generates a reply with the LLM.
"""
from __future__ import annotations

from typing import TypedDict, List, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from models.bedrock_llm import get_llm
from models.pinecone_client import search_in_namespace


class ChatState(TypedDict, total=False):
    namespace: str
    fallback_namespace: str  # e.g. owner/repo@branch when per-run namespace is empty
    query: str
    history: List[dict]  # [{ "role": "user"|"assistant", "content": str }]
    retrieved_docs: List[dict]
    report_context: str  # Summary/report from the analysis so LLM can answer without Pinecone
    reply: str


def _format_docs(docs: List[dict]) -> str:
    if not docs:
        return "(No relevant code or docs found for this run.)"
    parts = []
    for i, d in enumerate(docs[:10], 1):
        text = (d.get("text") or "").strip()
        path = d.get("path") or "?"
        if text:
            parts.append(f"[{i}] {path}:\n{text[:1200]}")
    return "\n\n---\n\n".join(parts) if parts else "(No relevant snippets.)"


def _merge_docs_by_id(doc_lists: List[List[dict]], max_total: int = 14) -> List[dict]:
    """Merge search results from multiple queries, dedupe by id, keep highest score."""
    seen: set = set()
    out: List[dict] = []
    for doc_list in doc_lists:
        for d in doc_list:
            vid = d.get("id") or id(d)
            if vid in seen:
                continue
            seen.add(vid)
            out.append(d)
            if len(out) >= max_total:
                return out
    return out


def node_retrieve(state: ChatState) -> ChatState:
    """Semantic search in the run's Pinecone namespace; fallback to base namespace if empty."""
    namespace = state.get("namespace") or ""
    fallback = state.get("fallback_namespace") or ""
    query = (state.get("query") or "").strip()
    if not query:
        return {**state, "retrieved_docs": []}
    # Primary: per-run namespace
    docs = search_in_namespace(namespace, query, top_k=12) if namespace else []
    # If empty, try base namespace (older runs or shared index)
    if not docs and fallback:
        docs = search_in_namespace(fallback, query, top_k=12)
    # Second pass: generic query to pull in repo card / README / how to run (same ns we got results from, or both)
    active_ns = namespace if (namespace and docs) else (fallback or namespace)
    if active_ns:
        generic = search_in_namespace(
            active_ns,
            "README how to run setup install project overview entry point",
            top_k=6,
        )
        docs = _merge_docs_by_id([docs, generic], max_total=14)
    return {**state, "retrieved_docs": docs}


def node_generate(state: ChatState) -> ChatState:
    """Build prompt from history + report context + retrieved docs and generate reply."""
    query = (state.get("query") or "").strip()
    history = state.get("history") or []
    docs = state.get("retrieved_docs") or []
    report_context = (state.get("report_context") or "").strip()
    context = _format_docs(docs)

    # Always include analysis report when available so "how do I run" etc. can be answered
    report_block = ""
    if report_context:
        report_block = f"Analysis report for this run:\n{report_context}\n\n"
    context_block = f"{report_block}Retrieved code/docs from index:\n{context}"

    llm = get_llm(max_tokens=1024)
    system = (
        "You are CodeAtlas assistant. You answer questions about this codebase using the "
        "analysis report and retrieved context below. Prefer the analysis report for things "
        "like how to run, overview, and stack; use retrieved code/docs for file-level details. "
        "If neither has enough information, say so briefly. Be concise and cite file paths when relevant."
    )
    messages: List[BaseMessage] = [SystemMessage(content=system)]

    for h in history[-10:]:  # last 10 turns
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=f"{context_block}\n\n---\n\nUser question: {query}"))

    response = llm.invoke(messages)
    reply = (response.content or "").strip()
    return {**state, "reply": reply}


def build_chat_graph():
    g = StateGraph(ChatState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", node_generate)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()
