# Recommended CLAUDE.md Addition

Copy this section into any project's `CLAUDE.md` that uses pmem:

---

```markdown
## Project Memory

This project has a local RAG memory index via `pmem`. Use the `memory_query` MCP tool when:
- Looking for past decisions, context, or rationale ("why did we do X?")
- Searching for historical task context or outcomes
- Finding documented gotchas or lessons learned

Do NOT use memory_query for: reading specific known files, checking current code state, or anything derivable from `git log`. The index updates at session start (`/welcome`) and session end (`/sleep`), so it may be slightly behind mid-session.

If results seem stale, run `memory_reindex` to refresh.
```
