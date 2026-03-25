# ROADMAP.md — Project Memory Tool

> **Last updated:** 2026-03-25

---

## Phase 1 — Core (MVP) ✅

Everything needed for a usable, working tool.

- [x] `pyproject.toml` — package setup, entry point for `pmem` CLI, dependencies
- [x] `src/project_memory/config.py` — load/validate `config.json`, walk up CWD to find `.memory/`, global defaults
- [x] `src/project_memory/indexer.py` — glob files, header-aware markdown chunker, file hashing, incremental diff
- [x] `src/project_memory/store.py` — ChromaDB wrapper: init collection, upsert chunks, similarity search, delete by file
- [x] `src/project_memory/query.py` — retrieval + optional LLM synthesis via OpenAI-compatible endpoint
- [x] `src/project_memory/mcp_server.py` — MCP server with 4 tools (async, thread pool, lazy imports)
- [x] `src/project_memory/cli.py` — all CLI commands including install-skills
- [x] `README.md` — quick start, CLI reference, config, skills, known issues
- [x] Basic tests — 19 tests covering config, chunking, hashing, scanning, store

---

## Phase 2 — Robustness & Polish (mostly complete)

- [x] `pmem watch` — polling-based watcher; re-indexes on change (5s interval, cross-platform)
- [x] Global default config at `~/.config/pmem/config.json` — deep-merged with project config
- [ ] `pmem init --interactive` — guided setup (asks for endpoints, writes config)
- [x] `pmem init` auto-appends `.memory/chroma/` and `index_state.json` to `.gitignore`
- [x] `pmem init` appends `CLAUDE.md` snippet if CLAUDE.md exists
- [x] Better error messages — detect "Ollama not running", "model not found", actionable advice
- [x] `/welcome`, `/sleep`, `/reindex` skills — using MCP tools, not bash
- [x] `pmem install-skills` — one-command skill installation
- [x] MCP server stability — async thread pool, lazy imports, heartbeat logging, warning suppression
- [x] LLM synthesis disabled by default — Claude interprets chunks directly
- [x] `auto_reindex_on_query` disabled by default — skills handle freshness
- [ ] Multi-collection support — designed (see `docs/multi-collection-design.md`), not yet implemented
- [ ] LanceDB evaluation — shelved (ChromaDB is fine for typical use)

---

## Phase 3 — Power Features

- [ ] Multi-collection build (architecture ready in docs/multi-collection-design.md)
- [ ] `pmem diff "question"` — show what changed in the answer since last index
- [ ] Support for non-markdown file types (`.py`, `.apex`, `.js`) with language-aware chunking
- [ ] `pmem export` — dump indexed chunks to JSON for backup or migration
- [ ] Web UI (optional) — lightweight local UI for browsing chunks and running queries
- [ ] Cloudflare tunnel setup guide — run embedding + LLM on Mac Studio, query from any machine

---

## Backlog / Resolved Questions

- ~~Should the MCP server stay resident or spawn per-request?~~ → Resident per Claude Code session (stdio subprocess)
- ~~ChromaDB vs LanceDB~~ → ChromaDB, shelved LanceDB evaluation
- Should `pmem init` support a `--template` flag for project-type-specific configs?
