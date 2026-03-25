# Skills

These are Claude Code slash command skills that integrate with pmem. They are optional but recommended.

## Installation

Copy (or symlink) the skills you want into your Claude Code commands directory:

```bash
# Copy both skills
cp skills/welcome.md ~/.claude/commands/welcome.md
cp skills/sleep.md ~/.claude/commands/sleep.md
```

Or symlink so they stay in sync with the repo:

```bash
ln -sf "$(pwd)/skills/welcome.md" ~/.claude/commands/welcome.md
ln -sf "$(pwd)/skills/sleep.md" ~/.claude/commands/sleep.md
```

## Usage

- **`/welcome`** — Run at the start of each session. Reads governance files, runs an incremental reindex (fast if nothing changed), and confirms readiness.
- **`/sleep`** — Run at the end of each session. Full governance pass: updates tasks, docs, changelog, memory, and reindexes before closing out.

## How they work with pmem

Both skills check for `.memory/config.json` in the project root. If it exists, they run `pmem index` — `/welcome` at session start to catch any manual edits, `/sleep` at session end to capture changes made during the session.

The incremental index is fast when nothing has changed (~100ms for file hashing). It only embeds files whose content has actually changed.
