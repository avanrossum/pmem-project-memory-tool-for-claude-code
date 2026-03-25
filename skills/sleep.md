# /sleep — Session Governance Pass

You are performing a governance pass at the end of a working session. The goal is to move important context from short-term (this conversation) into long-term storage (version-controlled files) so that future sessions — and future instances of you — can pick up exactly where we left off with full context.

Think of this as committing to memory before shutting down.

---

## Step 1 — Orient

Identify what kind of project this is:

- Does it have a `CLAUDE.md`? Read it. Follow any project-specific governance instructions it contains.
- Does it have a `TASKS.md` or equivalent task index? Read it.
- Does it have `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`, `LESSONS_LEARNED.md`? Read whichever exist.
- Does it use a `tasks/YYYY-MM-DD_name/TASK.md` folder structure? Note any open task folders.

If none of these exist, adapt: look for whatever passes as documentation in this project (README, docs/, ADRs, etc.) and treat those as the governance surfaces.

---

## Step 2 — Update Project Memory Index (do this early)

If this project has a `.memory/config.json`, **use the `memory_reindex` MCP tool now** — before the governance updates below. This ensures the index captures any documentation changes made during the session. Do it early because the MCP server may not be available later in the flow.

After the reindex completes, briefly confirm it — e.g. "Memory index refreshed (2 files re-embedded)."

Do NOT run `pmem index` as a bash command. If the MCP tool is not available, skip silently.

---

## Step 3 — Review Open Tasks

For each open or in-progress task:
- Is the TASK.md (or equivalent) up to date with what happened this session?
- Has status changed? Update it.
- Are there new decisions, blockers, or discoveries that aren't captured? Add them.
- Is anything that was "in progress" now complete, or newly blocked? Reflect that.
- Are there any tasks that should be archived or closed?

---

## Step 4 — Update Governance Files

Work through each governance file that exists and ask: *does this reflect the current state of the world?*

**CHANGELOG.md** — Was meaningful work done this session that isn't logged? Add an entry. Follow the existing versioning convention.

**ARCHITECTURE.md** — Was anything discovered or confirmed about the system's structure, integrations, objects, or components? Log it.

**ROADMAP.md** — Did priorities shift? Were milestones hit? Were new items identified? Update accordingly.

**LESSONS_LEARNED.md** — Was anything non-obvious encountered — a gotcha, an anti-pattern, a confirmed pattern, a platform constraint? Log it so future sessions don't re-learn it.

**CLAUDE.md** — Did any new conventions, rules, or workflow decisions get established this session? If so, update it.

---

## Step 5 — Capture Loose Context

Scan the conversation for anything important that hasn't been written down yet:

- Decisions made but not logged
- Open questions surfaced but not tracked
- "We should do X later" items not in any backlog
- Architectural observations worth preserving
- Any "we tried that and it didn't work" moments

Write these to the appropriate file. If no file is right, add them to LESSONS_LEARNED.md or the relevant TASK.md.

---

## Step 6 — Check Memory

If this project uses the auto-memory system (`~/.claude/projects/.../memory/`):
- Are there user preferences, feedback, or project context items worth saving that aren't already there?
- Are any existing memories now stale or incorrect? Update or remove them.

Note: for projects with a `CLAUDE.md`, the repo files are the authoritative source of truth. Memory is a convenience cache only.

---

## Step 7 — Report

When done, give a brief summary:
- What files were updated and why
- Any open questions or blockers that couldn't be resolved
- What the next session should pick up first

Keep it short. The point is that everything important is now in the files — the summary is just a receipt.
