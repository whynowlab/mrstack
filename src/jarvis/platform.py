"""Platform abstraction layer for Jarvis context engine.

Detects the current platform and provides cross-platform alternatives
for system monitoring APIs (active app, battery, CPU, etc.).

Usage:
    from .platform import PLATFORM, can, collect_battery, collect_cpu_load

    if can("active_app"):
        app = collect_active_app()
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import structlog

logger = structlog.get_logger()

# ── Platform detection ─────────────────────────────────
PLATFORM: str = sys.platform  # 'darwin', 'linux', 'win32'
IS_MACOS = PLATFORM == "darwin"
IS_LINUX = PLATFORM == "linux"
IS_WINDOWS = PLATFORM == "win32"


@dataclass
class PlatformFeatures:
    """Which features are available on this platform."""

    active_app: bool = False
    battery: bool = False
    cpu_load: bool = True  # psutil works everywhere
    chrome_tabs: bool = False
    sleep_prevent: bool = False
    keychain: bool = True  # keyring library is cross-platform


# Build feature map at import time
def _detect_features() -> PlatformFeatures:
    f = PlatformFeatures()
    if IS_MACOS:
        f.active_app = shutil.which("osascript") is not None
        f.battery = shutil.which("pmset") is not None
        f.chrome_tabs = f.active_app
        f.sleep_prevent = shutil.which("caffeinate") is not None
    elif IS_LINUX:
        # xdotool or xprop can detect active window on X11
        f.active_app = shutil.which("xdotool") is not None
        f.battery = _has_psutil_battery()
    elif IS_WINDOWS:
        f.battery = _has_psutil_battery()
    return f


def _has_psutil_battery() -> bool:
    try:
        import psutil

        return psutil.sensors_battery() is not None
    except Exception:
        return False


FEATURES = _detect_features()


def can(feature: str) -> bool:
    """Check if a feature is available on this platform."""
    return getattr(FEATURES, feature, False)


# ── Cross-platform collectors ──────────────────────────


def collect_active_app() -> str:
    """Return the name of the frontmost application."""
    if IS_MACOS:
        return _run_cmd([
            "osascript", "-e",
            'tell app "System Events" to get name of first process '
            "whose frontmost is true",
        ])
    if IS_LINUX:
        # xdotool approach
        wid = _run_cmd(["xdotool", "getactivewindow"])
        if wid:
            name = _run_cmd(["xdotool", "getactivewindow", "getwindowclassname"])
            return name
    # Windows / unsupported
    return ""


def collect_battery() -> tuple[int, bool]:
    """Return (battery_percent, is_charging).

    Returns (100, True) if battery info is unavailable.
    """
    if IS_MACOS:
        import re

        out = _run_cmd(["pmset", "-g", "batt"])
        if out:
            m = re.search(r"(\d+)%", out)
            pct = int(m.group(1)) if m else 100
            charging = "charging" in out.lower() or "charged" in out.lower()
            return pct, charging

    # Cross-platform fallback via psutil
    try:
        import psutil

        batt = psutil.sensors_battery()
        if batt:
            return int(batt.percent), batt.power_plugged or False
    except Exception:
        pass

    return 100, True


def collect_cpu_load() -> float:
    """Return 1-minute load average (or CPU percent on Windows)."""
    if IS_MACOS:
        import re

        out = _run_cmd(["sysctl", "-n", "vm.loadavg"])
        if out:
            m = re.search(r"[\d.]+", out)
            if m:
                try:
                    return float(m.group())
                except ValueError:
                    pass

    # Cross-platform via psutil
    try:
        import psutil

        if hasattr(psutil, "getloadavg"):
            return psutil.getloadavg()[0]
        return psutil.cpu_percent(interval=1) / 100.0
    except Exception:
        pass

    return 0.0


def collect_chrome_tabs() -> List[str]:
    """Return list of Chrome tab titles (macOS only)."""
    if IS_MACOS:
        out = _run_cmd([
            "osascript", "-e",
            'tell application "Google Chrome" to get title of active tab '
            "of front window",
        ])
        if out:
            return [out]
    return []


def collect_git_info(working_directory: str) -> tuple[str, bool]:
    """Return (branch_name, is_dirty)."""
    branch = _run_cmd(["git", "-C", working_directory, "branch", "--show-current"])
    dirty_out = _run_cmd(["git", "-C", working_directory, "status", "--short"])
    return branch, bool(dirty_out)


# ── Helper ─────────────────────────────────────────────
def _run_cmd(cmd: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""
