# CHANGELOG.md

---

## [0.5.0] — 2026-03-25

### Added
- Server heartbeat logging (every 60s) for diagnosing idle server exits
- `SERVER_STDIO_OPEN`, `SERVER_RUN_EXITED`, `SERVER_CANCELLED` lifecycle events in log
- Full traceback logging on server crash
- 18 watcher tests covering polling, lifecycle, error handling

### Fixed
- **Watcher pattern matching bug** — `_matches_patterns` used `fnmatch` which doesn't understand `**` globs. Root-level files and many nested paths were silently ignored. Switched to `pathspec` (gitignore-style) to match the indexer's behavior.
- `auto_reindex_on_query` now defaults to `false` — was causing unnecessary file hashing overhead
- No-op reindex skips ChromaDB entirely when nothing changed (~250ms vs ~3.6s)
- `/sleep` runs reindex as Step 2 (early) instead of Step 6 — MCP server may be unavailable late in flow
- README: corrected `auto_reindex_on_query` default from `true` to `false`

### Changed
- **`pmem watch` rewritten as polling-based** — replaced watchdog/FSEvents with a simple 5-second polling loop using the indexer's hash-based change detection. Works reliably on all platforms (macOS, Linux, Windows). Runs an initial index on startup to catch stale files.
- LLM synthesis disabled by default — Claude interprets raw chunks directly, no second LLM needed
- `/welcome` confirms reindex result instead of silently completing
- Removed `watchdog` dependency — no longer needed

## [0.4.0] — 2026-03-25

### Added
- `/reindex` skill — quick trigger for memory_reindex MCP tool
- `pmem install-skills` command — copies skills to `~/.claude/commands/` with `--link` option for symlinks
- MCP server file logging to `~/.pmem-mcp.log` for diagnosing issues
- `pmem init` now detects and prints the full path to `pmem` in the MCP snippet (fixes pyenv/version manager compatibility)

### Fixed
- **MCP server session stability** — all blocking operations (ChromaDB, embedding, file I/O) now run in `asyncio.to_thread()` with 30s timeout, preventing event loop stalls that killed Claude Code sessions
- **MCP server lazy imports** — heavy modules only load on tool call, not on server startup
- **`auto_reindex_on_query` disabled in MCP context** — `/welcome` and `/sleep` handle freshness, removes seconds of overhead per query
- **`memory_status` no longer opens ChromaDB** — counts chunks from index_state.json (instant vs 700ms)
- **Stale SQLite lock recovery** — `ChunkStore` auto-cleans WAL/SHM files on init failure
- **MCP registration requires full path** — pyenv shims don't work in Claude Code's subprocess environment; documented and auto-detected

### Changed
- `/welcome` and `/sleep` skills now use `memory_reindex` MCP tool instead of `pmem index` bash command (prevents database lock conflicts)
- CLAUDE.md snippet updated: memory tools should only be used when explicitly asked, not proactively

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
