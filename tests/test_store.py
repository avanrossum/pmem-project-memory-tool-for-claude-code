"""Tests for the ChromaDB store."""

import pytest

from project_memory.config import create_default_config, load_config
from project_memory.indexer import Chunk
from project_memory.store import ChunkStore


@pytest.fixture
def store(tmp_path):
    """Create a ChunkStore with a temporary config."""
    create_default_config(tmp_path)
    config = load_config(tmp_path)
    return ChunkStore(config)


def _make_chunk(chunk_id: str, text: str = "test text") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_file="test.md",
        heading_path="Test",
        chunk_index=0,
        file_hash="abc",
    )


def test_upsert_and_count(store):
    """Upserting chunks increases the count."""
    assert store.count == 0
    chunks = [_make_chunk("c1", "hello world"), _make_chunk("c2", "goodbye world")]
    # Use a simple embedding (chromadb accepts raw floats)
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    store.upsert_chunks(chunks, embeddings)
    assert store.count == 2


def test_query(store):
    """Querying returns results sorted by relevance."""
    chunks = [
        _make_chunk("c1", "python programming language"),
        _make_chunk("c2", "javascript framework"),
    ]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    store.upsert_chunks(chunks, embeddings)

    results = store.query([1.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0]["text"] == "python programming language"


def test_delete_chunks(store):
    """Deleting chunks reduces the count."""
    chunks = [_make_chunk("c1"), _make_chunk("c2")]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    store.upsert_chunks(chunks, embeddings)
    assert store.count == 2

    store.delete_chunks(["c1"])
    assert store.count == 1


def test_query_empty_store(store):
    """Querying an empty store returns no results."""
    results = store.query([1.0, 0.0], top_k=5)
    assert results == []
