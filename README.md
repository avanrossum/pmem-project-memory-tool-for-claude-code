# pmem — Project Memory Tool

A portable, local-first RAG memory layer for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) projects. Gives Claude semantic search over your project's documentation, decisions, and history — using local models, with no external API dependencies.

Think of it as long-term memory that persists across Claude Code sessions, queryable via MCP.

## How it works

```
Claude Code → MCP tool call → pmem server
                                  ↓
                        embed query (Ollama)
                                  ↓
                        search ChromaDB (local)
                                  ↓
                        (optional) synthesize answer via local LLM
                                  ↓
                        return answer + sources to Claude
```

pmem indexes your project's markdown and text files into a local vector database (ChromaDB). When Claude needs context, it queries the memory via MCP tools — no copy-pasting, no manual file pointing.

## Quick start

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

Pull the embedding model (~274MB, one-time):

```bash
ollama pull nomic-embed-text
```

### 2. Install pmem

```bash
git clone https://github.com/yourusername/project-memory-tool.git
cd project-memory-tool
pip install -e .
pmem install-skills
```

### 3. Register the MCP server

Add this to `~/.claude/settings.json` (one-time, works for all projects):

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "/full/path/to/pmem",
      "args": ["serve"]
    }
  }
}
```

> **Important:** Use the full path to `pmem`, not just `"pmem"`. Claude Code spawns MCP servers as subprocesses without your shell profile, so pyenv shims and other version managers won't work. Run `which pmem` to get the path. `pmem init` prints the correct snippet automatically.

### 4. Initialize in your project

```bash
cd ~/your-project
pmem init
pmem index
```

That's it. Claude Code can now query your project's memory.

## CLI reference

```
pmem init                       Create .memory/config.json with sensible defaults
pmem index                      Incremental index (only changed files)
pmem index --force              Full reindex (re-embed everything)
pmem index --dry-run            Show what would be indexed
pmem query "your question"      Query memory from the terminal
pmem query "..." --no-llm       Return raw chunks (no LLM synthesis)
pmem status                     Show index state, stale files, config
pmem exclude "snapshots/**"     Add a pattern to the exclude list
pmem include "**/*.py"          Add a pattern to the include list
pmem serve                      Start the MCP server (used by Claude Code)
pmem config                     Print current config
pmem config --edit              Open config in $EDITOR
pmem config --global            Show global config
pmem config --init-global       Create global config at ~/.config/pmem/config.json
pmem watch                      Watch for file changes and reindex automatically
pmem install-skills             Install /welcome, /sleep, /reindex to Claude Code
pmem install-skills --link      Symlink instead of copy (macOS/Linux)
```

> **Note:** Don't run `pmem index` or `pmem watch` from the terminal while Claude Code is active on the same project — they can cause database lock conflicts with the MCP server. Use the `memory_reindex` MCP tool (or `/reindex` skill) from within Claude Code instead. `pmem watch` is ideal for keeping the index fresh during manual editing sessions when Claude Code is not running.

## MCP tools

Once registered, Claude Code has access to four tools:

| Tool | Description |
|------|-------------|
| `memory_query` | Ask a natural language question — retrieves relevant chunks and optionally synthesizes an answer via a local LLM |
| `memory_search` | Search for matching chunks with source locations (no synthesis) |
| `memory_status` | Check index state: file count, chunk count, stale files, config |
| `memory_reindex` | Trigger a reindex from within Claude Code |

## Configuration

`pmem init` creates `.memory/config.json` in your project root:

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

### Embedding providers

| Provider | Config | Notes |
|----------|--------|-------|
| `ollama` (default) | `endpoint: "http://localhost:11434"` | Uses `/api/embed` (batch). Free, local. |
| `openai_compatible` | Any OpenAI-compatible endpoint | Uses `/v1/embeddings`. Works with LMStudio, vLLM, etc. |

### LLM synthesis

Synthesis is optional. When enabled, retrieved chunks are sent to a local LLM to generate a concise answer. When disabled (or when using `--no-llm`), raw chunks are returned directly.

Any OpenAI-compatible endpoint works — LMStudio, Ollama's OpenAI mode, vLLM, or even a remote API.

### Indexing options

- **`include`** — glob patterns for files to index (default: `*.md`, `*.txt`)
- **`exclude`** — glob patterns to skip (default: `.memory/`, `.git/`, `node_modules/`, lock files)
- **`chunk_size`** — target chunk size in words (default: 400)
- **`chunk_overlap`** — overlap between chunks in words (default: 80)
- **`split_on_headers`** — split markdown at H1/H2/H3 boundaries before splitting by size (default: true)

### Query options

- **`top_k`** — number of chunks to retrieve per query (default: 8)
- **`auto_reindex_on_query`** — check for stale files before every query and re-embed if needed (default: true, adds ~100ms)

## What gets created in your project

```
your-project/
└── .memory/
    ├── config.json        ← commit this (your project's memory config)
    ├── chroma/            ← gitignore (generated vector store)
    └── index_state.json   ← gitignore (file hash registry)
```

Add to your `.gitignore`:

```
.memory/chroma/
.memory/index_state.json
```

## Skills (optional)

pmem ships with three Claude Code slash command skills:

- **`/welcome`** — Run at the start of each session. Reads governance files, runs incremental reindex, confirms readiness.
- **`/sleep`** — Run at the end of each session. Full governance pass: updates tasks, docs, changelog, memory, and reindexes.
- **`/reindex`** — Quick trigger to refresh the memory index mid-session.

### Install skills

```bash
# Recommended: use the built-in installer
pmem install-skills

# Or with symlinks (stays in sync with repo, macOS/Linux only)
pmem install-skills --link
```

Or manually:

```bash
# Copy
cp skills/welcome.md ~/.claude/commands/welcome.md
cp skills/sleep.md ~/.claude/commands/sleep.md
cp skills/reindex.md ~/.claude/commands/reindex.md

# Or symlink (macOS/Linux only)
ln -sf "$(pwd)/skills/welcome.md" ~/.claude/commands/welcome.md
ln -sf "$(pwd)/skills/sleep.md" ~/.claude/commands/sleep.md
ln -sf "$(pwd)/skills/reindex.md" ~/.claude/commands/reindex.md
```

## Recommended CLAUDE.md snippet

Add this to any project using pmem so Claude knows it's available:

```markdown
## Project Memory

This project has a local RAG memory index via `pmem`. Use the `memory_query` MCP tool when:
- Looking for past decisions, context, or rationale ("why did we do X?")
- Searching for historical task context or outcomes
- Finding documented gotchas or lessons learned

Do NOT use memory_query for: reading specific known files, checking current code
state, or anything derivable from `git log`. The index updates at session start
(`/welcome`) and session end (`/sleep`), so it may be slightly behind mid-session.

If results seem stale, run `memory_reindex` to refresh.
```

## Hardware notes

| Setup | Embedding | LLM synthesis |
|-------|-----------|---------------|
| Any Mac (even 8GB) | Runs locally — nomic-embed-text is tiny | Point at a remote machine or disable |
| 32GB+ Mac | Runs locally | Run 8B–32B model locally via Ollama/LMStudio |
| Dedicated server (Mac Studio, etc.) | Runs locally | Run 70B+ model, expose via Cloudflare tunnel |

## Design principles

- **Local-first** — no data leaves your machine. No API keys required.
- **Portable** — install once globally, `pmem init` in any project.
- **Low friction** — setup takes under 2 minutes. Querying is automatic via MCP.
- **Minimal dependencies** — no LangChain, no LlamaIndex. Just ChromaDB, httpx, click, and the MCP SDK.

## License

MIT
