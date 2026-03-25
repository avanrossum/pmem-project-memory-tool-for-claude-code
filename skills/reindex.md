# /reindex — Refresh Project Memory Index

Run the `memory_reindex` MCP tool to refresh the project's memory index.

This embeds any files that have changed since the last index. It is incremental — unchanged files are skipped.

If the index seems stale or you've just made significant documentation changes, pass `force: true` to re-embed everything.

Do not run `pmem index` as a bash command while Claude Code is active — use this skill or the `memory_reindex` MCP tool directly to avoid database lock conflicts.
