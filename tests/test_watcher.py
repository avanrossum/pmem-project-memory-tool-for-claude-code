"""Tests for the polling-based file watcher module."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from project_memory.config import IndexingConfig, ProjectConfig
from project_memory.watcher import (
    DEFAULT_POLL_SECONDS,
    PollingWatcher,
    _run_poll,
    start_watcher,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, include=None, exclude=None) -> ProjectConfig:
    """Create a minimal ProjectConfig rooted at tmp_path."""
    return ProjectConfig(
        project_name="test",
        indexing=IndexingConfig(
            include=include or ["**/*.md", "**/*.txt"],
            exclude=exclude or [".memory/**", ".git/**"],
        ),
        project_root=tmp_path,
        memory_dir=tmp_path / ".memory",
    )


def _mock_index_result(**overrides):
    """Create a mock IndexResult with sensible defaults."""
    defaults = dict(
        files_indexed=0, chunks_added=0, chunks_replaced=0,
        chunks_removed=0, duration_seconds=0.1,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# _run_poll
# ---------------------------------------------------------------------------

class TestRunPoll:
    def test_logs_when_files_indexed(self, tmp_path):
        cfg = _make_config(tmp_path)
        log = MagicMock()

        with patch("project_memory.indexer.run_index") as mock_index:
            mock_index.return_value = _mock_index_result(
                files_indexed=2, chunks_added=5,
            )
            _run_poll(cfg, log)

            mock_index.assert_called_once()
            step_logs = [c for c in log.call_args_list if c[0][1] == "step"]
            assert any("Indexed 2 files" in c[0][0] for c in step_logs)

    def test_silent_when_nothing_changed(self, tmp_path):
        cfg = _make_config(tmp_path)
        log = MagicMock()

        with patch("project_memory.indexer.run_index") as mock_index:
            mock_index.return_value = _mock_index_result(files_indexed=0)
            _run_poll(cfg, log)

            # No "Indexed" log when nothing changed
            step_logs = [c for c in log.call_args_list if c[0][1] == "step"]
            assert not any("Indexed" in c[0][0] for c in step_logs)

    def test_logs_error_on_failure(self, tmp_path):
        cfg = _make_config(tmp_path)
        log = MagicMock()

        with patch("project_memory.indexer.run_index", side_effect=RuntimeError("boom")):
            _run_poll(cfg, log)

            info_logs = [c for c in log.call_args_list if c[0][1] == "info"]
            assert any("Reindex failed: boom" in c[0][0] for c in info_logs)


# ---------------------------------------------------------------------------
# PollingWatcher lifecycle
# ---------------------------------------------------------------------------

class TestPollingWatcher:
    def test_starts_and_stops(self, tmp_path):
        cfg = _make_config(tmp_path)

        with patch("project_memory.indexer.run_index", return_value=_mock_index_result()):
            watcher = PollingWatcher(cfg, log=MagicMock(), poll_interval=0.1)
            watcher.start()

            assert watcher.is_alive()

            watcher.stop()
            watcher.join(timeout=5)

            assert not watcher.is_alive()

    def test_polls_repeatedly(self, tmp_path):
        """Watcher should call run_index multiple times over several intervals."""
        cfg = _make_config(tmp_path)
        call_count = 0
        enough_calls = threading.Event()

        with patch("project_memory.indexer.run_index") as mock_index:
            mock_index.return_value = _mock_index_result()

            def _counting_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    enough_calls.set()
                return _mock_index_result()

            mock_index.side_effect = _counting_side_effect

            watcher = PollingWatcher(cfg, log=MagicMock(), poll_interval=0.1)
            watcher.start()

            assert enough_calls.wait(timeout=5), f"Only got {call_count} polls"

            watcher.stop()
            watcher.join(timeout=5)

            assert call_count >= 3

    def test_stop_interrupts_sleep(self, tmp_path):
        """Stopping mid-poll should not block for the full interval."""
        cfg = _make_config(tmp_path)

        with patch("project_memory.indexer.run_index", return_value=_mock_index_result()):
            watcher = PollingWatcher(cfg, log=MagicMock(), poll_interval=60)
            watcher.start()

            time.sleep(0.2)  # let it start
            start = time.monotonic()
            watcher.stop()
            watcher.join(timeout=5)
            elapsed = time.monotonic() - start

            # Should stop well under the 60s poll interval
            assert elapsed < 5


# ---------------------------------------------------------------------------
# start_watcher convenience function
# ---------------------------------------------------------------------------

class TestStartWatcher:
    def test_returns_running_watcher(self, tmp_path):
        cfg = _make_config(tmp_path)

        with patch("project_memory.indexer.run_index", return_value=_mock_index_result()):
            watcher = start_watcher(cfg, poll_interval=0.5)
            assert watcher.is_alive()

            watcher.stop()
            watcher.join(timeout=5)
            assert not watcher.is_alive()

    def test_default_log_is_noop(self, tmp_path):
        """start_watcher with no log should not raise."""
        cfg = _make_config(tmp_path)

        with patch("project_memory.indexer.run_index", return_value=_mock_index_result()):
            watcher = start_watcher(cfg, poll_interval=0.5)
            time.sleep(0.3)

            watcher.stop()
            watcher.join(timeout=5)
