"""MCP server exposing project memory tools to Claude Code."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from project_memory.config import load_config
from project_memory.indexer import get_stale_files, run_index, IndexState
from project_memory.query import query_memory, retrieve
from project_memory.store import ChunkStore

server = Server("project-memory")


def _get_config():
    """Load config from CWD, raising a readable error if not found."""
    return load_config()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available MCP tools."""
    return [
        Tool(
            name="memory_query",
            description=(
                "Query the project memory for information about past decisions, "
                "architecture, tasks, or any documented context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question",
                    },
                    "synthesize": {
                        "type": "boolean",
                        "description": "If true, synthesize an answer via LLM. If false, return raw chunks.",
                        "default": True,
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of chunks to retrieve",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="memory_search",
            description=(
                "Search project memory and return matching chunks with source locations. "
                "Use when you want relevant documentation without synthesis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="memory_status",
            description="Return the current state of the project memory index.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="memory_reindex",
            description=(
                "Trigger a reindex of the project memory. Use after significant "
                "documentation changes or when memory_status shows stale files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "If true, re-embeds all files regardless of change state.",
                        "default": False,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle an MCP tool call."""
    try:
        config = _get_config()

        if name == "memory_query":
            result = query_memory(
                question=arguments["question"],
                config=config,
                synthesize_answer=arguments.get("synthesize", True),
                top_k=arguments.get("top_k"),
            )
            text = result["answer"]
            if result["sources"]:
                text += "\n\nSources:\n" + "\n".join(
                    f"- {s['source_file']} ({s['heading_path']})"
                    for s in result["sources"]
                )
            return [TextContent(type="text", text=text)]

        elif name == "memory_search":
            chunks = retrieve(arguments["query"], config)
            if not chunks:
                return [TextContent(type="text", text="No results found.")]
            text = "\n\n---\n\n".join(
                f"**{c['source_file']}** ({c['heading_path']}) "
                f"[score: {c['relevance_score']}]\n\n{c['text']}"
                for c in chunks
            )
            return [TextContent(type="text", text=text)]

        elif name == "memory_status":
            store = ChunkStore(config)
            stale = get_stale_files(config)
            state_path = config.memory_dir / "index_state.json"
            state = IndexState.load(state_path)
            last_indexed = max(
                (f.get("last_indexed", "") for f in state.files.values()),
                default="never",
            )
            text = (
                f"Project: {config.project_name}\n"
                f"Indexed files: {len(state.files)}\n"
                f"Total chunks: {store.count}\n"
                f"Last indexed: {last_indexed}\n"
                f"Stale files: {len(stale)}\n"
                f"Embedding model: {config.embedding.model}\n"
                f"LLM enabled: {config.llm.enabled}"
            )
            if stale:
                text += "\n\nStale files:\n" + "\n".join(f"- {f}" for f in stale)
            return [TextContent(type="text", text=text)]

        elif name == "memory_reindex":
            force = arguments.get("force", False)
            result = run_index(config, force=force)
            text = (
                f"Reindex complete.\n"
                f"Files indexed: {result.files_indexed}\n"
                f"Chunks added: {result.chunks_added}\n"
                f"Chunks updated: {result.chunks_updated}\n"
                f"Chunks removed: {result.chunks_removed}\n"
                f"Duration: {result.duration_seconds:.1f}s"
            )
            return [TextContent(type="text", text=text)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


async def run_server() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
