"""Daemon lifecycle management — launchd (macOS), systemd (Linux)."""

from __future__ import annotations

import os
import signal
import subprocess
import textwrap
from pathlib import Path

from rich.console import Console

from .constants import (
    BOT_COMMAND,
    DATA_DIR,
    ENV_FILE,
    IS_LINUX,
    IS_MACOS,
    LOG_DIR,
    PID_FILE,
    PLIST_DIR,
    PLIST_FILE,
    PLIST_LABEL,
    SERVICE_FILE,
    SYSTEMD_USER_DIR,
)

console = Console()


# ── PID helpers ────────────────────────────────────────
def _read_pid() -> int | None:
    if PID_FILE.is_file():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # check alive
            return pid
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)
    return None


def _write_pid(pid: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


# ── Process discovery ──────────────────────────────────
def find_bot_pid() -> int | None:
    """Find running claude-telegram-bot process."""
    pid = _read_pid()
    if pid:
        return pid
    # Fallback: pgrep
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", BOT_COMMAND], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError):
        pass
    return None


def is_running() -> bool:
    return find_bot_pid() is not None


# ── Foreground start ───────────────────────────────────
def start_foreground() -> None:
    """Start the bot in the foreground (blocking)."""
    if not ENV_FILE.is_file():
        console.print("[red].env not found.[/]  Run [bold]mrstack init[/] first.")
        raise SystemExit(1)

    env = _load_env()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]Starting {BOT_COMMAND}...[/]")
    proc = subprocess.Popen(
        [BOT_COMMAND],
        cwd=str(DATA_DIR),
        env=env,
    )
    _write_pid(proc.pid)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=10)
    finally:
        PID_FILE.unlink(missing_ok=True)


# ── Background start ──────────────────────────────────
def start_background() -> int:
    """Start the bot in the background. Returns PID."""
    existing_pid = find_bot_pid()
    if existing_pid is not None:
        console.print(f"[yellow]Already running (PID {existing_pid})[/]")
        return existing_pid

    if not ENV_FILE.is_file():
        console.print("[red].env not found.[/]  Run [bold]mrstack init[/] first.")
        raise SystemExit(1)

    env = _load_env()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    stdout_log = LOG_DIR / "daemon-stdout.log"
    stderr_log = LOG_DIR / "daemon-stderr.log"

    with open(stdout_log, "a") as out, open(stderr_log, "a") as err:
        proc = subprocess.Popen(
            [BOT_COMMAND],
            cwd=str(DATA_DIR),
            env=env,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
    _write_pid(proc.pid)
    console.print(f"[green]Bot started (PID {proc.pid})[/]")
    return proc.pid


# ── Stop ───────────────────────────────────────────────
def stop_bot() -> bool:
    """Stop the bot. Returns True if a process was stopped."""
    pid = find_bot_pid()
    if pid is None:
        console.print("[yellow]Bot is not running.[/]")
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Sent SIGTERM to PID {pid}[/]")
    except OSError as exc:
        console.print(f"[red]Failed to stop PID {pid}: {exc}[/]")
        return False
    # Wait for process to actually exit (max 10s)
    import time

    for _ in range(20):
        time.sleep(0.5)
        try:
            os.kill(pid, 0)
        except OSError:
            break
    PID_FILE.unlink(missing_ok=True)
    return True


# ── Daemon registration ───────────────────────────────
def daemon_install() -> None:
    """Register and start the bot as a system daemon."""
    if IS_MACOS:
        _install_launchd()
    elif IS_LINUX:
        _install_systemd()
    else:
        console.print("[yellow]Daemon not supported on this platform.[/]")
        console.print("Use [bold]mrstack start[/] to run in foreground instead.")


def daemon_uninstall() -> None:
    """Unregister the daemon."""
    if IS_MACOS:
        _uninstall_launchd()
    elif IS_LINUX:
        _uninstall_systemd()
    else:
        console.print("[yellow]No daemon to uninstall.[/]")


# ── macOS launchd ──────────────────────────────────────
def _install_launchd() -> None:
    PLIST_DIR.mkdir(parents=True, exist_ok=True)

    bot_path = _which(BOT_COMMAND)
    if not bot_path:
        console.print(f"[red]{BOT_COMMAND} not found in PATH[/]")
        raise SystemExit(1)

    daemon_sh = DATA_DIR / "start-daemon.sh"
    if not daemon_sh.is_file():
        _write_daemon_sh(daemon_sh)

    plist = textwrap.dedent(f"""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
      "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>Label</key>
        <string>{PLIST_LABEL}</string>
        <key>ProgramArguments</key>
        <array>
            <string>/bin/bash</string>
            <string>{daemon_sh}</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
        <key>ThrottleInterval</key>
        <integer>30</integer>
        <key>StandardOutPath</key>
        <string>{LOG_DIR}/daemon-stdout.log</string>
        <key>StandardErrorPath</key>
        <string>{LOG_DIR}/daemon-stderr.log</string>
        <key>WorkingDirectory</key>
        <string>{DATA_DIR}</string>
    </dict>
    </plist>
    """)

    # Unload first if exists
    if PLIST_FILE.is_file():
        subprocess.run(
            ["launchctl", "unload", str(PLIST_FILE)],
            capture_output=True,
        )

    PLIST_FILE.write_text(plist)
    subprocess.run(["launchctl", "load", str(PLIST_FILE)], check=True)
    console.print(f"[green]LaunchAgent installed and loaded.[/]")
    console.print(f"  Plist: {PLIST_FILE}")


def _uninstall_launchd() -> None:
    if PLIST_FILE.is_file():
        subprocess.run(["launchctl", "unload", str(PLIST_FILE)], capture_output=True)
        PLIST_FILE.unlink()
        console.print("[green]LaunchAgent removed.[/]")
    else:
        console.print("[yellow]No LaunchAgent found.[/]")


# ── Linux systemd ─────────────────────────────────────
def _install_systemd() -> None:
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    bot_path = _which(BOT_COMMAND)
    if not bot_path:
        console.print(f"[red]{BOT_COMMAND} not found in PATH[/]")
        raise SystemExit(1)

    unit = textwrap.dedent(f"""\
    [Unit]
    Description=Mr.Stack — Proactive AI Butler
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    ExecStart={bot_path}
    WorkingDirectory={DATA_DIR}
    EnvironmentFile={ENV_FILE}
    Restart=on-failure
    RestartSec=30

    [Install]
    WantedBy=default.target
    """)

    SERVICE_FILE.write_text(unit)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "mrstack"], check=True)
    console.print("[green]systemd user service installed and started.[/]")
    console.print(f"  Unit: {SERVICE_FILE}")


def _uninstall_systemd() -> None:
    if SERVICE_FILE.is_file():
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", "mrstack"],
            capture_output=True,
        )
        SERVICE_FILE.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        console.print("[green]systemd service removed.[/]")
    else:
        console.print("[yellow]No systemd service found.[/]")


# ── Helpers ────────────────────────────────────────────
def _which(cmd: str) -> str | None:
    import shutil

    return shutil.which(cmd)


def _load_env() -> dict[str, str]:
    """Load environment from .env file merged with current environ."""
    env = os.environ.copy()
    # Ensure common paths
    extra_path = f"{Path.home() / '.local' / 'bin'}:/opt/homebrew/bin:/usr/local/bin"
    env["PATH"] = f"{extra_path}:{env.get('PATH', '')}"
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                val = v.strip().strip("\"'")
                if " #" in val:
                    val = val[: val.index(" #")].rstrip()
                env[k.strip()] = val
    return env


def _write_daemon_sh(path: Path) -> None:
    """Write start-daemon.sh if it doesn't exist."""
    path.write_text(textwrap.dedent(f"""\
    #!/bin/bash
    cd "{DATA_DIR}"
    set -a
    source .env
    set +a
    export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
    {BOT_COMMAND}
    """))
    path.chmod(0o755)
