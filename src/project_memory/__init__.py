"""Project Memory Tool — local-first RAG memory layer for Claude Code projects."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("project-memory-tool")
except PackageNotFoundError:
    __version__ = "0.0.0"  # not installed as a package
