# CHANGELOG.md

---

## [Unreleased]

## [0.3.0] — 2026-03-25

### Added
- `pmem watch` — background file watcher with 2-second debounce, auto-reindexes on file changes
- `pmem exclude` / `pmem include` — CLI commands for easy per-project pattern management
- `pmem config --global` / `--init-global` — global default config at `~/.config/pmem/config.json`
- Global config deep-merges with project config (global base, project overrides)
- `pmem init` now auto-appends to `.gitignore` and appends Project Memory snippet to `CLAUDE.md`
- Actionable error messages: "Ollama not running", "model not found", connection failures
- `/welcome` skill — session start: reads governance files, incremental reindex
- `/sleep` skill — session end: governance pass + reindex (included in repo)
- Multi-collection architecture design doc (`docs/multi-collection-design.md`)

### Fixed
- Infinite loop in `_split_by_size` when char limit forced overlap past start position
- Chunk size now enforced by both word count AND character limit (prevents embedding context overflow)
- Batch embed via Ollama `/api/embed` instead of one-at-a-time `/api/embeddings`
- Batch chunk deletion before re-indexing (single ChromaDB call instead of per-file)

### Changed
- Structured progress logging with colored output for all CLI commands
- `run_index` accepts `log` callback for stage-by-stage progress reporting

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
