# CHANGELOG.md

---

## [0.5.3] — 2026-04-03

### Added
- **Minimum chunk size** — new `min_chunk_size` config option (default: 50 words). Sections below this threshold are merged with adjacent sections instead of becoming standalone chunks. Prevents tiny, semantically meaningless chunks (e.g. "CTA", single headings) from polluting the vector store.
- **`_merge_small_sections()` in indexer** — merges undersized header sections forward into the next section; last undersized section merges backward. Chained small sections accumulate correctly.
- 6 new tests for section merging (forward, backward, chain, all-small, preserves-large, integration)

### Changed
- Test count: 27 → 33

### Migration
- Existing indexes should be rebuilt with `pmem index --force` to re-chunk with the new merge logic. Without rebuilding, existing tiny chunks remain in the index.

## [0.5.2] — 2026-03-27

### Added
- **Update notifications** — checks GitHub releases once per day, appends notice to `pmem status` and MCP tool responses when a newer version is available. Supports stable/beta channels via `update_channel` config field.
- **Beta release track** — set `"update_channel": "beta"` to get notified about pre-releases. Documented in README.
- **`update_channel` config field** — new top-level config option (default: `"stable"`)

### Fixed
- **Nested `node_modules` indexed** — exclude pattern `node_modules/**` was anchored to root, so nested instances (e.g. `infographics/node_modules/`) slipped through. Changed defaults to `**/node_modules/**` and `**/.git/**`.
- **`.gitignore` too specific** — `pmem init` now adds `.memory/` instead of `.memory/chroma/` and `.memory/index_state.json` individually. Catches transient files like `index_state.lock`.
- **Skill ToolSearch failure** — `/welcome`, `/sleep`, and `/reindex` referenced `memory_reindex` but the runtime MCP name is `mcp__project-memory__memory_reindex`. Added full name and hint to search by keyword `"memory"`.
- **Wrong GitHub repo name** in update checker — was missing `-code` suffix from repo URL

### Changed
- PyPI publishing added to Phase 3 roadmap
- README install section notes PyPI is pending

## [0.5.1] — 2026-03-26

### Fixed
- **Version mismatch** (H1) — `__init__.py` now reads version from `importlib.metadata` instead of hardcoded string that was stuck at 0.4.0
- **LLM config default** (H2) — `LLMConfig.enabled` dataclass default changed from `True` to `False` to match `DEFAULT_CONFIG`; CLI users without an `llm` section no longer get synthesis errors
- **Stale lock cleanup removed** (H3) — `_cleanup_stale_locks` deleted WAL/SHM files unconditionally, risking corruption when another process had the database open; retry now catches specific `sqlite3.OperationalError`/`ChromaError` instead of bare `except Exception`
- **Index state concurrency** (H4) — `IndexState.save/load` now use `fcntl.flock` for cross-process serialization and atomic temp+rename writes; corrupted state files produce actionable error messages
- **Signal handler** (H5) — MCP server signal handler no longer swallows SIGTERM/SIGINT; re-raises via `SIG_DFL` so the server can actually be killed
- **Progress callback timing** (M6) — embedding progress fires after successful API response, not before the request

### Changed
- **mtime pre-check** (M1) — watcher/indexer skip SHA-256 hashing for files whose mtime hasn't changed, major performance improvement for polling
- **OpenAI embedding batching** (M3) — `_embed_openai_compatible` now batches at 25 texts, matching the Ollama path
- **Counter renamed** (M4) — `IndexResult.chunks_updated` → `chunks_replaced` for clearer semantics
- **Log rotation** (L4) — MCP server uses `RotatingFileHandler` (5MB, 2 backups) instead of unbounded `FileHandler`
- Cleaned up non-standard `__import__` hacks and `subprocess.os.environ` access
- Removed unused `asdict` import from indexer
- Added docstring note that H4-H6 headers are intentionally ignored by the markdown splitter

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
