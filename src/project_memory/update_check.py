"""Check GitHub for newer pmem releases."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from project_memory import __version__

logger = logging.getLogger("pmem-mcp")

GITHUB_REPO = "avanrossum/pmem-project-memory-tool-for-claude-code"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

# Cache lives in the global config dir so it's per-installation, not per-project.
CACHE_DIR = Path.home() / ".config" / "pmem"
CACHE_PATH = CACHE_DIR / "update_check.json"

# Check at most once per day (seconds).
CHECK_INTERVAL = 86400


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version tag like 'v0.5.1' or '0.5.1-beta.1' into a comparable tuple."""
    tag = tag.lstrip("v")
    # Split off pre-release suffix for base comparison
    base = tag.split("-")[0]
    parts: list[int] = []
    for segment in base.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts)


def _is_prerelease(release: dict[str, Any]) -> bool:
    """Check if a GitHub release is a pre-release."""
    return bool(release.get("prerelease"))


def _load_cache() -> dict[str, Any]:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_cache(data: dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(data, indent=2) + "\n")
    except OSError:
        pass  # non-critical


def check_for_update(channel: str = "stable") -> str | None:
    """Check GitHub for a newer release.

    Args:
        channel: "stable" (default) only considers full releases.
                 "beta" also considers pre-releases.

    Returns a notice string if an update is available, or None.
    Uses a local cache to avoid hitting GitHub more than once per day.
    """
    current = _parse_version(__version__)
    if current == (0, 0, 0):
        return None  # dev install, skip check

    cache = _load_cache()
    now = time.time()

    # Return cached result if fresh
    if now - cache.get("last_check", 0) < CHECK_INTERVAL:
        notice = cache.get("notice")
        # Re-evaluate: if channel changed or version was upgraded, re-check
        if cache.get("channel") == channel and cache.get("current_version") == __version__:
            return notice

    # Fetch releases from GitHub
    try:
        resp = httpx.get(
            RELEASES_URL,
            headers={"Accept": "application/vnd.github+json"},
            timeout=5,
        )
        resp.raise_for_status()
        releases: list[dict[str, Any]] = resp.json()
    except Exception as exc:
        logger.debug(f"Update check failed: {exc}")
        # Cache the failure so we don't retry immediately
        _save_cache({
            "last_check": now,
            "channel": channel,
            "current_version": __version__,
            "notice": None,
        })
        return None

    # Find the latest release for this channel
    latest_tag: str | None = None
    latest_version: tuple[int, ...] = current
    is_beta_release = False

    for release in releases:
        if release.get("draft"):
            continue
        prerelease = _is_prerelease(release)
        if channel == "stable" and prerelease:
            continue
        tag = release.get("tag_name", "")
        ver = _parse_version(tag)
        if ver > latest_version:
            latest_version = ver
            latest_tag = tag
            is_beta_release = prerelease

    notice: str | None = None
    if latest_tag is not None:
        label = " (beta)" if is_beta_release else ""
        notice = (
            f"\n>>> pmem update available: {__version__} -> "
            f"{latest_tag.lstrip('v')}{label}. "
            f"Run `git pull` in your pmem repo and reinstall."
        )

    _save_cache({
        "last_check": now,
        "channel": channel,
        "current_version": __version__,
        "latest_tag": latest_tag,
        "notice": notice,
    })
    return notice
