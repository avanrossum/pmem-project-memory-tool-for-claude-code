"""File scanning, chunking, hashing, and embedding orchestration."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pathspec

from project_memory.config import ProjectConfig


@dataclass
class Chunk:
    """A single chunk of text with metadata."""

    chunk_id: str
    text: str
    source_file: str
    heading_path: str
    chunk_index: int
    file_hash: str


@dataclass
class IndexState:
    """Tracks the state of indexed files."""

    files: dict[str, dict[str, Any]] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Save index state to disk."""
        path.write_text(json.dumps(self.files, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> IndexState:
        """Load index state from disk."""
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(files=data)


def scan_files(config: ProjectConfig) -> list[Path]:
    """Scan the project for files matching include/exclude patterns."""
    include_spec = pathspec.PathSpec.from_lines("gitignore", config.indexing.include)
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.indexing.exclude)

    results = []
    for path in config.project_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(config.project_root)
        rel_str = str(rel)
        if include_spec.match_file(rel_str) and not exclude_spec.match_file(rel_str):
            results.append(path)
    return sorted(results)


def hash_file(path: Path) -> str:
    """Return the SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk_markdown(text: str, source_file: str, file_hash: str, config: ProjectConfig) -> list[Chunk]:
    """Split markdown text into chunks, respecting header boundaries.

    If split_on_headers is True, splits at H1/H2/H3 boundaries first,
    then splits oversized sections by chunk_size with overlap.
    """
    chunk_size = config.indexing.chunk_size
    chunk_overlap = config.indexing.chunk_overlap
    split_on_headers = config.indexing.split_on_headers

    if split_on_headers:
        sections = _split_by_headers(text)
    else:
        sections = [("", text)]

    chunks: list[Chunk] = []
    for heading_path, section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue

        if len(section_text) <= chunk_size:
            chunk_id = _make_chunk_id(source_file, len(chunks))
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=section_text,
                source_file=source_file,
                heading_path=heading_path,
                chunk_index=len(chunks),
                file_hash=file_hash,
            ))
        else:
            sub_chunks = _split_by_size(section_text, chunk_size, chunk_overlap)
            for sub_text in sub_chunks:
                chunk_id = _make_chunk_id(source_file, len(chunks))
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=sub_text,
                    source_file=source_file,
                    heading_path=heading_path,
                    chunk_index=len(chunks),
                    file_hash=file_hash,
                ))
    return chunks


def _split_by_headers(text: str) -> list[tuple[str, str]]:
    """Split markdown text at H1/H2/H3 boundaries.

    Returns a list of (heading_path, section_text) tuples.
    """
    header_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(text))

    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    heading_stack: list[tuple[int, str]] = []

    # Text before first heading
    pre_text = text[: matches[0].start()].strip()
    if pre_text:
        sections.append(("", pre_text))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()

        # Update heading stack
        heading_stack = [(l, t) for l, t in heading_stack if l < level]
        heading_stack.append((level, title))
        heading_path = " > ".join(t for _, t in heading_stack)

        # Get section text (from after header to start of next header)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        # Include the header line itself as part of the section
        header_line = match.group(0)
        full_text = header_line + "\n" + section_text if section_text else header_line
        sections.append((heading_path, full_text))

    return sections


def _split_by_size(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks of approximately chunk_size with overlap."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - overlap
    return chunks


def _make_chunk_id(source_file: str, chunk_index: int) -> str:
    """Generate a deterministic chunk ID."""
    raw = f"{source_file}::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def embed_texts(texts: list[str], config: ProjectConfig) -> list[list[float]]:
    """Embed a list of texts using the configured embedding provider."""
    if config.embedding.provider == "ollama":
        return _embed_ollama(texts, config)
    elif config.embedding.provider == "openai_compatible":
        return _embed_openai_compatible(texts, config)
    else:
        raise ValueError(f"Unknown embedding provider: {config.embedding.provider}")


def _embed_ollama(texts: list[str], config: ProjectConfig) -> list[list[float]]:
    """Embed texts using the Ollama API."""
    embeddings: list[list[float]] = []
    with httpx.Client(timeout=120.0) as client:
        for text in texts:
            resp = client.post(
                f"{config.embedding.endpoint}/api/embeddings",
                json={"model": config.embedding.model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings.append(data["embedding"])
    return embeddings


def _embed_openai_compatible(texts: list[str], config: ProjectConfig) -> list[list[float]]:
    """Embed texts using an OpenAI-compatible API."""
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{config.embedding.endpoint}/v1/embeddings",
            json={"model": config.embedding.model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


@dataclass
class IndexResult:
    """Result of an index run."""

    files_indexed: int = 0
    chunks_added: int = 0
    chunks_updated: int = 0
    chunks_removed: int = 0
    duration_seconds: float = 0.0


def run_index(config: ProjectConfig, force: bool = False, dry_run: bool = False) -> IndexResult:
    """Run an incremental (or full) index of the project.

    Returns an IndexResult with stats about what was done.
    """
    from project_memory.store import ChunkStore

    start_time = time.time()
    state_path = config.memory_dir / "index_state.json"
    state = IndexState.load(state_path)
    store = ChunkStore(config)

    files = scan_files(config)
    current_files = {str(f.relative_to(config.project_root)): f for f in files}

    result = IndexResult()

    # Find files to process
    files_to_index: list[tuple[str, Path]] = []
    for rel_str, abs_path in current_files.items():
        fhash = hash_file(abs_path)
        if force or rel_str not in state.files or state.files[rel_str].get("hash") != fhash:
            files_to_index.append((rel_str, abs_path))

    # Find deleted files
    deleted_files = set(state.files.keys()) - set(current_files.keys())

    if dry_run:
        result.files_indexed = len(files_to_index)
        result.chunks_removed = sum(
            len(state.files[f].get("chunk_ids", [])) for f in deleted_files
        )
        result.duration_seconds = time.time() - start_time
        return result

    # Remove chunks for deleted files
    for rel_str in deleted_files:
        chunk_ids = state.files[rel_str].get("chunk_ids", [])
        if chunk_ids:
            store.delete_chunks(chunk_ids)
            result.chunks_removed += len(chunk_ids)
        del state.files[rel_str]

    # Index changed files
    for rel_str, abs_path in files_to_index:
        fhash = hash_file(abs_path)
        text = abs_path.read_text(errors="replace")
        chunks = chunk_markdown(text, rel_str, fhash, config)

        if not chunks:
            continue

        # Remove old chunks for this file
        old_chunk_ids = state.files.get(rel_str, {}).get("chunk_ids", [])
        if old_chunk_ids:
            store.delete_chunks(old_chunk_ids)
            result.chunks_updated += len(old_chunk_ids)

        # Embed and store new chunks
        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts, config)
        store.upsert_chunks(chunks, embeddings)

        result.chunks_added += len(chunks)
        result.files_indexed += 1

        # Update state
        state.files[rel_str] = {
            "hash": fhash,
            "last_indexed": datetime.now(timezone.utc).isoformat(),
            "chunk_ids": [c.chunk_id for c in chunks],
        }

    state.save(state_path)
    result.duration_seconds = time.time() - start_time
    return result


def get_stale_files(config: ProjectConfig) -> list[str]:
    """Return a list of files that have changed since last index."""
    state_path = config.memory_dir / "index_state.json"
    state = IndexState.load(state_path)
    files = scan_files(config)

    stale: list[str] = []
    for path in files:
        rel_str = str(path.relative_to(config.project_root))
        fhash = hash_file(path)
        if rel_str not in state.files or state.files[rel_str].get("hash") != fhash:
            stale.append(rel_str)
    return stale
