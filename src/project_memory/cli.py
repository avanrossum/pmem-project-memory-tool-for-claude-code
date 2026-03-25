"""CLI entry point for the pmem command."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import click

from project_memory.config import (
    create_default_config,
    create_global_config,
    load_config,
    load_global_config,
    find_memory_root,
    GLOBAL_CONFIG_PATH,
)


@click.group()
def cli() -> None:
    """pmem — Project Memory Tool for Claude Code."""
    pass


CLAUDE_MD_SNIPPET = """

## Project Memory

This project has a local RAG memory index via `pmem`. Use the `memory_query` MCP tool when:
- Looking for past decisions, context, or rationale ("why did we do X?")
- Searching for historical task context or outcomes
- Finding documented gotchas or lessons learned

Do NOT use memory_query for: reading specific known files, checking current code state, or anything derivable from `git log`. The index updates at session start (`/welcome`) and session end (`/sleep`).

If results seem stale, run `memory_reindex` to refresh.
"""

GITIGNORE_ENTRIES = [".memory/chroma/", ".memory/index_state.json"]
GITIGNORE_COMMENT = "# Project memory (generated)"


def _update_gitignore(project_root: Path) -> str | None:
    """Ensure .gitignore contains project memory entries.

    Returns a description of what was done, or None if nothing changed.
    """
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        missing = [e for e in GITIGNORE_ENTRIES if e not in content]
        if not missing:
            return None
        lines = f"\n{GITIGNORE_COMMENT}\n" + "\n".join(missing) + "\n"
        with open(gitignore_path, "a") as f:
            f.write(lines)
        return f"Appended {', '.join(missing)} to .gitignore"
    else:
        lines = f"{GITIGNORE_COMMENT}\n" + "\n".join(GITIGNORE_ENTRIES) + "\n"
        gitignore_path.write_text(lines)
        return "Created .gitignore with memory entries"


def _update_claude_md(project_root: Path) -> str | None:
    """Append project memory snippet to CLAUDE.md if it exists and doesn't already have it.

    Returns a description of what was done, or None if nothing changed.
    """
    claude_md_path = project_root / "CLAUDE.md"
    if not claude_md_path.exists():
        return None
    content = claude_md_path.read_text()
    if "Project Memory" in content or "memory_query" in content:
        return None
    with open(claude_md_path, "a") as f:
        f.write(CLAUDE_MD_SNIPPET)
    return "Appended Project Memory section to CLAUDE.md"


@cli.command()
def init() -> None:
    """Initialize project memory in the current directory."""
    project_root = Path.cwd()
    config_path = project_root / ".memory" / "config.json"

    if config_path.exists():
        click.echo(click.style("  Already initialized ", fg="yellow", bold=True)
                    + click.style(str(config_path), fg="white", dim=True))
        click.echo(click.style("  Edit .memory/config.json to update configuration.", fg="white", dim=True))
        return

    click.echo()
    click.echo(click.style("  pmem init", fg="green", bold=True))
    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))

    # Step 1: Create config
    config_path = create_default_config(project_root)
    click.echo(click.style("  >> Created config", fg="cyan", bold=True)
               + click.style(f"  {config_path}", fg="white", dim=True))

    # Step 2: Update .gitignore
    gitignore_result = _update_gitignore(project_root)
    if gitignore_result:
        click.echo(click.style("  >> .gitignore  ", fg="cyan", bold=True)
                    + click.style(gitignore_result, fg="white", dim=True))

    # Step 3: Update CLAUDE.md
    claude_md_result = _update_claude_md(project_root)
    if claude_md_result:
        click.echo(click.style("  >> CLAUDE.md  ", fg="cyan", bold=True)
                    + click.style(claude_md_result, fg="white", dim=True))

    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))
    click.echo(click.style("  Done ", fg="green", bold=True))
    # Detect the full path to pmem for the MCP snippet — pyenv shims
    # and other version managers aren't available in Claude Code's subprocess env.
    import shutil
    pmem_path = shutil.which("pmem") or "pmem"

    click.echo()
    click.echo(click.style("  Next steps:", fg="cyan", bold=True))
    click.echo(click.style("  1. ", fg="white") + "Edit .memory/config.json to set your embedding/LLM endpoints")
    click.echo(click.style("  2. ", fg="white") + "Add to ~/.claude.json (or .mcp.json) under mcpServers:")
    click.echo()
    click.echo(click.style('     "project-memory": {', fg="white", dim=True))
    click.echo(click.style(f'       "command": "{pmem_path}",', fg="white", dim=True))
    click.echo(click.style('       "args": ["serve"]', fg="white", dim=True))
    click.echo(click.style("     }", fg="white", dim=True))
    click.echo()
    click.echo(click.style("  3. ", fg="white") + "Run: " + click.style("pmem install-skills", fg="cyan", bold=True))
    click.echo(click.style("  4. ", fg="white") + "Run: " + click.style("pmem index", fg="cyan", bold=True))


@cli.command()
@click.option("--force", is_flag=True, help="Re-embed all files regardless of change state.")
@click.option("--dry-run", is_flag=True, help="Show what would be indexed without doing it.")
def index(force: bool, dry_run: bool) -> None:
    """Run incremental index of project files.

    Note: If Claude Code is running with the project-memory MCP server active,
    use the memory_reindex MCP tool instead. Running pmem index from the terminal
    while Claude Code is active can cause database lock conflicts.
    """
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
    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("  Interrupted — index state saved.", fg="yellow", bold=True))
        sys.exit(130)
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
def watch() -> None:
    """Watch for file changes and reindex automatically.

    Note: Do not run pmem watch while Claude Code is active on the same project.
    The watcher and MCP server can conflict on the ChromaDB database. Use /welcome
    and /sleep skills instead when working with Claude Code.
    """
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    from project_memory.watcher import run_watcher

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
    click.echo(
        click.style("  pmem watch", fg="green", bold=True)
        + click.style(f"  {cfg.project_name}", fg="white", dim=True)
    )
    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))

    run_watcher(cfg, log=_log)

    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))
    click.echo()


@cli.command("config")
@click.option("--edit", is_flag=True, help="Open config.json in $EDITOR.")
@click.option("--global", "show_global", is_flag=True, help="Show global config path and contents.")
@click.option("--init-global", is_flag=True, help="Create a minimal global config at ~/.config/pmem/config.json.")
def config_cmd(edit: bool, show_global: bool, init_global: bool) -> None:
    """Show or edit the current project configuration."""
    if init_global:
        if GLOBAL_CONFIG_PATH.is_file():
            click.echo(f"Global config already exists at {GLOBAL_CONFIG_PATH}")
            click.echo(GLOBAL_CONFIG_PATH.read_text())
        else:
            path = create_global_config()
            click.echo(f"Created global config at {path}")
            click.echo(path.read_text())
        return

    if show_global:
        click.echo(f"Global config path: {GLOBAL_CONFIG_PATH}")
        click.echo()
        if GLOBAL_CONFIG_PATH.is_file():
            click.echo(GLOBAL_CONFIG_PATH.read_text())
        else:
            click.echo("Global config does not exist yet. Run 'pmem config --init-global' to create it.")
        return

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


def _find_skills_dir() -> Path | None:
    """Find the skills directory shipped with pmem."""
    # Check relative to this file (works for editable installs and normal installs)
    pkg_dir = Path(__file__).resolve().parent
    candidates = [
        pkg_dir.parent.parent / "skills",  # editable install: src/project_memory/../../skills
        pkg_dir / "skills",                 # bundled install
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "welcome.md").exists():
            return candidate
    return None


SKILL_FILES = ["welcome.md", "sleep.md", "reindex.md"]


@cli.command("install-skills")
@click.option("--link", is_flag=True, help="Symlink instead of copy (not recommended on Windows).")
def install_skills(link: bool) -> None:
    """Install Claude Code slash command skills (/welcome, /sleep, /reindex)."""
    skills_src = _find_skills_dir()
    if skills_src is None:
        click.echo(click.style("  ERROR: ", fg="red", bold=True)
                    + "Could not find skills directory. Is pmem installed correctly?")
        sys.exit(1)

    commands_dir = Path.home() / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    click.echo()
    click.echo(click.style("  pmem install-skills", fg="green", bold=True))
    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))

    for name in SKILL_FILES:
        src = skills_src / name
        dest = commands_dir / name

        if not src.exists():
            continue

        # Remove existing file/symlink before installing
        if dest.exists() or dest.is_symlink():
            dest.unlink()

        if link:
            dest.symlink_to(src)
            action = "linked"
        else:
            import shutil
            shutil.copy2(src, dest)
            action = "copied"

        skill_name = name.replace(".md", "")
        click.echo(
            click.style(f"  >> /{skill_name}", fg="cyan", bold=True)
            + click.style(f"  {action} to {dest}", fg="white", dim=True)
        )

    click.echo(click.style("  " + "─" * 40, fg="white", dim=True))
    click.echo(click.style("  Done ", fg="green", bold=True)
               + click.style("— restart Claude Code to use the new skills", fg="white", dim=True))
    click.echo()
