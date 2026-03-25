# Multi-Collection Feature Design

> **Status:** Architecture only — not yet implemented. This is the design document for Phase 2/3.

## Overview

Named collections allow users to define subsets of their project that are indexed and queried independently. For example, a "tasks" collection that only indexes `tasks/**/*.md`, an "architecture" collection for design docs, and the default "all" collection for everything.

---

## 1. Config Schema Changes

The current `config.json` has a flat `indexing` section. The new schema adds a `collections` key alongside it. The top-level `indexing` becomes the default for any collection that doesn't override it.

### New schema (additive — old configs still work)

```json
{
  "project_name": "my-project",
  "embedding": { "..." : "..." },
  "llm": { "..." : "..." },
  "indexing": {
    "include": ["**/*.md", "**/*.txt"],
    "exclude": [".memory/**", ".git/**", "node_modules/**", "*.lock"],
    "chunk_size": 400,
    "chunk_overlap": 80,
    "split_on_headers": true
  },
  "collections": {
    "tasks": {
      "description": "Task logs and work-in-progress notes",
      "include": ["tasks/**/*.md", "TASKS.md"]
    },
    "architecture": {
      "description": "Core design documents",
      "include": ["ARCHITECTURE.md", "SCOPE.md", "ROADMAP.md"]
    }
  },
  "query": {
    "top_k": 8,
    "auto_reindex_on_query": true,
    "default_collection": "all"
  }
}
```

### Collection definition fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `description` | `str` | No | `""` | Human-readable purpose. Surfaced in `memory_status` and tool descriptions. |
| `include` | `list[str]` | No | Inherits from top-level `indexing.include` | Glob patterns for files to include. |
| `exclude` | `list[str]` | No | Inherits from top-level `indexing.exclude` | Glob patterns for files to exclude. |
| `chunk_size` | `int` | No | Inherits | Words per chunk. |
| `chunk_overlap` | `int` | No | Inherits | Word overlap between chunks. |
| `split_on_headers` | `bool` | No | Inherits | Whether to split on markdown headers. |

The name `"all"` is reserved. If the user doesn't define it, one is implicitly created from the top-level `indexing` settings.

---

## 2. store.py Changes

`ChunkStore` becomes collection-aware. All ChromaDB collections are prefixed with `pmem_` to avoid conflicts.

```python
COLLECTION_PREFIX = "pmem_"

class ChunkStore:
    def _get_collection(self, name: str) -> chromadb.Collection:
        """Get or create a ChromaDB collection by name."""
        ...

    def count(self, collection: str = "all") -> int: ...
    def upsert_chunks(self, chunks, embeddings, collection: str = "all"): ...
    def delete_chunks(self, chunk_ids, collection: str = "all"): ...
    def query(self, embedding, top_k=8, collection: str = "all"): ...
    def query_multiple(self, embedding, top_k=8, collections: list[str] | None = None): ...
    def list_collections(self) -> list[str]: ...
    def delete_collection(self, name: str): ...
```

`query_multiple` merges results from several collections by cosine similarity, deduplicates by chunk_id, and returns top_k overall.

---

## 3. indexer.py Changes

- `resolve_collection_config(collection_name, config) -> IndexingConfig` — merges collection settings with top-level defaults
- `scan_files` accepts an `IndexingConfig` parameter
- `IndexState` becomes per-collection: `{collection -> {file -> state}}`
- `run_index` gains `collection: str | None` parameter (None = index all)
- Chunk IDs namespaced: `md5(f"{collection}::{source_file}::{chunk_index}")`

---

## 4. MCP Tool Changes

- `memory_query` and `memory_search` gain `collection` parameter (defaults to `config.query.default_collection`)
- `memory_status` shows per-collection breakdown
- `memory_reindex` gains `collection` parameter
- Tool descriptions dynamically list available collections

---

## 5. CLI Changes

```
pmem index --collection tasks       # Index only "tasks"
pmem query "..." --collection arch  # Scoped query
pmem status --collection tasks      # Status for one collection
pmem collections                    # List all defined collections
pmem collections delete tasks       # Delete a collection's index data
```

---

## 6. Migration Path

**Zero-cost, transparent migration:**

1. **Config**: No `collections` key = behave exactly as before. Implicit `"all"` uses top-level settings.
2. **ChromaDB**: If old `"project_memory"` collection exists and `"pmem_all"` does not, alias it. Only create `"pmem_all"` on next `--force` reindex.
3. **IndexState**: Detect flat format (old) vs nested (new) on load. Wrap flat data under `"all"` automatically.
4. **No breaking changes**: Users who never add `collections` get identical behavior.

---

## 7. Edge Cases

| Case | Resolution |
|------|------------|
| **Overlapping collections** | By design — a file can be in multiple collections. Each gets its own chunk copies with namespaced IDs. |
| **Deleted collection in config** | Orphaned data is harmless. Warn in `pmem status`, clean up via `pmem collections delete`. |
| **Empty collections** | Show `0 files, 0 chunks` rather than hiding. |
| **auto_reindex_on_query** | Only reindex the queried collection, not all. |
| **Collection name validation** | Must be valid ChromaDB name after `pmem_` prefix (1-58 chars, alphanumeric/underscore/hyphen). |
| **Performance with many collections** | Each is a separate HNSW index. Fine for 2-5 collections. 20+ may have cold-start cost. |
| **Embedding dedup (optimization, defer)** | Same file in multiple collections produces identical embeddings. Could cache by `(file_hash, chunk_index)` and reuse. |
