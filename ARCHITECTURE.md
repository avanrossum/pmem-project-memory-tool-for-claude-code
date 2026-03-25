# ARCHITECTURE.md — Project Memory Tool

> **Last updated:** 2026-03-25
> Current state: Phase 1 complete. All core components implemented and tested.

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `pmem init` CLI | ✅ Done | Creates .memory/config.json with defaults |
| `pmem index` CLI | ✅ Done | Incremental, --force, --dry-run |
| `pmem query` CLI | ✅ Done | Supports --no-llm and --top-k |
| `pmem serve` (MCP server) | ✅ Done | 4 tools: memory_query, memory_search, memory_status, memory_reindex |
| `pmem status` CLI | ✅ Done | Shows index state, stale files |
| `pmem config` CLI | ✅ Done | Print config or open in $EDITOR |
| ChromaDB integration | ✅ Done | Cosine similarity, persistent client |
| Embedding client (Ollama) | ✅ Done | Also supports openai_compatible provider |
| LLM synthesis client | ✅ Done | OpenAI-compatible endpoint |
| Markdown chunker | ✅ Done | Header-aware splitting with size fallback |
| Incremental indexer | ✅ Done | Hash-based change detection, deleted file cleanup |
| File watcher | ⬜ Not started | Phase 2 |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/project_memory/cli.py` | Click CLI entry point — all `pmem` subcommands |
| `src/project_memory/config.py` | Config loading, validation, defaults |
| `src/project_memory/indexer.py` | File scanning, chunking, hash comparison, embedding orchestration |
| `src/project_memory/store.py` | ChromaDB wrapper — upsert, query, delete |
| `src/project_memory/query.py` | Retrieval logic + LLM synthesis |
| `src/project_memory/mcp_server.py` | MCP server with 4 tools |
| `src/project_memory/watcher.py` | watchdog-based file watcher (Phase 2) |

---

## Data Flow

### Index run
```
pmem index
  → config.py: load .memory/config.json
  → indexer.py: glob files per include/exclude patterns
  → indexer.py: hash each file, compare to index_state.json
  → indexer.py: for changed files: chunk by headers → chunk by size
  → embedding client: POST chunks to embedding endpoint
  → store.py: upsert chunks + metadata to ChromaDB
  → indexer.py: update index_state.json
```

### MCP query
```
Claude Code → MCP tool call: memory_query("what did we decide about X?")
  → mcp_server.py: detect project from CWD (walk up to find .memory/)
  → config.py: load project config
  → indexer.py: incremental index check (if auto_reindex_on_query)
  → embedding client: embed the question
  → store.py: ChromaDB similarity search → top_k chunks
  → query.py: format chunks as context
  → LLM client: POST to synthesis endpoint (if synthesize=true)
  → return: {answer, sources}
```

---

## Dependency Decisions

| Dependency | Version | Reason |
|------------|---------|--------|
| `chromadb` | latest stable | Vector store — file-based, no server required |
| `mcp` | latest stable | Official Anthropic MCP Python SDK |
| `click` | latest stable | CLI framework |
| `httpx` | latest stable | Async HTTP client for embedding + LLM calls |
| `watchdog` | latest stable | File watching (Phase 2 only) |
| `pathspec` | latest stable | Gitignore-style pattern matching for include/exclude |

No LangChain, no LlamaIndex — keep dependencies minimal and the code readable.
