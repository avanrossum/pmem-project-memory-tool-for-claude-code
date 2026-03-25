"""ChromaDB vector store interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from project_memory.config import ProjectConfig
from project_memory.indexer import Chunk


COLLECTION_NAME = "project_memory"


def _cleanup_stale_locks(chroma_dir: Path) -> None:
    """Remove stale SQLite WAL/SHM lock files left by crashed processes.

    These files prevent ChromaDB from opening after an interrupted index run.
    Safe to remove when no other process is using the database.
    """
    for pattern in ("*.wal", "*.shm"):
        for lock_file in chroma_dir.rglob(pattern):
            try:
                lock_file.unlink()
            except OSError:
                pass


class ChunkStore:
    """Wrapper around ChromaDB for storing and querying embedded chunks."""

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the ChromaDB client and collection."""
        chroma_dir = config.memory_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(path=str(chroma_dir))
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            # If ChromaDB fails to open (likely stale locks), clean up and retry once
            _cleanup_stale_locks(chroma_dir)
            self._client = chromadb.PersistentClient(path=str(chroma_dir))
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

    @property
    def count(self) -> int:
        """Return the total number of chunks in the collection."""
        return self._collection.count()

    def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks with their embeddings into the store."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "source_file": c.source_file,
                    "heading_path": c.heading_path,
                    "chunk_index": c.chunk_index,
                    "file_hash": c.file_hash,
                }
                for c in chunks
            ],
        )

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete chunks by their IDs."""
        if not chunk_ids:
            return
        self._collection.delete(ids=chunk_ids)

    def query(self, embedding: list[float], top_k: int = 8) -> list[dict[str, Any]]:
        """Query the store for the most similar chunks.

        Returns a list of dicts with keys: text, source_file, heading_path, relevance_score.
        """
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self.count) if self.count > 0 else 1,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        chunks = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text": doc,
                "source_file": meta["source_file"],
                "heading_path": meta.get("heading_path", ""),
                "relevance_score": round(1 - distance, 4),  # cosine distance → similarity
            })
        return chunks
