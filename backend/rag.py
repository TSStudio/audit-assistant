"""RAG utilities backed by persistent ChromaDB collections."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Sequence
from uuid import uuid4

from dotenv import load_dotenv


load_dotenv()

CHROMA_DIR = Path(__file__).resolve().parent / "chroma_store"


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


def _get_persistent_client():
    import chromadb
    from chromadb.config import Settings

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        return chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    except Exception:
        return chromadb.Client(
            Settings(
                anonymized_telemetry=False,
                is_persistent=True,
                persist_directory=str(CHROMA_DIR),
            )
        )


def make_reference_collection_name(reference_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", str(reference_id or "")).lower()
    if not cleaned:
        cleaned = uuid4().hex
    return f"audit_ref_{cleaned[:48]}"


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


def index_reference_document(collection_name: str, doc_name: str, text: str) -> None:
    """Persist a single reference document into a dedicated Chroma collection."""

    body = str(text or "").strip()
    if not body:
        return

    chunks = _chunk_text(body)
    if not chunks:
        return

    import chromadb

    client = _get_persistent_client()
    embedding_function = _build_embedding_function()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine", "doc_name": doc_name},
    )

    try:
        # Keep replacement semantics by clearing old chunks before re-index.
        collection.delete(where={"doc_name": doc_name})
    except Exception:
        pass

    ids: List[str] = []
    docs: List[str] = []
    metas: List[dict] = []
    for idx, chunk in enumerate(chunks):
        ids.append(f"{collection_name}-{idx}")
        docs.append(chunk)
        metas.append({"source": doc_name, "doc_name": doc_name})

    collection.add(ids=ids, documents=docs, metadatas=metas)


def delete_reference_collection(collection_name: str) -> None:
    try:
        client = _get_persistent_client()
        client.delete_collection(collection_name)
    except Exception:
        pass


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


def _retrieve_from_persistent_collections(
    selected_references: Sequence[dict],
    query_text: str,
    *,
    top_k: int,
    max_chars: int,
) -> str:
    valid_refs = [r for r in selected_references if r.get("collection_name")]
    if not valid_refs:
        return ""

    client = _get_persistent_client()
    embedding_function = _build_embedding_function()
    query = (query_text or "").strip() or "审校人名 身份 组织 时间 事实一致性"

    scored_chunks: List[tuple[float, str, str]] = []
    each_k = max(1, min(4, top_k))

    for ref in valid_refs:
        cname = str(ref.get("collection_name") or "").strip()
        if not cname:
            continue
        try:
            col = client.get_collection(
                name=cname, embedding_function=embedding_function
            )
            result = col.query(query_texts=[query], n_results=each_k)
        except Exception:
            continue

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for idx, chunk in enumerate(docs):
            if not str(chunk or "").strip():
                continue
            source = str(ref.get("name") or "reference")
            if idx < len(metas) and isinstance(metas[idx], dict):
                source = str(metas[idx].get("source") or source)
            dist = float(dists[idx]) if idx < len(dists) else 999.0
            scored_chunks.append((dist, source, str(chunk).strip()))

    if not scored_chunks:
        return ""

    scored_chunks.sort(key=lambda x: x[0])
    parts: List[str] = []
    total = 0
    for _, source, chunk in scored_chunks[: max(1, top_k * 2)]:
        block = f"[参考资料片段: {source}]\n{chunk}"
        total += len(block)
        if total > max_chars:
            break
        parts.append(block)
    merged = "\n\n".join(parts).strip()
    return merged[:max_chars] if merged else ""


def retrieve_reference_context(
    reference_docs: Sequence[dict],
    query_text: str,
    *,
    top_k: int = 8,
    max_chars: int = 6000,
) -> str:
    """Retrieve top-k relevant chunks from reference docs using Chroma.

    If entries include collection_name, query persisted on-disk collections first.
    Otherwise, fallback to transient querying with inline text.
    """

    docs_input = [doc for doc in reference_docs if isinstance(doc, dict)]
    if not docs_input:
        return ""

    persisted = [d for d in docs_input if d.get("collection_name")]
    if persisted:
        try:
            merged = _retrieve_from_persistent_collections(
                persisted,
                query_text,
                top_k=top_k,
                max_chars=max_chars,
            )
            if merged:
                return merged
        except Exception:
            pass

    client = None
    collection_name = ""
    try:
        import chromadb
        from chromadb.config import Settings

        embedding_function = _build_embedding_function()

        try:
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
