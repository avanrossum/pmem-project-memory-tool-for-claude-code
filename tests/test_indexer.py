"""Tests for the indexer: chunking, hashing, file scanning."""

from pathlib import Path

import pytest

from project_memory.config import ProjectConfig, create_default_config, load_config
from project_memory.indexer import (
    Chunk,
    _split_by_headers,
    _split_by_size,
    chunk_markdown,
    hash_file,
    scan_files,
)


def test_hash_file(tmp_path):
    """hash_file returns consistent hashes."""
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    h1 = hash_file(f)
    h2 = hash_file(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_hash_file_changes(tmp_path):
    """hash_file detects content changes."""
    f = tmp_path / "test.txt"
    f.write_text("hello")
    h1 = hash_file(f)
    f.write_text("world")
    h2 = hash_file(f)
    assert h1 != h2


def test_split_by_headers_basic():
    """_split_by_headers splits on H1/H2/H3."""
    text = "# Title\nSome text\n\n## Section\nMore text\n\n### Sub\nDeep text"
    sections = _split_by_headers(text)
    assert len(sections) == 3
    assert sections[0][0] == "Title"
    assert sections[1][0] == "Title > Section"
    assert sections[2][0] == "Title > Section > Sub"


def test_split_by_headers_no_headers():
    """_split_by_headers returns full text when no headers exist."""
    text = "Just some plain text\nwith multiple lines."
    sections = _split_by_headers(text)
    assert len(sections) == 1
    assert sections[0][0] == ""
    assert "plain text" in sections[0][1]


def test_split_by_headers_preamble():
    """_split_by_headers captures text before the first heading."""
    text = "Preamble text\n\n# Heading\nBody"
    sections = _split_by_headers(text)
    assert len(sections) == 2
    assert sections[0][0] == ""
    assert "Preamble" in sections[0][1]


def test_split_by_size():
    """_split_by_size splits into chunks with overlap and respects char limit."""
    text = " ".join(f"w{i}" for i in range(100))
    chunks = _split_by_size(text, chunk_size=30, overlap=5)
    assert len(chunks) > 1
    # Each chunk should not exceed chunk_size * 5 characters
    max_chars = 30 * 5
    for c in chunks:
        assert len(c) <= max_chars


def test_chunk_markdown(tmp_path):
    """chunk_markdown produces chunks with correct metadata."""
    create_default_config(tmp_path)
    config = load_config(tmp_path)

    text = "# Heading\nShort section."
    chunks = chunk_markdown(text, "test.md", "abc123", config)
    assert len(chunks) >= 1
    assert chunks[0].source_file == "test.md"
    assert chunks[0].heading_path == "Heading"
    assert chunks[0].file_hash == "abc123"


def test_scan_files(tmp_path):
    """scan_files finds files matching include patterns and excludes others."""
    create_default_config(tmp_path)
    config = load_config(tmp_path)

    # Create matching files
    (tmp_path / "readme.md").write_text("# Readme")
    (tmp_path / "notes.txt").write_text("Notes")
    # Create non-matching file
    (tmp_path / "code.py").write_text("print('hi')")
    # Create excluded file
    mem_dir = tmp_path / ".memory"
    (mem_dir / "internal.md").write_text("# Internal")

    files = scan_files(config)
    rel_names = [str(f.relative_to(tmp_path)) for f in files]

    assert "readme.md" in rel_names
    assert "notes.txt" in rel_names
    assert "code.py" not in rel_names
    assert ".memory/internal.md" not in rel_names
