"""Lightweight RAG utilities backed by ChromaDB.

This module builds transient in-memory collections per request from supplementary
reference documents, and retrieves top-k chunks relevant to the current audit.
"""

from __future__ import annotations

import os
from typing import List, Sequence
from uuid import uuid4

from dotenv import load_dotenv


load_dotenv()


def _build_embedding_function():
    """Build embedding function from env; fallback to Chroma default embedding."""

    api_key = (os.getenv("EMBEDDING_API_KEY") or "").strip()
    model = (os.getenv("EMBEDDING_MODEL") or "").strip()
    base_url = (os.getenv("EMBEDDING_BASE_URL") or "").strip()

    # If no third-party config is provided, use Chroma's default local embedding.
    if not api_key or not model:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        return DefaultEmbeddingFunction()

    try:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

        kwargs = {
            "api_key": api_key,
            "model_name": model,
        }
        if base_url:
            kwargs["api_base"] = base_url
        return OpenAIEmbeddingFunction(**kwargs)
    except Exception:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        return DefaultEmbeddingFunction()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    cleaned = (text or "").replace("\r", "\n")
    cleaned = "\n".join([line.strip() for line in cleaned.split("\n") if line.strip()])
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(cleaned):
        chunks.append(cleaned[start : start + chunk_size])
        start += step
    return chunks


def _fallback_reference_context(
    reference_docs: Sequence[dict], max_chars: int = 6000
) -> str:
    parts: List[str] = []
    for doc in reference_docs:
        name = str(doc.get("name") or "reference")
        text = str(doc.get("text") or "").strip()
        if not text:
            continue
        parts.append(f"[参考资料: {name}]\n{text}")
    merged = "\n\n".join(parts).strip()
    return merged[:max_chars] if merged else ""


def retrieve_reference_context(
    reference_docs: Sequence[dict],
    query_text: str,
    *,
    top_k: int = 8,
    max_chars: int = 6000,
) -> str:
    """Retrieve top-k relevant chunks from reference docs using Chroma embeddings.

    Falls back to simple truncation when Chroma or embeddings are unavailable.
    """

    docs_input = [doc for doc in reference_docs if isinstance(doc, dict)]
    if not docs_input:
        return ""

    client = None
    collection_name = ""
    try:
        import chromadb
        from chromadb.config import Settings

        embedding_function = _build_embedding_function()

        try:
            # Prefer ephemeral mode to avoid any on-disk persistence.
            client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False)
            )
        except Exception:
            client = chromadb.Client(
                Settings(anonymized_telemetry=False, is_persistent=False)
            )

        collection_name = f"audit-ref-{uuid4().hex}"
        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

        ids: List[str] = []
        docs: List[str] = []
        metas: List[dict] = []
        idx = 0

        for doc in docs_input:
            name = str(doc.get("name") or "reference")
            text = str(doc.get("text") or "").strip()
            for chunk in _chunk_text(text):
                ids.append(f"c{idx}")
                docs.append(chunk)
                metas.append({"source": name})
                idx += 1

        if not docs:
            return ""

        collection.add(ids=ids, documents=docs, metadatas=metas)

        query = (query_text or "").strip() or "审校人名 身份 组织 时间 事实一致性"
        result = collection.query(
            query_texts=[query], n_results=max(1, min(top_k, len(docs)))
        )

        ret_docs = (result.get("documents") or [[]])[0]
        ret_meta = (result.get("metadatas") or [[]])[0]
        if not ret_docs:
            return ""

        parts: List[str] = []
        total = 0
        for i, chunk in enumerate(ret_docs):
            source = "reference"
            if i < len(ret_meta) and isinstance(ret_meta[i], dict):
                source = str(ret_meta[i].get("source") or source)
            block = f"[参考资料片段: {source}]\n{chunk.strip()}"
            if not chunk.strip():
                continue
            total += len(block)
            if total > max_chars:
                break
            parts.append(block)

        merged = "\n\n".join(parts).strip()
        return merged[:max_chars] if merged else ""
    except Exception:
        return _fallback_reference_context(docs_input, max_chars=max_chars)
    finally:
        if client and collection_name:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass
