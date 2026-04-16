"""ChromaDB vector store interface."""

from __future__ import annotations

import fcntl
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import chromadb

from project_memory.config import ProjectConfig
from project_memory.indexer import Chunk


COLLECTION_NAME = "project_memory"
logger = logging.getLogger(__name__)


def _wipe_chroma_dir(chroma_dir: Path) -> None:
    """Remove and recreate a corrupted ChromaDB directory."""
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.info("Removed corrupted ChromaDB directory: %s", chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)


class ChunkStore:
    """Wrapper around ChromaDB for storing and querying embedded chunks."""

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the ChromaDB client and collection.

        Acquires an exclusive file lock to prevent concurrent access to the
        ChromaDB database. If the database is corrupted (e.g. from a previous
        interrupted write or version mismatch), it is automatically wiped and
        a full reindex will be triggered.
        """
        chroma_dir = config.memory_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        # Acquire exclusive lock to prevent concurrent ChromaDB access
        self._lock_path = config.memory_dir / "chroma.lock"
        self._lock_fd = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR)
        fcntl.flock(self._lock_fd, fcntl.LOCK_EX)

        try:
            self._open_chroma(chroma_dir)
        except Exception as first_exc:
            logger.warning(
                "ChromaDB open failed (%s: %s), wiping corrupt database and rebuilding",
                type(first_exc).__name__,
                first_exc,
            )
            # ChromaDB caches a singleton System keyed by persist path.
            # If the first open fails mid-initialization, the broken system
            # stays in the cache and all subsequent PersistentClient() calls
            # for this path silently reuse it.  We must clear it before retry.
            from chromadb.api.shared_system_client import SharedSystemClient
            SharedSystemClient.clear_system_cache()

            _wipe_chroma_dir(chroma_dir)
            try:
                self._open_chroma(chroma_dir)
            except Exception:
                self._release_lock()
                raise

    def _open_chroma(self, chroma_dir: Path) -> None:
        """Open the ChromaDB client and collection."""
        self._client = chromadb.PersistentClient(path=str(chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _release_lock(self) -> None:
        """Release the file lock on the ChromaDB directory."""
        if hasattr(self, "_lock_fd") and self._lock_fd >= 0:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = -1

    def close(self) -> None:
        """Release resources and the file lock."""
        self._release_lock()

    def __del__(self) -> None:
        self._release_lock()

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
