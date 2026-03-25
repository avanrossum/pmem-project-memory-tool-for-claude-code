"""Polling-based watcher for automatic incremental reindexing on file changes.

Instead of relying on OS-level filesystem events (FSEvents, inotify, etc.),
this polls on a configurable interval and uses the indexer's hash-based change
detection to find and reindex modified files.  Works reliably on all platforms.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from project_memory.config import ProjectConfig

LogCallback = Callable[[str, str], None]

DEFAULT_POLL_SECONDS = 5


def _run_poll(config: ProjectConfig, log: LogCallback) -> None:
    """Run a single incremental index pass, logging the result."""
    from project_memory.indexer import run_index

    try:
        result = run_index(config, force=False, dry_run=False, log=log)
        if result.files_indexed > 0:
            log(
                f"Indexed {result.files_indexed} files — "
                f"{result.chunks_added} added, {result.chunks_updated} updated, "
                f"{result.chunks_removed} removed "
                f"({result.duration_seconds:.1f}s)",
                "step",
            )
    except Exception as exc:
        log(f"Reindex failed: {exc}", "info")


class PollingWatcher:
    """Periodically polls for file changes and triggers incremental reindex."""

    def __init__(
        self,
        config: ProjectConfig,
        log: LogCallback,
        poll_interval: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        self._config = config
        self._log = log
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _poll_loop(self) -> None:
        """Run the polling loop until stop is requested."""
        while not self._stop_event.is_set():
            _run_poll(self._config, self._log)
            self._stop_event.wait(timeout=self._poll_interval)

    def start(self) -> None:
        """Start polling in a background thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the polling thread to stop."""
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the polling thread to finish."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        """Return True if the polling thread is running."""
        return self._thread is not None and self._thread.is_alive()


def start_watcher(
    config: ProjectConfig,
    log: LogCallback | None = None,
    poll_interval: float = DEFAULT_POLL_SECONDS,
) -> PollingWatcher:
    """Start a polling watcher that triggers incremental reindex on file changes.

    Returns the running PollingWatcher instance.  Call watcher.stop() and
    watcher.join() to shut down cleanly.
    """
    if log is None:
        log = lambda msg, level: None  # noqa: E731

    watcher = PollingWatcher(config, log, poll_interval)
    watcher.start()
    return watcher


def run_watcher(
    config: ProjectConfig,
    log: LogCallback | None = None,
    poll_interval: float = DEFAULT_POLL_SECONDS,
) -> None:
    """Run the file watcher in the foreground until interrupted.

    Blocks until KeyboardInterrupt, then shuts down cleanly.
    """
    if log is None:
        log = lambda msg, level: None  # noqa: E731

    log(f"Watching {config.project_root} (polling every {poll_interval}s)", "step")
    log(f"Include: {', '.join(config.indexing.include)}", "info")
    log(f"Exclude: {', '.join(config.indexing.exclude)}", "info")
    log("Press Ctrl+C to stop.", "info")

    watcher = PollingWatcher(config, log, poll_interval)
    watcher.start()

    try:
        while watcher.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        watcher.join(timeout=5)
        log("Watcher stopped.", "step")
