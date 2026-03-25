"""Configuration loading and validation for project memory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GLOBAL_CONFIG_DIR = Path.home() / ".config" / "pmem"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.json"

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
        "enabled": False,
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
        "auto_reindex_on_query": False,
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
    auto_reindex_on_query: bool = False


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


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dicts. Values in override take precedence.

    For nested dicts, merging is recursive. For all other types (including lists),
    the override value replaces the base value entirely.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_global_config() -> dict[str, Any]:
    """Load the global config from ~/.config/pmem/config.json.

    Returns an empty dict if the file does not exist or is invalid.
    """
    if not GLOBAL_CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(GLOBAL_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def create_global_config() -> Path:
    """Create a minimal global config with embedding and LLM sections.

    Returns the path to the created config file.
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any] = {
        "embedding": dict(DEFAULT_CONFIG["embedding"]),
        "llm": dict(DEFAULT_CONFIG["llm"]),
    }
    GLOBAL_CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    return GLOBAL_CONFIG_PATH


def load_config(start: Path | None = None) -> ProjectConfig:
    """Load project config by walking up from start to find .memory/config.json.

    If a global config exists at ~/.config/pmem/config.json, it is loaded first
    as a base, then the project config is deep-merged on top (project wins).

    Raises FileNotFoundError if no .memory/config.json is found.
    """
    project_root = find_memory_root(start)
    if project_root is None:
        raise FileNotFoundError(
            "No .memory/config.json found. Run 'pmem init' in your project root."
        )
    config_path = project_root / ".memory" / "config.json"
    project_data = json.loads(config_path.read_text())

    global_data = load_global_config()
    if global_data:
        data = deep_merge(global_data, project_data)
    else:
        data = project_data

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
