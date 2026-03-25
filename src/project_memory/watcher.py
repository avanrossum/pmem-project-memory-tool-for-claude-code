"""File watcher for automatic incremental reindexing on file changes."""

from __future__ import annotations

import fnmatch
import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from project_memory.config import ProjectConfig

LogCallback = Callable[[str, str], None]

DEBOUNCE_SECONDS = 2.0


def _matches_patterns(rel_path: str, patterns: list[str]) -> bool:
    """Check whether a relative path matches any of the given glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also check each path component for directory-level patterns like ".git/**"
        if fnmatch.fnmatch(rel_path + "/", pattern):
            return True
    return False


class _DebouncedHandler(FileSystemEventHandler):
    """Collects file events and triggers a debounced reindex."""

    def __init__(
        self,
        config: ProjectConfig,
        log: LogCallback,
    ) -> None:
        super().__init__()
        self._config = config
        self._log = log
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    # --- filtering -----------------------------------------------------------

    def _is_relevant(self, path: str) -> bool:
        """Return True if the path matches include patterns and not exclude patterns."""
        try:
            rel = str(Path(path).relative_to(self._config.project_root))
        except ValueError:
            return False

        include = self._config.indexing.include
        exclude = self._config.indexing.exclude

        if not _matches_patterns(rel, include):
            return False
        if _matches_patterns(rel, exclude):
            return False
        return True

    # --- event handling ------------------------------------------------------

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = str(event.src_path)
        if not self._is_relevant(src):
            return

        rel = str(Path(src).relative_to(self._config.project_root))
        self._log(rel, "file")

        with self._lock:
            self._pending.add(rel)
            # Reset the debounce timer
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        self._handle(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        self._handle(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename."""
        self._handle(event)

    # --- flush (runs on timer thread) ----------------------------------------

    def _flush(self) -> None:
        """Run incremental index for the batch of changed files."""
        with self._lock:
            batch = sorted(self._pending)
            self._pending.clear()
            self._timer = None

        if not batch:
            return

        self._log(f"Reindexing ({len(batch)} file(s) changed)...", "step")
        for f in batch:
            self._log(f"  {f}", "file")

        from project_memory.indexer import run_index

        try:
            result = run_index(self._config, force=False, dry_run=False, log=self._log)
            self._log(
                f"Indexed {result.files_indexed} files — "
                f"{result.chunks_added} added, {result.chunks_updated} updated, "
                f"{result.chunks_removed} removed "
                f"({result.duration_seconds:.1f}s)",
                "info",
            )
        except Exception as exc:
            self._log(f"Reindex failed: {exc}", "info")

    def cancel(self) -> None:
        """Cancel any pending debounce timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


def start_watcher(
    config: ProjectConfig,
    log: LogCallback | None = None,
) -> Observer:
    """Start a watchdog Observer that triggers incremental reindex on file changes.

    Returns the running Observer instance. Call observer.stop() and observer.join()
    to shut down cleanly.
    """
    if log is None:
        log = lambda msg, level: None  # noqa: E731

    handler = _DebouncedHandler(config, log)
    observer = Observer()
    observer.schedule(handler, str(config.project_root), recursive=True)
    observer.start()
    return observer


def run_watcher(
    config: ProjectConfig,
    log: LogCallback | None = None,
) -> None:
    """Run the file watcher in the foreground until interrupted.

    Blocks until KeyboardInterrupt, then shuts down cleanly.
    """
    if log is None:
        log = lambda msg, level: None  # noqa: E731

    log(f"Watching {config.project_root}", "step")
    log(f"Include: {', '.join(config.indexing.include)}", "info")
    log(f"Exclude: {', '.join(config.indexing.exclude)}", "info")
    log("Press Ctrl+C to stop.", "info")

    handler = _DebouncedHandler(config, log)
    observer = Observer()
    observer.schedule(handler, str(config.project_root), recursive=True)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(timeout=1)
    except KeyboardInterrupt:
        pass
    finally:
        handler.cancel()
        observer.stop()
        observer.join()
        log("Watcher stopped.", "step")
