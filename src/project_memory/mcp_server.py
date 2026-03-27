"""MCP server exposing project memory tools to Claude Code."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

# Suppress all warnings — stray output to stderr can corrupt the MCP stdio protocol
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Log to file so it doesn't interfere with MCP stdio protocol.
# View with: tail -f ~/.pmem-mcp.log
_log_handler = logging.handlers.RotatingFileHandler(
    str(Path.home() / ".pmem-mcp.log"), mode="a", maxBytes=5_000_000, backupCount=2
)
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger = logging.getLogger("pmem-mcp")
logger.addHandler(_log_handler)
logger.setLevel(logging.INFO)

server = Server("project-memory")

# Timeout for any blocking operation (seconds)
TOOL_TIMEOUT = 30


def _get_config():
    """Load config from CWD, raising a readable error if not found."""
    from project_memory.config import load_config

    return load_config()


def _do_query(arguments: dict[str, Any]) -> str:
    """Run memory_query synchronously (called via to_thread)."""
    from project_memory.query import query_memory

    config = _get_config()
    config.query.auto_reindex_on_query = False

    result = query_memory(
        question=arguments["question"],
        config=config,
        synthesize_answer=arguments.get("synthesize", False),
        top_k=arguments.get("top_k"),
    )
    text = result["answer"]
    if result["sources"]:
        text += "\n\nSources:\n" + "\n".join(
            f"- {s['source_file']} ({s['heading_path']})"
            for s in result["sources"]
        )
    return text


def _do_search(arguments: dict[str, Any]) -> str:
    """Run memory_search synchronously (called via to_thread)."""
    from project_memory.query import retrieve

    config = _get_config()
    config.query.auto_reindex_on_query = False

    chunks = retrieve(arguments["query"], config)
    if not chunks:
        return "No results found."
    return "\n\n---\n\n".join(
        f"**{c['source_file']}** ({c['heading_path']}) "
        f"[score: {c['relevance_score']}]\n\n{c['text']}"
        for c in chunks
    )


def _do_status() -> str:
    """Run memory_status synchronously (called via to_thread)."""
    from project_memory.indexer import get_stale_files, IndexState

    config = _get_config()
    state_path = config.memory_dir / "index_state.json"
    state = IndexState.load(state_path)
    stale = get_stale_files(config)
    last_indexed = max(
        (f.get("last_indexed", "") for f in state.files.values()),
        default="never",
    )
    total_chunks = sum(
        len(f.get("chunk_ids", [])) for f in state.files.values()
    )
    text = (
        f"Project: {config.project_name}\n"
        f"Indexed files: {len(state.files)}\n"
        f"Total chunks: {total_chunks}\n"
        f"Last indexed: {last_indexed}\n"
        f"Stale files: {len(stale)}\n"
        f"Embedding model: {config.embedding.model}\n"
        f"LLM enabled: {config.llm.enabled}"
    )
    if stale:
        text += "\n\nStale files:\n" + "\n".join(f"- {f}" for f in stale)
    return text


def _do_reindex(arguments: dict[str, Any]) -> str:
    """Run memory_reindex synchronously (called via to_thread)."""
    from project_memory.indexer import run_index

    config = _get_config()
    force = arguments.get("force", False)
    result = run_index(config, force=force)
    return (
        f"Reindex complete.\n"
        f"Files indexed: {result.files_indexed}\n"
        f"Chunks added: {result.chunks_added}\n"
        f"Chunks updated: {result.chunks_replaced}\n"
        f"Chunks removed: {result.chunks_removed}\n"
        f"Duration: {result.duration_seconds:.1f}s"
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available MCP tools."""
    logger.info("LIST_TOOLS called")
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
                        "description": "If true, synthesize via local LLM (requires LLM endpoint). Defaults to false — returns raw chunks for Claude to interpret directly.",
                        "default": False,
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


_HANDLERS = {
    "memory_query": _do_query,
    "memory_search": _do_search,
    "memory_status": lambda args: _do_status(),
    "memory_reindex": _do_reindex,
}


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle an MCP tool call.

    All blocking work runs in a thread pool so the async event loop stays
    responsive — prevents the MCP protocol connection from breaking.
    """
    logger.info(f"CALL {name} args={arguments}")
    start = time.time()

    handler = _HANDLERS.get(name)
    if handler is None:
        logger.info(f"UNKNOWN {name}")
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(handler, arguments),
            timeout=TOOL_TIMEOUT,
        )
        elapsed = time.time() - start
        logger.info(f"OK {name} {elapsed:.1f}s ({len(text)} chars)")

        # Append update notice if available (non-blocking, best-effort)
        try:
            from project_memory.update_check import check_for_update

            config = _get_config()
            notice = check_for_update(channel=config.update_channel)
            if notice:
                text += notice
        except Exception:
            pass  # never let update check break a tool call

        return [TextContent(type="text", text=text)]
    except asyncio.TimeoutError:
        logger.error(f"TIMEOUT {name} after {TOOL_TIMEOUT}s")
        return [TextContent(type="text", text=f"Error: {name} timed out after {TOOL_TIMEOUT}s")]
    except FileNotFoundError as e:
        logger.error(f"NOT_FOUND {name}: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"ERROR {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


async def run_server() -> None:
    """Run the MCP server over stdio."""
    import atexit
    import signal

    logger.info("SERVER_START pid=%d", os.getpid())
    atexit.register(lambda: logger.info("SERVER_EXIT atexit"))

    def _signal_handler(signum, frame):
        logger.info(f"SERVER_SIGNAL {signal.Signals(signum).name}")
        # Re-raise as the default handler would — allows the server to be killed
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _signal_handler)

    async def _heartbeat():
        """Log a heartbeat every 60s so we can see if the server is alive but idle."""
        while True:
            await asyncio.sleep(60)
            logger.info("SERVER_HEARTBEAT pid=%d", os.getpid())

    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("SERVER_STDIO_OPEN")
            heartbeat_task = asyncio.create_task(_heartbeat())
            try:
                await server.run(read_stream, write_stream, server.create_initialization_options())
            finally:
                heartbeat_task.cancel()
            logger.info("SERVER_RUN_EXITED")
    except asyncio.CancelledError:
        logger.info("SERVER_CANCELLED")
    except Exception as e:
        logger.error(f"SERVER_CRASH {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        logger.info("SERVER_SHUTDOWN")
