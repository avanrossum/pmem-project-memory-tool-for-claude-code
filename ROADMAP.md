# ROADMAP.md — Project Memory Tool

> **Last updated:** 2026-03-25

---

## Phase 1 — Core (MVP)

Everything needed for a usable, working tool. End state: Alex can run `pmem init` in a project, run `pmem index`, and query memory from Claude Code via MCP.

- [ ] `pyproject.toml` — package setup, entry point for `pmem` CLI, dependencies
- [ ] `src/project_memory/config.py` — load/validate `config.json`, walk up CWD to find `.memory/`, global defaults
- [ ] `src/project_memory/indexer.py` — glob files, header-aware markdown chunker, file hashing, incremental diff
- [ ] `src/project_memory/store.py` — ChromaDB wrapper: init collection, upsert chunks, similarity search, delete by file
- [ ] `src/project_memory/query.py` — retrieval + optional LLM synthesis via OpenAI-compatible endpoint
- [ ] `src/project_memory/mcp_server.py` — MCP server with `memory_query`, `memory_search`, `memory_status`, `memory_reindex` tools
- [ ] `src/project_memory/cli.py` — `pmem init`, `pmem index`, `pmem query`, `pmem status`, `pmem serve`, `pmem config`
- [ ] `docs/integration-guide.md` — step-by-step: install, init, configure, MCP register
- [ ] `docs/configuration.md` — full config reference with all options documented
- [ ] `docs/mcp-setup.md` — exact `settings.json` snippet + verification steps
- [ ] `README.md` — quick start in under 10 steps
- [ ] Basic tests — config loading, chunking, hash detection, MCP tool schemas

**Success criteria for Phase 1:**
- `pmem init` creates valid config in under 5 seconds
- `pmem index` successfully embeds a 50-file markdown project
- `memory_query` returns a relevant answer via Claude Code MCP call
- Works on M5 MBP pointing at local Ollama

---

## Phase 2 — Robustness & Polish

- [ ] `pmem watch` — background file watcher; re-indexes on change
- [ ] Global default config at `~/.config/pmem/config.json` — override per-project
- [ ] `pmem init --interactive` — guided setup (asks for endpoints, writes config)
- [ ] `pmem init` auto-appends `.memory/chroma/` and `index_state.json` to `.gitignore`
- [ ] `pmem init` optionally appends `CLAUDE.md` snippet
- [ ] LanceDB as an alternative vector store option (evaluate vs ChromaDB)
- [ ] Better error messages — detect "Ollama not running", "model not found", etc. and give actionable advice
- [ ] `/sleep` skill update — add `pmem index` step conditionally (only if `.memory/config.json` exists)
- [ ] Multi-collection support — index different subsets separately (e.g. "tasks only", "architecture only")

---

## Phase 3 — Power Features

- [ ] `pmem diff "question"` — show what changed in the answer since last index (useful for tracking how understanding of a topic has evolved)
- [ ] Web UI (optional) — lightweight local UI for browsing chunks and running queries without Claude
- [ ] Cloudflare tunnel setup guide — run embedding + LLM on Mac Studio, query from any machine
- [ ] `pmem export` — dump indexed chunks to JSON for backup or migration
- [ ] Support for non-markdown file types (`.py`, `.apex`, `.js`) with language-aware chunking

---

## Backlog / Open Questions

- Should the MCP server stay resident or spawn per-request?
- ChromaDB vs LanceDB — evaluate size, speed, and reliability before Phase 1 ships
- Should `pmem init` support a `--template` flag for project-type-specific configs (e.g. `--template salesforce`, `--template nextjs`)?
