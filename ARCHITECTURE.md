# ARCHITECTURE.md — Project Memory Tool

> **Last updated:** 2026-03-25
> Current state: v0.4.0 — Phase 1 complete, most of Phase 2 complete. MCP server stable in production use.

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `pmem init` CLI | ✅ Done | Creates config, auto-appends .gitignore + CLAUDE.md, detects full pmem path |
| `pmem index` CLI | ✅ Done | Incremental, --force, --dry-run, colored progress, early-exit when nothing changed |
| `pmem query` CLI | ✅ Done | Supports --no-llm and --top-k |
| `pmem serve` (MCP server) | ✅ Done | 4 tools, async thread pool, lazy imports, heartbeat logging |
| `pmem status` CLI | ✅ Done | Shows index state, stale files |
| `pmem config` CLI | ✅ Done | Print config, --edit, --global, --init-global |
| `pmem watch` CLI | ✅ Done | watchdog file watcher, 2s debounce |
| `pmem exclude/include` CLI | ✅ Done | Per-project pattern management |
| `pmem install-skills` CLI | ✅ Done | Copies or symlinks skills to ~/.claude/commands/ |
| ChromaDB integration | ✅ Done | Cosine similarity, persistent client, stale lock recovery |
| Embedding client (Ollama) | ✅ Done | Batch /api/embed, OpenAI-compatible fallback |
| LLM synthesis client | ✅ Done | Disabled by default, opt-in for terminal use |
| Markdown chunker | ✅ Done | Header-aware splitting, word + char limits |
| Incremental indexer | ✅ Done | Hash-based, skips ChromaDB when nothing changed |
| Global config | ✅ Done | ~/.config/pmem/config.json, deep-merged with project |
| Skills | ✅ Done | /welcome, /sleep, /reindex — all use MCP tools |
| File watcher | ✅ Done | watchdog-based, 2s debounce |
| Multi-collection | 📐 Designed | See docs/multi-collection-design.md |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/project_memory/cli.py` | Click CLI — all `pmem` subcommands |
| `src/project_memory/config.py` | Config loading, validation, defaults, global config, deep merge |
| `src/project_memory/indexer.py` | File scanning, chunking, hash comparison, embedding orchestration |
| `src/project_memory/store.py` | ChromaDB wrapper — upsert, query, delete, stale lock recovery |
| `src/project_memory/query.py` | Retrieval logic + optional LLM synthesis |
| `src/project_memory/mcp_server.py` | MCP server — async thread pool, lazy imports, file logging |
| `src/project_memory/watcher.py` | watchdog-based file watcher with debounce |
| `skills/welcome.md` | /welcome skill — session start |
| `skills/sleep.md` | /sleep skill — session governance pass |
| `skills/reindex.md` | /reindex skill — quick trigger |

---

## Data Flow

### Index run
```
pmem index
  → config.py: load .memory/config.json (with global config merge)
  → indexer.py: glob files per include/exclude patterns
  → indexer.py: hash each file, compare to index_state.json
  → if nothing changed: return immediately (no ChromaDB)
  → indexer.py: for changed files: chunk by headers → chunk by size
  → embedding client: batch POST to Ollama /api/embed
  → store.py: upsert chunks + metadata to ChromaDB
  → indexer.py: update index_state.json
```

### MCP query
```
Claude Code → MCP tool call: memory_query("what did we decide about X?")
  → mcp_server.py: detect project from CWD (walk up to find .memory/)
  → asyncio.to_thread: run blocking work off event loop
  → embedding client: embed the question
  → store.py: ChromaDB similarity search → top_k chunks
  → return raw chunks + sources (no LLM synthesis by default)
```

---

## MCP Server Architecture

The MCP server (`pmem serve`) runs as a subprocess spawned by Claude Code via stdio.

**Key design decisions:**
- All heavy imports are lazy (per-tool-call, not on startup)
- All blocking operations run in `asyncio.to_thread()` with 30s timeout
- `auto_reindex_on_query` is disabled in MCP context — skills handle freshness
- `memory_status` reads from index_state.json, never opens ChromaDB
- File logging to `~/.pmem-mcp.log` with heartbeat every 60s
- Python warnings suppressed to prevent stderr corruption of MCP protocol
- Registration requires full path to `pmem` binary (pyenv shims don't work)
- Registration goes in `~/.claude.json` or `.mcp.json`, NOT `~/.claude/settings.json`

---

## Dependency Decisions

| Dependency | Version | Reason |
|------------|---------|--------|
| `chromadb` | latest stable | Vector store — file-based, no server required |
| `mcp` | latest stable | Official Anthropic MCP Python SDK |
| `click` | latest stable | CLI framework |
| `httpx` | latest stable | HTTP client for embedding + LLM calls |
| `watchdog` | latest stable | File watching for `pmem watch` |
| `pathspec` | latest stable | Gitignore-style pattern matching for include/exclude |

No LangChain, no LlamaIndex — keep dependencies minimal and the code readable.
