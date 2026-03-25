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

If this project has a `.memory/config.json` (i.e. the project memory tool is set up), run an incremental index:

```bash
pmem index
```

This is fast when nothing has changed (just file hashing, no embedding). It ensures any manual documentation edits made between sessions are captured.

If `pmem` is not installed or `.memory/config.json` does not exist, skip this step silently.

---

## Step 3 — Check Memory Status

If the memory index exists, run:

```bash
pmem status
```

Briefly note the state (indexed files, stale files) but do not print the full output to the user unless something looks wrong (e.g. many stale files after indexing, or zero indexed files).

---

## Step 4 — Ready

Give a brief one-line confirmation that you're oriented and ready. Mention:
- The project name
- How many tasks are open (if TASKS.md exists)
- Whether the memory index is fresh

Do not dump file contents or lengthy summaries. The point is speed — get oriented and get to work.
