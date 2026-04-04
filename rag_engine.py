"""
RAG engine for the ollama Search Tool.

Pipeline: chunk → embed (nomic-embed-text via Ollama) → store (ChromaDB in-memory)
          → retrieve (cosine similarity) → rerank (CrossEncoder)

Key design decisions:
- EphemeralClient: fully in-memory, no SQLite/persistence issues
- Manual metadata filtering for remove(): where-clause API is unreliable in ChromaDB 1.x
- clear() recreates the client — collection.delete() alone does not release RAM reliably
- CrossEncoder is loaded lazily but pre-warmed in a background thread at startup
- ollama.embed() batches multiple texts in one HTTP call (ollama >= 0.5)
"""

import logging
import threading
import uuid
from typing import List, Dict

import chromadb
import ollama

from config import (
    OLLAMA_HOST,
    EMBED_MODEL, RERANK_MODEL,
    RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP,
    RAG_RETRIEVE_K, RAG_RERANK_TOP_K,
    RAG_SCORE_THRESHOLD, RAG_MAX_CHUNKS,
)

logger = logging.getLogger(__name__)


class RagEngine:
    """In-memory RAG index for a single chat session."""

    def __init__(self):
        self._ollama = ollama.Client(host=OLLAMA_HOST)
        self._reranker = None
        self._reranker_lock = threading.Lock()
        self._init_db()
        # Pre-warm the reranker in the background so the first query isn't slow
        threading.Thread(target=self._load_reranker, daemon=True).start()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self._client = chromadb.EphemeralClient()
        # Unique name per instance: ChromaDB 1.x uses a shared Rust backend per
        # process, so two EphemeralClient instances would collide on the same name.
        self._col_name = f"docs_{uuid.uuid4().hex[:8]}"
        self._collection = self._client.create_collection(
            name=self._col_name,
            metadata={"hnsw:space": "cosine"},
        )

    def clear(self) -> None:
        """Drop and recreate the in-memory store, releasing all RAM."""
        del self._collection
        del self._client
        self._init_db()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def chunk_count(self) -> int:
        return self._collection.count()

    def list_documents(self) -> List[str]:
        """Return sorted list of indexed document names."""
        if self.chunk_count == 0:
            return []
        result = self._collection.get(include=["metadatas"])
        return sorted({m["source"] for m in result["metadatas"]})

    def index(self, name: str, text: str) -> int:
        """
        Chunk, embed, and store a document.
        If a document with the same name already exists it is replaced.
        Returns the number of chunks stored.
        """
        self.remove(name)  # idempotent replace

        chunks = self._chunk(text)
        if not chunks:
            return 0

        BATCH = 64  # nomic-embed-text handles large batches efficiently
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            texts = [c["text"] for c in batch]
            embeddings = self._embed(texts)
            self._collection.add(
                ids=[f"{name}__c{i + j}" for j in range(len(batch))],
                documents=texts,
                embeddings=embeddings,
                metadatas=[{"source": name, "chunk_index": c["idx"]} for c in batch],
            )
            logger.debug(f"Indexed batch {i // BATCH + 1} for '{name}' ({len(batch)} chunks)")

        total = len(chunks)
        logger.info(f"Indexed '{name}': {total} chunks, collection total: {self.chunk_count}")
        return total

    def query(self, question: str) -> List[Dict]:
        """
        Retrieve and rerank chunks relevant to the question.
        Returns list of {"text", "source", "score"} sorted by descending score.
        Chunks with CrossEncoder score <= RAG_SCORE_THRESHOLD are dropped.
        """
        if self.chunk_count == 0:
            return []

        k = min(RAG_RETRIEVE_K, self.chunk_count)
        q_emb = self._embed([question])[0]

        results = self._collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents", "metadatas"],
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if not docs:
            return []

        reranker = self._get_reranker()
        scores = reranker.predict([[question, d] for d in docs])

        ranked = sorted(zip(docs, metas, scores), key=lambda x: x[2], reverse=True)

        return [
            {"text": doc, "source": meta["source"], "score": float(score)}
            for doc, meta, score in ranked[:RAG_RERANK_TOP_K]
            if score > RAG_SCORE_THRESHOLD
        ]

    def remove(self, name: str) -> None:
        """Remove all chunks for a given document."""
        if self.chunk_count == 0:
            return
        try:
            result = self._collection.get(include=["metadatas"])
            ids = [id_ for id_, m in zip(result["ids"], result["metadatas"]) if m["source"] == name]
            if ids:
                self._collection.delete(ids=ids)
                logger.info(f"Removed '{name}' ({len(ids)} chunks)")
        except Exception as e:
            logger.warning(f"remove('{name}'): {e}")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _chunk(self, text: str) -> List[Dict]:
        """Split text into overlapping word-count-based chunks."""
        words = text.split()
        chunks, start, idx = [], 0, 0
        while start < len(words):
            end = min(start + RAG_CHUNK_SIZE, len(words))
            chunks.append({"text": " ".join(words[start:end]), "idx": idx})
            if end == len(words):
                break
            start += RAG_CHUNK_SIZE - RAG_CHUNK_OVERLAP
            idx += 1
        return chunks

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Batch-embed texts using Ollama (nomic-embed-text)."""
        response = self._ollama.embed(model=EMBED_MODEL, input=texts)
        return response.embeddings

    def _load_reranker(self):
        """Load the CrossEncoder model (thread-safe, called once)."""
        with self._reranker_lock:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading reranker: {RERANK_MODEL}")
                self._reranker = CrossEncoder(RERANK_MODEL)
                logger.info("Reranker ready")

    def _get_reranker(self):
        if self._reranker is None:
            self._load_reranker()
        return self._reranker
