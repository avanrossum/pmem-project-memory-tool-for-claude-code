# SCOPE.md — Project Memory Tool: Full Architecture & Design

> This is the authoritative design document. All implementation decisions flow from here.
> Last updated: 2026-03-25

---

## Problem Statement

Claude Code sessions are stateless. Every session starts cold. Institutional knowledge lives in project files, but Claude has no way to semantically search them — it can only read files it's explicitly pointed to. Large projects accumulate significant history across hundreds of markdown files, task logs, and architecture docs. The cognitive load of keeping track of "what did we decide about X?" falls entirely on the human.

The goal: give Claude Code a queryable long-term memory that lives in the project, runs locally, costs nothing per query, and updates itself.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
│                                                             │
│   "What did we decide about the FSA cohort swap?"          │
│                          │                                  │
│                    MCP Tool Call                            │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (pmem)                         │
│                                                             │
│   1. Embed the query (local embedding model)               │
│   2. Search vector store for relevant chunks               │
│   3. Optionally synthesize answer via local LLM            │
│   4. Return results to Claude                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐     ┌─────────────────────────┐
│   ChromaDB Store    │     │   Local LLM Endpoint     │
│   (.memory/chroma/) │     │   (LMStudio / Ollama)   │
│                     │     │                         │
│   Embedded chunks   │     │   Synthesis / answering │
│   + metadata        │     │   (optional)            │
└─────────────────────┘     └─────────────────────────┘
              ▲
              │  (re-index on /sleep or file change)
              │
┌─────────────────────────────────────────────────────────────┐
│                      Indexer                                 │
│                                                             │
│   Scans include patterns → chunks markdown by headers →    │
│   hashes each chunk → embeds changed chunks only →         │
│   upserts to ChromaDB                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Per-Project Setup (`.memory/`)

Each project that adopts the tool gets a `.memory/` directory at its root:

```
.memory/
├── config.json       # Project-specific configuration
├── chroma/           # ChromaDB vector store (auto-created)
└── index_state.json  # File hash registry (for incremental updates)
```

`.memory/chroma/` and `.memory/index_state.json` should be in `.gitignore` (they're generated artifacts).
`.memory/config.json` should be committed — it's the project's memory configuration.

**Init command:** `pmem init` creates `.memory/config.json` with sensible defaults and prints the MCP registration snippet.

---

### 2. Configuration (`config.json`)

```json
{
  "project_name": "my-project",
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
    "exclude": [".memory/**", ".git/**", "node_modules/**", "*.lock"],
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

**Design decisions:**
- `split_on_headers: true` — markdown files are split at H1/H2/H3 boundaries first, then by size. This preserves semantic units (a section about FSA stays together rather than being split mid-sentence).
- `auto_reindex_on_query: true` — before answering any query, check if any indexed files have changed and re-embed them. Adds ~100ms overhead but ensures freshness. Can be disabled for speed.
- `top_k: 8` — retrieve 8 chunks by default. Enough context without overwhelming the LLM.

**Provider options for embedding:** `ollama`, `openai_compatible` (for LMStudio or any OpenAI-compatible server)
**Provider options for LLM:** `openai_compatible` (works for LMStudio, Ollama's OpenAI endpoint, real OpenAI, Anthropic via proxy — anything with `/v1/chat/completions`)

---

### 3. Indexer

The indexer is responsible for:
1. Scanning the project for files matching `include` patterns
2. Chunking each file into semantically meaningful pieces
3. Hashing each chunk
4. Comparing against `index_state.json` to find what's new or changed
5. Embedding only changed chunks
6. Upserting to ChromaDB

**Chunking strategy:**

For markdown files with `split_on_headers: true`:
```
# Top Level Heading          ← chunk boundary
...content...

## Sub Heading               ← chunk boundary
...content...                ← if > chunk_size, split further with overlap
```

Each chunk stores metadata:
```json
{
  "source_file": "tasks/2026-03-12_faculty-feedback-child-object/TASK.md",
  "heading_path": "Task: Faculty Feedback > Architectural Decisions > Stable external ID",
  "chunk_index": 3,
  "file_hash": "abc123...",
  "last_indexed": "2026-03-25T10:30:00Z"
}
```

**Incremental updates:**
- `index_state.json` maps `file_path → {hash, last_indexed, chunk_ids[]}`
- On each index run: hash each file → compare → only re-embed files where hash changed
- Deleted files: chunk IDs removed from ChromaDB

**CLI:** `pmem index` — runs incremental index. `pmem index --force` — re-embeds everything.

---

### 4. MCP Server

The MCP server is the interface between Claude Code and the memory system.

**Auto-detection:** The server detects the active project by walking up from CWD to find `.memory/config.json`. This means it works correctly regardless of which subdirectory Claude Code is open in.

**Exposed MCP tools:**

#### `memory_query`
```
Query the project memory for information about past decisions, architecture, tasks, or any documented context.

Parameters:
  question (str): Natural language question
  synthesize (bool, default: true): If true, pass retrieved chunks to LLM for a synthesized answer.
                                     If false, return raw chunk text (faster, no LLM required).
  top_k (int, optional): Number of chunks to retrieve. Defaults to config value.

Returns:
  answer (str): Synthesized answer or raw chunks
  sources (list): Source files and heading paths for each retrieved chunk
```

#### `memory_search`
```
Search project memory and return matching chunks with their source locations.
Use this when you want to find relevant documentation without synthesis.

Parameters:
  query (str): Search query

Returns:
  chunks (list): [{text, source_file, heading_path, relevance_score}]
```

#### `memory_status`
```
Return the current state of the project memory index.

Returns:
  project_name (str)
  indexed_files (int)
  total_chunks (int)
  last_indexed (str): ISO timestamp of most recent index run
  stale_files (list): Files that have changed since last index
  embedding_model (str)
  llm_enabled (bool)
```

#### `memory_reindex`
```
Trigger a reindex of the project memory. Use after significant documentation changes
or when memory_status shows stale files.

Parameters:
  force (bool, default: false): If true, re-embeds all files regardless of change state.

Returns:
  files_indexed (int)
  chunks_added (int)
  chunks_updated (int)
  chunks_removed (int)
  duration_seconds (float)
```

**MCP server registration** (added to `~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "project-memory": {
      "command": "pmem",
      "args": ["serve"]
    }
  }
}
```

The server uses the CWD of the Claude Code instance to auto-detect the project. One global registration works for all projects.

---

### 5. CLI (`pmem`)

```
pmem init                    Initialize memory for current project
                             Creates .memory/config.json with defaults
                             Prints MCP registration snippet

pmem index                   Incremental index (only changed files)
pmem index --force           Full reindex (all files)
pmem index --dry-run         Show what would be indexed without doing it

pmem query "your question"   Query memory from the terminal
pmem query "..." --no-llm    Return raw chunks only (no synthesis)

pmem status                  Show index state, stale files, config summary

pmem serve                   Start the MCP server (used by Claude Code)

pmem config                  Print current effective config
pmem config --edit           Open config.json in $EDITOR
```

---

### 6. Update Strategy

**Trigger 1: `/sleep` integration**
The global `/sleep` skill is updated to include a final step:
> After completing the governance pass, run `pmem index` if `.memory/config.json` exists in the project root. This keeps the memory index current with any documentation changes made during the session.

**Trigger 2: `auto_reindex_on_query`**
When enabled (default), the MCP server runs an incremental index check before answering any query. Files changed since last index are re-embedded inline. Adds minimal latency.

**Trigger 3: Manual**
`pmem index` can be run anytime from the terminal.

**Trigger 4: File watcher (optional, Phase 2)**
`pmem watch` starts a background file watcher using `watchdog`. Any file matching `include` patterns that changes triggers an incremental index. Intended for power users who want real-time freshness during active documentation sessions. Not required for core functionality.

---

### 7. Portability Design

The tool is designed to be adopted by any project with minimal friction:

**Installing the tool (once, globally):**
```bash
cd ~/Developer/project-memory-tool
pip install -e .
```

**Adopting in a new project (under 2 minutes):**
```bash
cd ~/my-project
pmem init
# Edit .memory/config.json to point to your LLM endpoint
# Add the MCP snippet to ~/.claude/settings.json (pmem init prints it)
# Add .memory/chroma/ and .memory/index_state.json to .gitignore
pmem index
```

**What changes in the project:**
- `.memory/config.json` (committed — this is your config)
- `.memory/chroma/` (gitignored — generated)
- `.memory/index_state.json` (gitignored — generated)
- `.gitignore` — two lines added

**What changes in Claude Code:**
- `~/.claude/settings.json` — one MCP server entry (done once, works for all projects)
- `CLAUDE.md` — optional but recommended: add a note that project memory is available via `memory_query`

---

### 8. Recommended `CLAUDE.md` Addition for Adopting Projects

Add this section to any project's `CLAUDE.md`:

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

## Hardware Recommendations

| Machine | Role | Notes |
|---------|------|-------|
| Mac Studio M1 MAX 96GB | LLM synthesis server | Run LMStudio with 70B model. Always-on via Cloudflare tunnel. |
| M5 MBP 32GB | Primary dev machine | Run 32B model locally or hit the Mac Studio. Both embedding and LLM can run here. |
| M2 MBP 16GB | Lightweight use | Embedding runs fine (nomic-embed-text is tiny). Point LLM at Mac Studio. |

**Embedding model:** `nomic-embed-text` via Ollama. Runs on all machines. ~600MB. No GPU required.

**Recommended LLM for synthesis:** `llama3.1:70b` or `qwen2.5:72b` on Mac Studio. For on-the-go: `llama3.1:8b` locally.

---

## What This Is Not

- **Not a fine-tuned model** — knowledge lives in files, not weights. Adding/changing docs is instant.
- **Not a cloud service** — everything runs locally. No data leaves your machines.
- **Not a replacement for reading files** — Claude should still read files directly when pointed to specific ones. This is for _discovery_ ("what do we know about X?") not _content retrieval_ ("show me TASK.md").
- **Not real-time** — the index is updated on sleep/query/manual trigger, not on every keystroke.

---

## Open Questions (resolve before or during Phase 1 build)

1. Should `.memory/config.json` support inheriting from a global default config at `~/.config/pmem/default.json`? Would reduce per-project boilerplate.
2. Should the MCP server stay resident or spawn per-request? Resident is faster; per-request is simpler.
3. ChromaDB vs LanceDB — ChromaDB is more mature; LanceDB is faster and has a smaller footprint. Evaluate both before committing.
4. Should `pmem init` offer to auto-add the `.gitignore` entries and `CLAUDE.md` snippet, or leave that to the user?
