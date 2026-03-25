# Integration Guide — Adding Project Memory to an Existing Project

This guide covers everything needed to adopt the project memory tool in an existing Claude Code project.

---

## Prerequisites

- Ollama installed and running (`ollama serve`)
- `nomic-embed-text` pulled: `ollama pull nomic-embed-text`
- An LLM for synthesis (optional but recommended):
  - LMStudio with a model loaded, or
  - `ollama pull llama3.1:8b` (or any model)
- Project Memory Tool installed: `pip install -e ~/Developer/project-memory-tool`

---

## Step 1 — Initialize

From your project root:

```bash
pmem init
```

This creates `.memory/config.json` with defaults and prints the MCP registration snippet. Review the config and update the LLM endpoint if needed.

---

## Step 2 — Configure

Open `.memory/config.json`:

```json
{
  "project_name": "your-project-name",
  "embedding": {
    "endpoint": "http://localhost:11434",
    "model": "nomic-embed-text",
    "provider": "ollama"
  },
  "llm": {
    "endpoint": "http://localhost:1234/v1",
    "model": "local-model",
    "provider": "openai_compatible",
    "enabled": true
  },
  "indexing": {
    "include": ["**/*.md", "**/*.txt"],
    "exclude": [".memory/**", ".git/**", "node_modules/**"],
    "chunk_size": 400,
    "chunk_overlap": 80,
    "split_on_headers": true
  },
  "query": {
    "top_k": 8,
    "auto_reindex_on_query": true
  }
}
```

**Common adjustments:**
- Point `llm.endpoint` at your Mac Studio if using a remote LLM: `http://mac-studio.local:1234/v1`
- Set `llm.enabled: false` if you only want raw chunk retrieval (no synthesis)
- Narrow `indexing.include` if your project has lots of non-documentation files

---

## Step 3 — Update `.gitignore`

Add these two lines:

```
.memory/chroma/
.memory/index_state.json
```

Commit `.memory/config.json` — that's your project's memory configuration and belongs in source control.

---

## Step 4 — Register the MCP Server

Add to `~/.claude/settings.json` (under `mcpServers`):

```json
"project-memory": {
  "command": "pmem",
  "args": ["serve"]
}
```

This is a one-time global registration. The same entry works for all projects — the server auto-detects which project it's serving from the CWD.

Restart Claude Code to pick up the new MCP server.

---

## Step 5 — Index the Project

```bash
pmem index
```

This will scan your project files, chunk them, embed them, and store them. For a typical project with 50–100 markdown files this takes 30–60 seconds on the first run. Subsequent runs are incremental and much faster.

Check the result:

```bash
pmem status
```

---

## Step 6 — Update `CLAUDE.md` (recommended)

Add this section to your project's `CLAUDE.md`:

```markdown
## Project Memory

This project has a local RAG memory index. Query it via the `memory_query` MCP tool for:
- Past architectural decisions
- Why specific design choices were made
- Historical task context and outcomes
- Known gotchas and lessons learned

The index is updated automatically at the end of each session via `/sleep`.
Run `pmem status` to check index freshness. Run `pmem index` to manually refresh.
```

---

## Step 7 — Verify

In Claude Code, try:

> "Use memory_query to find what we know about [something in your project]"

You should get a sourced answer drawn from your project's documentation.

---

## Keeping the Index Fresh

The index stays fresh via three mechanisms:

1. **`/sleep`** — the global sleep skill runs `pmem index` at the end of every session (if `.memory/config.json` exists)
2. **`auto_reindex_on_query`** — before answering any MCP query, changed files are re-embedded automatically
3. **Manual** — run `pmem index` anytime

You should never need to think about index freshness during normal use.
