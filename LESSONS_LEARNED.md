# LESSONS_LEARNED.md

> Patterns, gotchas, and findings specific to this project. Update as they're discovered.

---

## Design Decisions (rationale captured at scope time)

### Why ChromaDB over a simpler approach (e.g. flat JSON + cosine similarity)
A flat JSON approach works for small projects but degrades quickly above ~1,000 chunks. ChromaDB handles persistence, metadata filtering, and similarity search efficiently at project scale. It's also file-based — no server, no Docker, no ports. The tradeoff is a heavier dependency, but it's worth it.

### Why no LangChain / LlamaIndex
Both frameworks are excellent but add significant abstraction and dependency weight. For a focused tool like this, the core operations (chunk → embed → store → retrieve → synthesize) are simple enough to implement directly. Keeping the code readable and dependency-light is more important than framework convenience.

### Why OpenAI-compatible API for LLM synthesis
LMStudio, Ollama, and real OpenAI all speak `/v1/chat/completions`. One client implementation works everywhere. No vendor lock-in. If the user wants to switch from a local model to Claude or OpenAI for synthesis, it's a config change, not a code change.

### Why nomic-embed-text as the default embedding model
- Runs locally via Ollama with no GPU
- 768-dimensional embeddings — good quality at low cost
- ~274M parameters — loads fast even on 16GB machines
- Well-supported and widely benchmarked
- Free to use with no API key

### Why walk up from CWD to find `.memory/`
Claude Code's CWD may be the project root or any subdirectory. Walking up ensures `pmem` commands and the MCP server work correctly regardless of where you are in the project tree. Same pattern used by git, which users already understand intuitively.

---

## Known Issues

### MCP server registration requires full path to `pmem`
Claude Code spawns MCP servers as subprocesses without the user's shell profile. Pyenv shims, nvm, and other version managers are not on the PATH. The `command` field in MCP registration must be the full absolute path (e.g. `/Users/you/.pyenv/versions/3.11.9/bin/pmem`). `pmem init` detects and prints the correct path automatically.

### MCP registration goes in `~/.claude.json`, not `~/.claude/settings.json`
As of Claude Code v2.1.x, MCP servers are defined in `~/.claude.json` (global) or `.mcp.json` (per-project). The `settings.json` file is for permissions and hooks only.

### Claude Code shows "Running…" after MCP tool completes
When an MCP tool finishes while Claude is still generating a response, the UI may continue to show "Running…" next to the tool call. This is a Claude Code display issue — the tool has completed successfully. Check `~/.pmem-mcp.log` to verify.

### MCP tool timeout can be configured
If memory tools are timing out, set `MCP_TIMEOUT` and `MCP_TOOL_TIMEOUT` in `~/.claude/settings.json` under `env`. Default timeouts should be sufficient for pmem (typical calls complete in under 1s), but larger projects or slow Ollama instances may need more headroom. See [Issue #424](https://github.com/anthropics/claude-code/issues/424) and [Issue #22542](https://github.com/anthropics/claude-code/issues/22542).

### CLAUDE.md must explicitly restrict proactive memory tool use
Without clear instructions, Claude will proactively call `memory_query` during normal work, adding latency to every interaction. The CLAUDE.md snippet must say "ONLY use memory tools when the user explicitly asks." See `skills/claude-md-snippet.md` for the recommended wording.
