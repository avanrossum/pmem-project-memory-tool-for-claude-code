# Recommended CLAUDE.md Addition

Copy this section into any project's `CLAUDE.md` that uses pmem:

---

```markdown
## Project Memory

This project has a local RAG memory index via `pmem`. The `memory_query` and `memory_search` MCP tools are available BUT:

**ONLY use memory tools when the user explicitly asks** — e.g. "search memory for X", "what does memory say about X", or "check project memory." NEVER proactively call memory tools during normal work. They are slow (1-2 seconds per call) and will degrade the session if overused.

When explicitly asked, memory is good for:
- Past decisions, context, or rationale ("why did we do X?")
- Historical task context or outcomes
- Documented gotchas or lessons learned

Do NOT use memory tools for: reading specific known files, checking current code state, or anything derivable from `git log` or the filesystem.
```
