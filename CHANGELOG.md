# CHANGELOG.md

---

## [Unreleased]

## [0.2.0] — 2026-03-25

### Added
- `pyproject.toml` with all Phase 1 dependencies (chromadb, mcp, click, httpx, pathspec)
- `src/project_memory/config.py` — config loading, CWD walk-up, validation, defaults
- `src/project_memory/indexer.py` — file scanning, header-aware markdown chunking, SHA-256 hashing, incremental indexing, Ollama + OpenAI-compatible embedding
- `src/project_memory/store.py` — ChromaDB persistent client, cosine similarity search, upsert/delete
- `src/project_memory/query.py` — retrieval pipeline, optional LLM synthesis via OpenAI-compatible endpoint
- `src/project_memory/mcp_server.py` — MCP server with 4 tools: memory_query, memory_search, memory_status, memory_reindex
- `src/project_memory/cli.py` — `pmem` CLI with init, index, query, status, serve, config commands
- 19 tests covering config, indexer (chunking, hashing, scanning), and store (upsert, query, delete)

## [0.1.0] — 2026-03-25

### Added
- Project scaffolding: `CLAUDE.md`, `SCOPE.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `CHANGELOG.md`, `LESSONS_LEARNED.md`
- `docs/` directory created for integration and configuration guides
- Full system architecture scoped in `SCOPE.md`
- Phase 1/2/3 roadmap defined
