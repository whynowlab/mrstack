"""Shared constants and path helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
HOME = Path.home()
DATA_DIR = HOME / "claude-telegram"
ENV_FILE = DATA_DIR / ".env"
DB_FILE = DATA_DIR / "data" / "bot.db"
LOG_DIR = DATA_DIR / "logs"
MEMORY_DIR = DATA_DIR / "memory"
TEMPLATES_DIR = DATA_DIR / "templates"

PLIST_LABEL = "com.mrstack.claude-telegram"
PLIST_DIR = HOME / "Library" / "LaunchAgents"
PLIST_FILE = PLIST_DIR / f"{PLIST_LABEL}.plist"

SYSTEMD_USER_DIR = HOME / ".config" / "systemd" / "user"
SERVICE_FILE = SYSTEMD_USER_DIR / "mrstack.service"

PID_FILE = DATA_DIR / ".mrstack.pid"

# ── Platform ───────────────────────────────────────────
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform == "linux"
IS_WINDOWS = sys.platform == "win32"

# ── Overlay source (bundled with package via hatchling force-include) ──
OVERLAY_DIR = Path(__file__).parent / "_overlay"
DATA_CONFIG_DIR = Path(__file__).parent / "_data" / "config"
DATA_SCHEDULERS_DIR = Path(__file__).parent / "_data" / "schedulers"
DATA_TEMPLATES_DIR = Path(__file__).parent / "_data" / "templates"

# ── External tools ─────────────────────────────────────
CLAUDE_TELEGRAM_PKG = "claude-code-telegram"
BOT_COMMAND = "claude-telegram-bot"


def find_site_packages() -> Path | None:
    """Find the claude-code-telegram site-packages directory."""
    # Method 1: uv tools
    uv_base = HOME / ".local" / "share" / "uv" / "tools" / CLAUDE_TELEGRAM_PKG
    if uv_base.is_dir():
        for d in sorted(uv_base.glob("lib/python3.*/site-packages/src"), reverse=True):
            if d.is_dir():
                return d.parent
    # Method 2: pipx
    pipx_base = HOME / ".local" / "pipx" / "venvs" / CLAUDE_TELEGRAM_PKG
    if pipx_base.is_dir():
        for d in sorted(pipx_base.glob("lib/python3.*/site-packages/src"), reverse=True):
            if d.is_dir():
                return d.parent
    return None


def resolve_env_value(key: str, default: str = "") -> str:
    """Read a value from .env file or environment."""
    val = os.environ.get(key)
    if val:
        return val
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                v = v.strip().strip("\"'")
                # Strip inline comments
                if " #" in v:
                    v = v[: v.index(" #")].rstrip()
                return v
    return default
