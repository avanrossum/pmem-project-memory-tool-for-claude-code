"""Retrieval and optional LLM synthesis."""

from __future__ import annotations

from typing import Any

import httpx

from project_memory.config import ProjectConfig
from project_memory.indexer import embed_texts, run_index
from project_memory.store import ChunkStore


def retrieve(question: str, config: ProjectConfig, top_k: int | None = None) -> list[dict[str, Any]]:
    """Retrieve the most relevant chunks for a question.

    Optionally runs an incremental reindex if auto_reindex_on_query is enabled.
    """
    if config.query.auto_reindex_on_query:
        run_index(config)

    k = top_k or config.query.top_k
    embeddings = embed_texts([question], config)
    store = ChunkStore(config)

    if store.count == 0:
        return []

    return store.query(embeddings[0], top_k=k)


def synthesize(question: str, chunks: list[dict[str, Any]], config: ProjectConfig) -> str:
    """Send the question + retrieved chunks to the LLM for a synthesized answer."""
    if not chunks:
        return "No relevant information found in project memory."

    context = "\n\n---\n\n".join(
        f"[Source: {c['source_file']}]\n[Section: {c['heading_path']}]\n\n{c['text']}"
        for c in chunks
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a project memory assistant. Answer the user's question based "
                "solely on the provided context from the project's documentation. "
                "Be concise and specific. Cite which source files your answer draws from. "
                "If the context doesn't contain enough information, say so."
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {question}",
        },
    ]

    endpoint = config.llm.endpoint
    model = config.llm.model
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{endpoint}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
            )
            if resp.status_code == 404:
                raise RuntimeError(
                    f"Model '{model}' not found. Pull it with: ollama pull {model}"
                )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"LLM endpoint returned {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to LLM at {endpoint}. Is your LLM server running? "
            f"Start Ollama with: ollama serve"
        )


def query_memory(
    question: str,
    config: ProjectConfig,
    synthesize_answer: bool = True,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Full query pipeline: retrieve chunks, optionally synthesize.

    Returns a dict with 'answer' (str) and 'sources' (list).
    """
    chunks = retrieve(question, config, top_k=top_k)
    sources = [
        {"source_file": c["source_file"], "heading_path": c["heading_path"]}
        for c in chunks
    ]

    if synthesize_answer and config.llm.enabled and chunks:
        answer = synthesize(question, chunks, config)
    else:
        # Return raw chunk texts
        answer = "\n\n---\n\n".join(
            f"**{c['source_file']}** ({c['heading_path']})\n\n{c['text']}"
            for c in chunks
        ) or "No relevant information found in project memory."

    return {"answer": answer, "sources": sources}
