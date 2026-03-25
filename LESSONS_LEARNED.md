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
