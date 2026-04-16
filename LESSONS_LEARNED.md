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

### LLM synthesis is redundant when Claude is the consumer
The original design included local LLM synthesis (via LMStudio/Ollama) to summarize retrieved chunks. In practice, Claude Code is already an LLM — sending chunks to a second LLM for synthesis is unnecessary overhead and adds a dependency (LMStudio on port 1234). LLM synthesis is now disabled by default. It remains available for standalone terminal use (`pmem query`).

### MCP server must not block the async event loop
All ChromaDB operations, embedding calls, and file I/O are synchronous and will block the MCP server's async event loop if called directly. This causes the MCP protocol connection to stall, which can destabilize the entire Claude Code session. All blocking work must run via `asyncio.to_thread()`.

### ChromaDB init is expensive on large indexes (~700ms for 6000 chunks)
Opening a ChromaDB PersistentClient on a 25MB database takes ~700ms. The `run_index` function now checks for changes before opening ChromaDB — if nothing is stale, it returns immediately. The MCP `memory_status` tool reads from `index_state.json` instead of opening ChromaDB.

### Don't delete WAL/SHM files to "fix" ChromaDB lock issues
An earlier version had `_cleanup_stale_locks()` that deleted SQLite WAL/SHM files when ChromaDB failed to open. This is dangerous — if another process (MCP server, watcher) has the database open, deleting active WAL files causes data corruption. The fix was to remove the cleanup entirely and let ChromaDB/SQLite handle their own recovery. The retry-once pattern still exists but only catches specific exceptions.

### Index state needs cross-process locking
`index_state.json` is read and written by the MCP server, CLI, and watcher — potentially concurrently. Without file locking, two processes can read stale state, both index the same file, and one overwrites the other's changes. Uses `fcntl.flock` (shared lock for reads, exclusive for writes) plus atomic temp+rename writes.

### Claude Code periodically kills and restarts MCP server subprocesses
Observed during testing: the MCP server process exits cleanly (`SERVER_SHUTDOWN` + `SERVER_EXIT atexit`) after minutes of idle time, then Claude Code restarts it seconds later. If a tool call is in flight when this happens, it gets dropped. The `/sleep` skill now runs reindex as Step 2 (early) instead of Step 6 (late) to avoid this.

### Exclude patterns must use `**/` prefix to match nested directories
The default exclude `node_modules/**` only matched at the project root because gitignore-style patterns without a leading `**/` are anchored. A nested `infographics/node_modules/` passed through indexing and polluted the vector store. The fix: `**/node_modules/**`. Same applies to `.git/**` → `**/.git/**`. Existing projects keep their old config — only new `pmem init` projects get the corrected defaults.

### MCP tool names are prefixed at runtime
Skills that reference `memory_reindex` fail ToolSearch because Claude Code registers the tool as `mcp__project-memory__memory_reindex`. When instructing Claude to find an MCP tool, use a broad keyword search (e.g. `"memory"`) rather than the exact tool name.

### GitHub API repo redirects aren't followed by httpx by default
The repo was renamed from `pmem-project-memory-tool-for-claude` to `pmem-project-memory-tool-for-claude-code`. GitHub returns a 301 redirect, but the releases endpoint returned `"Moved Permanently"` as JSON rather than actually redirecting. Always use the canonical repo name in API URLs.

### Tiny chunks from header splitting pollute search results
Markdown header-aware chunking splits at every H1/H2/H3 boundary with no minimum size. Changelog entries, table-of-contents sections, and stub headings produce 1-3 word chunks that embed with minimal semantic signal but match many queries (high false-positive rate). Fix: `_merge_small_sections()` combines undersized sections with neighbors before chunking. Default `min_chunk_size` is 50 words. Existing indexes need `pmem index --force` to re-chunk.

### fnmatch doesn't understand `**` — use pathspec everywhere
Python's `fnmatch` treats `*` and `**` identically and doesn't do recursive directory matching. `fnmatch.fnmatch("README.md", "**/*.md")` returns `False`. The watcher originally used `fnmatch` while the indexer used `pathspec` (gitignore-style matching), causing the watcher to silently ignore files. Rule: always use `pathspec` for glob pattern matching in this project — never `fnmatch`.

### Filesystem event watchers (watchdog/FSEvents) are unreliable for this use case
macOS FSEvents silently drops events in certain conditions (temp directories, files created by subprocess). After debugging multiple missed-detection cases, we replaced watchdog with simple 5-second polling. The indexer already has hash-based change detection, so polling is just as effective and works identically on all platforms. Simpler, fewer dependencies, more reliable.

### ChromaDB's SharedSystemClient caches broken connections
ChromaDB's `PersistentClient` uses a singleton cache (`SharedSystemClient._identifier_to_system`) keyed by the persist directory path. If the first open fails mid-`start()` (e.g. due to database corruption), the broken `System` object stays in the cache. All subsequent `PersistentClient()` calls for the same path skip initialization entirely and reuse the dead connection, producing confusing "tenant not found" errors. Fix: call `SharedSystemClient.clear_system_cache()` before retrying. This is an internal API but the only way to force a clean retry within the same process.

### ChromaDB concurrent access causes database corruption
ChromaDB's embedded SQLite does not handle multiple writers safely. If the MCP server and CLI `pmem index` open the same `.memory/chroma/` directory simultaneously, the database can be left in a state that causes a Rust panic (`range start index N out of range for slice of length M`) on next open. Fix: exclusive file lock (`chroma.lock`) around all ChromaDB access. The lock is held for the lifetime of the `ChunkStore` instance and released via `close()`.

### The "Interrupted" cascade in Claude Code
When Claude Code enters an "Interrupted" state (from any cause — MCP failure, bash error, user interrupt), subsequent tool calls also fail with "Interrupted." The session becomes effectively unrecoverable. This is a Claude Code bug, not specific to pmem, but MCP server instability can trigger it. Updating to the latest Claude Code version helped.
