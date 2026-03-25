# Configuration Reference

Full reference for `.memory/config.json`.

---

## `project_name`
**Type:** string
**Required:** yes

Human-readable name for this project. Used in MCP responses and status output.

---

## `embedding`

### `endpoint`
**Type:** string — URL
**Default:** `http://localhost:11434`

Base URL of the embedding server. Default is Ollama's local address.

### `model`
**Type:** string
**Default:** `nomic-embed-text`

Embedding model name. Must be available at the specified endpoint.

Tested models:
- `nomic-embed-text` — recommended, runs on all machines via Ollama
- `mxbai-embed-large` — higher quality, larger footprint
- Any model available via LMStudio's embedding endpoint

### `provider`
**Type:** `"ollama"` | `"openai_compatible"`
**Default:** `"ollama"`

Controls the request format sent to the embedding endpoint. Use `openai_compatible` for LMStudio or any server implementing `/v1/embeddings`.

---

## `llm`

### `enabled`
**Type:** boolean
**Default:** `true`

If false, `memory_query` with `synthesize: true` returns raw chunks instead of a synthesized answer. Useful on low-resource machines or when you only need retrieval.

### `endpoint`
**Type:** string — URL
**Default:** `http://localhost:1234/v1`

Base URL of the LLM server. Default is LMStudio's local OpenAI-compatible endpoint.

For remote Mac Studio: `http://mac-studio.local:1234/v1` or your Cloudflare tunnel URL.

### `model`
**Type:** string
**Default:** `local-model`

Model identifier sent to the LLM endpoint. For LMStudio, this is typically the model's display name. For Ollama's OpenAI endpoint: e.g. `llama3.1:70b`.

### `provider`
**Type:** `"openai_compatible"`

Currently only OpenAI-compatible endpoints are supported (covers LMStudio, Ollama, real OpenAI, and most local inference servers).

---

## `indexing`

### `include`
**Type:** array of glob patterns
**Default:** `["**/*.md", "**/*.txt"]`

Files matching any of these patterns are indexed. Patterns are relative to the project root.

### `exclude`
**Type:** array of glob patterns
**Default:** `[".memory/**", ".git/**", "node_modules/**", "*.lock"]`

Files matching any of these patterns are excluded even if they match an `include` pattern.

### `chunk_size`
**Type:** integer
**Default:** `400`

Target chunk size in tokens (approximate). Chunks smaller than this are kept whole; larger sections are split with overlap.

### `chunk_overlap`
**Type:** integer
**Default:** `80`

Token overlap between adjacent chunks from the same section. Helps preserve context at chunk boundaries.

### `split_on_headers`
**Type:** boolean
**Default:** `true`

When true, markdown files are first split at H1/H2/H3 boundaries, then by size. Recommended — preserves semantic units. Disable only if your markdown doesn't use headers.

---

## `query`

### `top_k`
**Type:** integer
**Default:** `8`

Number of chunks to retrieve per query. Higher values give more context but increase LLM prompt size. 6–10 is usually right.

### `auto_reindex_on_query`
**Type:** boolean
**Default:** `true`

When true, the MCP server checks for changed files before answering any query and re-embeds them inline. Adds ~100–200ms overhead but ensures the answer reflects the current state of your docs. Set to false if you prefer explicit control via `pmem index`.

---

## Example: Remote LLM on Mac Studio

```json
{
  "project_name": "haggai-salesforce",
  "embedding": {
    "endpoint": "http://localhost:11434",
    "model": "nomic-embed-text",
    "provider": "ollama"
  },
  "llm": {
    "endpoint": "https://your-tunnel.trycloudflare.com/v1",
    "model": "llama-3.1-70b",
    "provider": "openai_compatible",
    "enabled": true
  },
  "indexing": {
    "include": ["**/*.md"],
    "exclude": [".memory/**", ".git/**"],
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

## Example: Lightweight (embedding only, no LLM)

```json
{
  "project_name": "my-project",
  "embedding": {
    "endpoint": "http://localhost:11434",
    "model": "nomic-embed-text",
    "provider": "ollama"
  },
  "llm": {
    "enabled": false
  },
  "indexing": {
    "include": ["**/*.md"],
    "exclude": [".memory/**", ".git/**"],
    "chunk_size": 400,
    "chunk_overlap": 80,
    "split_on_headers": true
  },
  "query": {
    "top_k": 8,
    "auto_reindex_on_query": false
  }
}
```
