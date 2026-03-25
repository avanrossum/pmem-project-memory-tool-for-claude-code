# /welcome — Session Start

You are starting a new working session. The goal is to ensure you have fresh context and an up-to-date memory index before doing any work.

Keep this fast — most of the time nothing has changed and this should take seconds, not minutes.

---

## Step 1 — Orient

Read the project's governance files to understand current state:

- `CLAUDE.md` — project rules and conventions (read first, always)
- `TASKS.md` — what's open, what's next
- `ARCHITECTURE.md` — current system state
- `ROADMAP.md` — priorities and milestones

If these don't exist, adapt to whatever documentation the project uses.

---

## Step 2 — Refresh Memory Index

If this project has a `.memory/config.json` (i.e. the project memory tool is set up):

**Use the `memory_reindex` MCP tool** to refresh the index. Do NOT run `pmem index` as a bash command — running it via bash risks leaving database locks if interrupted.

After the reindex completes, briefly confirm it to the user — e.g. "Memory index refreshed (0 files changed)" or "Memory index updated (3 files re-embedded)." Don't dump the raw tool output, just a one-line summary.

If the `memory_reindex` MCP tool is not available (e.g. MCP server not registered), skip this step silently.

If the MCP tool is not available, skip silently.

---

## Step 4 — Ready

Give a brief one-line confirmation that you're oriented and ready. Mention:
- The project name
- How many tasks are open (if TASKS.md exists)
- Whether the memory index is fresh

Do not dump file contents or lengthy summaries. The point is speed — get oriented and get to work.
