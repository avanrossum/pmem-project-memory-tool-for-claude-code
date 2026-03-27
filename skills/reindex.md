# /reindex — Refresh Project Memory Index

Run the `memory_reindex` MCP tool to refresh the project's memory index. The tool's full name is `mcp__project-memory__memory_reindex` — if you need to search for it via ToolSearch, search for `"memory"` (not the full name, which may not match).

This embeds any files that have changed since the last index. It is incremental — unchanged files are skipped.

If the index seems stale or you've just made significant documentation changes, pass `force: true` to re-embed everything.

Do not run `pmem index` as a bash command while Claude Code is active — use this skill or the `memory_reindex` MCP tool directly to avoid database lock conflicts.
