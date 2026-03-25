# TASKS.md — Task Index

---

## Active / In Progress

| Task | Status | Notes |
|------|--------|-------|
| Multi-collection support | ⬜ Designed | Architecture doc at `docs/multi-collection-design.md`, build deferred |
| Claude Code stability investigation | ⏸ Paused | "Interrupted" issue in Salesforce project traced to Claude Code bug, not pmem. Update to latest Claude Code resolved it. |

---

## Upcoming

| Task | Notes |
|------|-------|
| Docs: mcp-setup.md | MCP registration walkthrough (now ~/.claude.json, not settings.json) |
| `pmem init --interactive` | Guided setup — low priority |
| Non-markdown file support | `.py`, `.apex`, `.js` with language-aware chunking (Phase 3) |

---

## Complete

| Task | Completed | Notes |
|------|-----------|-------|
| Phase 1 build — core MVP | 2026-03-25 | All core modules: config, indexer, store, query, mcp_server, cli. 19 tests passing. |
| Phase 2 — robustness | 2026-03-25 | Watch, global config, error messages, init improvements, skills, install-skills. Most items complete. |
| MCP server stability | 2026-03-25 | Lazy imports, async thread pool, heartbeat logging, warning suppression, full path detection. |
| Skills: /welcome, /sleep, /reindex | 2026-03-25 | All three built, using MCP tools not bash. Reindex moved to Step 2 in /sleep. |
| LLM synthesis default disabled | 2026-03-25 | Claude interprets chunks directly — no need for second LLM. Available as opt-in. |
| README + docs for open source | 2026-03-25 | README covers full setup, CLI reference, skills, config, known issues. |
| Watcher rewrite + tests | 2026-03-25 | Replaced watchdog/FSEvents with polling (5s). Fixed fnmatch bug. 8 new watcher tests, 27 total. Removed watchdog dependency. |
