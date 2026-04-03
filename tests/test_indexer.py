"""Tests for the indexer: chunking, hashing, file scanning."""

from pathlib import Path

import pytest

from project_memory.config import ProjectConfig, create_default_config, load_config
from project_memory.indexer import (
    Chunk,
    _merge_small_sections,
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


def test_merge_small_sections_forward():
    """Small sections merge forward into the next section."""
    sections = [
        ("Heading A", "tiny"),
        ("Heading B", " ".join(f"word{i}" for i in range(60))),
    ]
    merged = _merge_small_sections(sections, min_words=50)
    assert len(merged) == 1
    assert "tiny" in merged[0][1]
    assert "word0" in merged[0][1]


def test_merge_small_sections_backward():
    """Last undersized section merges backward."""
    sections = [
        ("Heading A", " ".join(f"word{i}" for i in range(60))),
        ("Heading B", "tiny tail"),
    ]
    merged = _merge_small_sections(sections, min_words=50)
    assert len(merged) == 1
    assert "word0" in merged[0][1]
    assert "tiny tail" in merged[0][1]


def test_merge_small_sections_chain():
    """Multiple consecutive small sections merge into the next large one."""
    sections = [
        ("H1", "one"),
        ("H2", "two"),
        ("H3", " ".join(f"word{i}" for i in range(60))),
    ]
    merged = _merge_small_sections(sections, min_words=50)
    assert len(merged) == 1
    assert "one" in merged[0][1]
    assert "two" in merged[0][1]
    assert "word0" in merged[0][1]


def test_merge_small_sections_all_small():
    """When every section is undersized, they merge into a single chunk."""
    sections = [
        ("H1", "alpha"),
        ("H2", "beta"),
        ("H3", "gamma"),
    ]
    merged = _merge_small_sections(sections, min_words=50)
    assert len(merged) == 1
    assert "alpha" in merged[0][1]
    assert "gamma" in merged[0][1]


def test_merge_small_sections_preserves_large():
    """Sections above the threshold are left alone."""
    big = " ".join(f"word{i}" for i in range(60))
    sections = [
        ("H1", big),
        ("H2", big),
    ]
    merged = _merge_small_sections(sections, min_words=50)
    assert len(merged) == 2


def test_chunk_markdown_min_chunk_size(tmp_path):
    """chunk_markdown merges tiny header sections instead of emitting them."""
    create_default_config(tmp_path)
    config = load_config(tmp_path)

    # Simulate a changelog with tiny sections
    text = "# Changelog\n\n## Added\n\n- CTA\n\n## Changed\n\n- Updated button style with new colors and hover states for the primary action component\n\n## Fixed\n\n- Resolved alignment issue in the navigation bar that caused items to shift on mobile viewport sizes when scrolling"
    chunks = chunk_markdown(text, "CHANGELOG.md", "abc123", config)
    # "CTA" alone (1 word) should NOT be its own chunk
    for c in chunks:
        assert c.text.strip() != "## Added\n\n- CTA", f"Tiny section should have been merged, got: {c.text!r}"


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
