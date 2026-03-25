"""Configuration loading and validation for project memory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "",
    "embedding": {
        "endpoint": "http://localhost:11434",
        "model": "nomic-embed-text",
        "provider": "ollama",
    },
    "llm": {
        "endpoint": "http://localhost:1234/v1",
        "model": "local-model",
        "provider": "openai_compatible",
        "enabled": True,
    },
    "indexing": {
        "include": ["**/*.md", "**/*.txt"],
        "exclude": [".memory/**", ".git/**", "node_modules/**", "*.lock"],
        "chunk_size": 400,
        "chunk_overlap": 80,
        "split_on_headers": True,
    },
    "query": {
        "top_k": 8,
        "auto_reindex_on_query": True,
    },
}


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""

    endpoint: str = "http://localhost:11434"
    model: str = "nomic-embed-text"
    provider: str = "ollama"


@dataclass
class LLMConfig:
    """LLM synthesis configuration."""

    endpoint: str = "http://localhost:1234/v1"
    model: str = "local-model"
    provider: str = "openai_compatible"
    enabled: bool = True


@dataclass
class IndexingConfig:
    """Indexing configuration."""

    include: list[str] = field(default_factory=lambda: ["**/*.md", "**/*.txt"])
    exclude: list[str] = field(
        default_factory=lambda: [".memory/**", ".git/**", "node_modules/**", "*.lock"]
    )
    chunk_size: int = 400
    chunk_overlap: int = 80
    split_on_headers: bool = True


@dataclass
class QueryConfig:
    """Query configuration."""

    top_k: int = 8
    auto_reindex_on_query: bool = True


@dataclass
class ProjectConfig:
    """Full project configuration."""

    project_name: str = ""
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    query: QueryConfig = field(default_factory=QueryConfig)
    project_root: Path = field(default_factory=Path)
    memory_dir: Path = field(default_factory=Path)

    @classmethod
    def from_dict(cls, data: dict[str, Any], project_root: Path) -> ProjectConfig:
        """Create a ProjectConfig from a dictionary and project root path."""
        memory_dir = project_root / ".memory"
        return cls(
            project_name=data.get("project_name", project_root.name),
            embedding=EmbeddingConfig(**data.get("embedding", {})),
            llm=LLMConfig(**data.get("llm", {})),
            indexing=IndexingConfig(**data.get("indexing", {})),
            query=QueryConfig(**data.get("query", {})),
            project_root=project_root,
            memory_dir=memory_dir,
        )


def find_memory_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default CWD) to find a directory containing .memory/config.json."""
    current = (start or Path.cwd()).resolve()
    while True:
        config_path = current / ".memory" / "config.json"
        if config_path.is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(start: Path | None = None) -> ProjectConfig:
    """Load project config by walking up from start to find .memory/config.json.

    Raises FileNotFoundError if no .memory/config.json is found.
    """
    project_root = find_memory_root(start)
    if project_root is None:
        raise FileNotFoundError(
            "No .memory/config.json found. Run 'pmem init' in your project root."
        )
    config_path = project_root / ".memory" / "config.json"
    data = json.loads(config_path.read_text())
    return ProjectConfig.from_dict(data, project_root)


def create_default_config(project_root: Path) -> Path:
    """Create a default .memory/config.json in the given project root.

    Returns the path to the created config file.
    """
    memory_dir = project_root / ".memory"
    memory_dir.mkdir(exist_ok=True)
    config_path = memory_dir / "config.json"
    config = dict(DEFAULT_CONFIG)
    config["project_name"] = project_root.name
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return config_path
