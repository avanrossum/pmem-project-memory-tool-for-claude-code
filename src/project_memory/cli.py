"""CLI entry point for the pmem command."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import click

from project_memory.config import create_default_config, load_config, find_memory_root


@click.group()
def cli() -> None:
    """pmem — Project Memory Tool for Claude Code."""
    pass


@cli.command()
def init() -> None:
    """Initialize project memory in the current directory."""
    project_root = Path.cwd()
    config_path = project_root / ".memory" / "config.json"

    if config_path.exists():
        click.echo(f"Memory already initialized at {config_path}")
        click.echo("Edit .memory/config.json to update configuration.")
        return

    config_path = create_default_config(project_root)
    click.echo(f"Created {config_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Edit .memory/config.json to set your embedding/LLM endpoints")
    click.echo("  2. Add to .gitignore:")
    click.echo("       .memory/chroma/")
    click.echo("       .memory/index_state.json")
    click.echo("  3. Add to ~/.claude/settings.json under mcpServers:")
    click.echo()
    click.echo('     "project-memory": {')
    click.echo('       "command": "pmem",')
    click.echo('       "args": ["serve"]')
    click.echo("     }")
    click.echo()
    click.echo("  4. Run: pmem index")


@cli.command()
@click.option("--force", is_flag=True, help="Re-embed all files regardless of change state.")
@click.option("--dry-run", is_flag=True, help="Show what would be indexed without doing it.")
def index(force: bool, dry_run: bool) -> None:
    """Run incremental index of project files."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    from project_memory.indexer import run_index

    if dry_run:
        click.echo(click.style("  DRY RUN", fg="yellow", bold=True) + " — no changes will be made.")

    def _log(msg: str, level: str = "info") -> None:
        if level == "step":
            click.echo(click.style(f"  >> {msg}", fg="cyan", bold=True))
        elif level == "file":
            click.echo(click.style(f"     {msg}", fg="white", dim=True))
        elif level == "count":
            click.echo(click.style(f"     {msg}", fg="yellow"))
        elif level == "progress":
            click.echo(click.style(f"     {msg}", fg="magenta"))
        else:
            click.echo(click.style(f"     {msg}", fg="white"))

    click.echo()
    click.echo(click.style("  pmem index", fg="green", bold=True) + click.style(f"  {config.project_name}", fg="white", dim=True))
    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))

    try:
        result = run_index(config, force=force, dry_run=dry_run, log=_log)
    except Exception as e:
        click.echo()
        click.echo(click.style(f"  ERROR: {e}", fg="red", bold=True))
        sys.exit(1)

    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))
    click.echo(
        click.style("  Done ", fg="green", bold=True)
        + click.style(f"in {result.duration_seconds:.1f}s", fg="white", dim=True)
    )
    click.echo(
        click.style(f"     {result.files_indexed}", fg="cyan", bold=True)
        + click.style(" files  ", fg="white")
        + click.style(f"{result.chunks_added}", fg="cyan", bold=True)
        + click.style(" added  ", fg="white")
        + click.style(f"{result.chunks_updated}", fg="yellow", bold=True)
        + click.style(" updated  ", fg="white")
        + click.style(f"{result.chunks_removed}", fg="red", bold=True)
        + click.style(" removed", fg="white")
    )
    click.echo()


@cli.command()
@click.argument("question")
@click.option("--no-llm", is_flag=True, help="Return raw chunks without LLM synthesis.")
@click.option("--top-k", type=int, default=None, help="Number of chunks to retrieve.")
def query(question: str, no_llm: bool, top_k: int | None) -> None:
    """Query project memory with a natural language question."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    from project_memory.query import query_memory

    try:
        result = query_memory(
            question=question,
            config=config,
            synthesize_answer=not no_llm,
            top_k=top_k,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(result["answer"])
    if result["sources"]:
        click.echo()
        click.echo("Sources:")
        for s in result["sources"]:
            click.echo(f"  - {s['source_file']} ({s['heading_path']})")


@cli.command()
def status() -> None:
    """Show the current state of the project memory index."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    from project_memory.indexer import get_stale_files, IndexState
    from project_memory.store import ChunkStore

    store = ChunkStore(config)
    state_path = config.memory_dir / "index_state.json"
    state = IndexState.load(state_path)
    stale = get_stale_files(config)

    last_indexed = max(
        (f.get("last_indexed", "") for f in state.files.values()),
        default="never",
    )

    click.echo(f"Project:         {config.project_name}")
    click.echo(f"Indexed files:   {len(state.files)}")
    click.echo(f"Total chunks:    {store.count}")
    click.echo(f"Last indexed:    {last_indexed}")
    click.echo(f"Stale files:     {len(stale)}")
    click.echo(f"Embedding model: {config.embedding.model}")
    click.echo(f"LLM enabled:     {config.llm.enabled}")

    if stale:
        click.echo()
        click.echo("Stale files:")
        for f in stale:
            click.echo(f"  - {f}")


@cli.command()
def serve() -> None:
    """Start the MCP server (used by Claude Code)."""
    from project_memory.mcp_server import run_server

    asyncio.run(run_server())


@cli.command()
@click.argument("pattern")
def exclude(pattern: str) -> None:
    """Add a glob pattern to the exclude list.

    Examples:
        pmem exclude "snapshots/**"
        pmem exclude "*.csv"
        pmem exclude "archive/old-reports/**"
    """
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    config_path = cfg.memory_dir / "config.json"
    data = json.loads(config_path.read_text())
    excludes = data.get("indexing", {}).get("exclude", [])

    if pattern in excludes:
        click.echo(click.style(f"  Already excluded: ", fg="yellow") + pattern)
        return

    excludes.append(pattern)
    data.setdefault("indexing", {})["exclude"] = excludes
    config_path.write_text(json.dumps(data, indent=2) + "\n")

    click.echo(click.style("  Added: ", fg="green", bold=True) + pattern)
    click.echo(click.style("  Excludes: ", fg="white", dim=True) + ", ".join(excludes))


@cli.command()
@click.argument("pattern")
def include(pattern: str) -> None:
    """Add a glob pattern to the include list.

    Examples:
        pmem include "**/*.py"
        pmem include "docs/**/*.rst"
    """
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    config_path = cfg.memory_dir / "config.json"
    data = json.loads(config_path.read_text())
    includes = data.get("indexing", {}).get("include", [])

    if pattern in includes:
        click.echo(click.style(f"  Already included: ", fg="yellow") + pattern)
        return

    includes.append(pattern)
    data.setdefault("indexing", {})["include"] = includes
    config_path.write_text(json.dumps(data, indent=2) + "\n")

    click.echo(click.style("  Added: ", fg="green", bold=True) + pattern)
    click.echo(click.style("  Includes: ", fg="white", dim=True) + ", ".join(includes))


@cli.command()
@click.option("--edit", is_flag=True, help="Open config.json in $EDITOR.")
def config(edit: bool) -> None:
    """Show or edit the current project configuration."""
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    config_path = cfg.memory_dir / "config.json"

    if edit:
        editor = subprocess.os.environ.get("EDITOR", "vim")
        subprocess.run([editor, str(config_path)])
    else:
        click.echo(config_path.read_text())
