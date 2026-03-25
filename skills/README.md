# Skills

These are Claude Code slash command skills that integrate with pmem. They are optional but recommended.

## Installation

```bash
# Recommended: use the built-in installer
pmem install-skills

# Or with symlinks (stays in sync with repo, macOS/Linux only)
pmem install-skills --link
```

## Usage

- **`/welcome`** — Run at the start of each session. Reads governance files, refreshes the memory index via MCP, and confirms readiness.
- **`/sleep`** — Run at the end of each session. Full governance pass: updates tasks, docs, changelog, memory, and reindexes via MCP.
- **`/reindex`** — Quick trigger to refresh the memory index mid-session.

## How they work with pmem

All skills use the `memory_reindex` MCP tool (not the `pmem index` bash command) to avoid database lock conflicts when Claude Code is active.

The incremental index is fast when nothing has changed (~100ms for file hashing). It only embeds files whose content has actually changed.
