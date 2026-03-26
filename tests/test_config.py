"""Tests for config loading and validation."""

import json
from pathlib import Path

import pytest

from project_memory.config import (
    ProjectConfig,
    create_default_config,
    find_memory_root,
    load_config,
)


def test_find_memory_root_found(tmp_path):
    """find_memory_root returns the project root when .memory/config.json exists."""
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "config.json").write_text("{}")
    assert find_memory_root(tmp_path) == tmp_path


def test_find_memory_root_walks_up(tmp_path):
    """find_memory_root walks up to parent directories."""
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "config.json").write_text("{}")
    subdir = tmp_path / "a" / "b" / "c"
    subdir.mkdir(parents=True)
    assert find_memory_root(subdir) == tmp_path


def test_find_memory_root_not_found(tmp_path):
    """find_memory_root returns None when no .memory/config.json exists."""
    assert find_memory_root(tmp_path) is None


def test_create_default_config(tmp_path):
    """create_default_config creates a valid config.json."""
    config_path = create_default_config(tmp_path)
    assert config_path.exists()
    data = json.loads(config_path.read_text())
    assert data["project_name"] == tmp_path.name
    assert data["embedding"]["model"] == "nomic-embed-text"
    assert data["indexing"]["split_on_headers"] is True


def test_load_config(tmp_path):
    """load_config returns a valid ProjectConfig."""
    create_default_config(tmp_path)
    config = load_config(tmp_path)
    assert config.project_name == tmp_path.name
    assert config.embedding.model == "nomic-embed-text"
    assert config.project_root == tmp_path
    assert config.memory_dir == tmp_path / ".memory"


def test_load_config_not_found(tmp_path):
    """load_config raises FileNotFoundError when no config exists."""
    with pytest.raises(FileNotFoundError, match="pmem init"):
        load_config(tmp_path)


def test_project_config_from_dict(tmp_path):
    """ProjectConfig.from_dict creates correct config from raw dict."""
    data = {
        "project_name": "test-project",
        "embedding": {"endpoint": "http://localhost:11434", "model": "nomic-embed-text", "provider": "ollama"},
        "query": {"top_k": 5, "auto_reindex_on_query": False},
    }
    config = ProjectConfig.from_dict(data, tmp_path)
    assert config.project_name == "test-project"
    assert config.query.top_k == 5
    assert config.query.auto_reindex_on_query is False
    # Defaults should be used for missing keys
    assert config.llm.enabled is False
