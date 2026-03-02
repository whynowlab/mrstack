"""Mr.Stack CLI — command-line interface for the proactive AI butler."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .constants import (
    BOT_COMMAND,
    DATA_DIR,
    DB_FILE,
    ENV_FILE,
    IS_MACOS,
    LOG_DIR,
    MEMORY_DIR,
    find_site_packages,
    resolve_env_value,
)
from .daemon import (
    daemon_install,
    daemon_uninstall,
    find_bot_pid,
    is_running,
    start_background,
    start_foreground,
    stop_bot,
)

console = Console()
app = typer.Typer(
    name="mrstack",
    help="Mr.Stack — Proactive AI Butler for Claude Code",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


# ── version ────────────────────────────────────────────
def _version_callback(value: bool) -> None:
    if value:
        console.print(f"Mr.Stack [bold]v{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Mr.Stack — Proactive AI Butler for Claude Code."""


# ── init ───────────────────────────────────────────────
@app.command()
def init() -> None:
    """Interactive setup wizard."""
    from .wizard import run_wizard

    run_wizard()


# ── start ──────────────────────────────────────────────
@app.command()
def start(
    background: bool = typer.Option(False, "--bg", "-b", help="Run in background."),
) -> None:
    """Start the bot."""
    if background:
        start_background()
    else:
        start_foreground()


# ── stop ───────────────────────────────────────────────
@app.command()
def stop() -> None:
    """Stop the bot."""
    stop_bot()


# ── daemon ─────────────────────────────────────────────
@app.command()
def daemon(
    uninstall: bool = typer.Option(False, "--uninstall", "-u", help="Remove daemon."),
) -> None:
    """Install/uninstall as a system daemon (launchd/systemd)."""
    if uninstall:
        daemon_uninstall()
    else:
        daemon_install()


# ── status ─────────────────────────────────────────────
@app.command()
def status() -> None:
    """Show current status."""
    pid = find_bot_pid()
    running = pid is not None

    # Collect info
    version_str = f"v{__version__}"
    status_str = f"[green]Running (PID {pid})[/]" if running else "[red]Stopped[/]"

    uptime_str = "—"
    if running and pid:
        try:
            import psutil

            proc = psutil.Process(pid)
            uptime = datetime.now() - datetime.fromtimestamp(proc.create_time())
            days = uptime.days
            hours, rem = divmod(uptime.seconds, 3600)
            mins = rem // 60
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            parts.append(f"{mins}m")
            uptime_str = " ".join(parts)
        except Exception:
            uptime_str = "unknown"

    memory_count = 0
    if MEMORY_DIR.is_dir():
        memory_count = sum(1 for _ in MEMORY_DIR.rglob("*.md"))

    jarvis_str = "[dim]OFF[/]"
    jarvis_enabled = resolve_env_value("ENABLE_JARVIS", "false").lower() == "true"
    if jarvis_enabled:
        if IS_MACOS:
            jarvis_str = "[green]ON[/]"
        else:
            jarvis_str = "[yellow]ON (limited — not macOS)[/]"

    last_msg = "—"
    if DB_FILE.is_file():
        try:
            import sqlite3

            with sqlite3.connect(str(DB_FILE)) as conn:
                row = conn.execute(
                    "SELECT MAX(created_at) FROM messages"
                ).fetchone()
                if row and row[0]:
                    ts = datetime.fromisoformat(row[0])
                    delta = datetime.now() - ts
                    if delta < timedelta(minutes=1):
                        last_msg = "just now"
                    elif delta < timedelta(hours=1):
                        last_msg = f"{int(delta.total_seconds() // 60)}m ago"
                    elif delta < timedelta(days=1):
                        last_msg = f"{int(delta.total_seconds() // 3600)}h ago"
                    else:
                        last_msg = ts.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    panel = Panel(
        f"  Status:        {status_str}\n"
        f"  Uptime:        {uptime_str}\n"
        f"  Memory:        {memory_count} entries\n"
        f"  Last message:  {last_msg}\n"
        f"  Jarvis:        {jarvis_str}\n"
        f"  Data:          {DATA_DIR}",
        title=f"[bold]Mr.Stack {version_str}[/]",
        border_style="cyan",
    )
    console.print(panel)


# ── logs ───────────────────────────────────────────────
@app.command()
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output."),
) -> None:
    """View recent logs."""
    log_file = LOG_DIR / "daemon-stdout.log"
    if not log_file.is_file():
        log_file = LOG_DIR / "stdout.log"
    if not log_file.is_file():
        console.print("[yellow]No log files found.[/]")
        raise typer.Exit(1)

    cmd = ["tail"]
    if follow:
        cmd.append("-f")
    cmd.extend(["-n", str(lines), str(log_file)])
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        console.print("[red]'tail' command not found.[/]")
        # Fallback: read with Python
        content = log_file.read_text()
        for line in content.splitlines()[-lines:]:
            console.print(line)


# ── config ─────────────────────────────────────────────
@app.command()
def config() -> None:
    """Open configuration file in editor."""
    if not ENV_FILE.is_file():
        console.print("[red].env not found.[/]  Run [bold]mrstack init[/] first.")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(ENV_FILE)])


# ── jarvis ─────────────────────────────────────────────
@app.command()
def jarvis(
    state: str = typer.Argument(
        ..., help="on / off", metavar="STATE",
    ),
) -> None:
    """Toggle Jarvis mode."""
    state = state.strip().lower()
    if state not in ("on", "off"):
        console.print("[red]Usage: mrstack jarvis on|off[/]")
        raise typer.Exit(1)

    if not ENV_FILE.is_file():
        console.print("[red].env not found.[/]")
        raise typer.Exit(1)

    enable = state == "on"
    if enable and not IS_MACOS:
        console.print(
            "[yellow]Jarvis mode has limited functionality on non-macOS platforms.[/]"
        )

    text = ENV_FILE.read_text()
    new_val = "true" if enable else "false"

    if "ENABLE_JARVIS=" in text:
        import re

        text = re.sub(r"ENABLE_JARVIS=\w+", f"ENABLE_JARVIS={new_val}", text)
    else:
        text += f"\nENABLE_JARVIS={new_val}\n"

    ENV_FILE.write_text(text)
    icon = "[green]ON[/]" if enable else "[red]OFF[/]"
    console.print(f"Jarvis mode: {icon}")

    if is_running():
        console.print("[dim]Restart the bot for changes to take effect.[/]")


# ── patch ──────────────────────────────────────────────
@app.command()
def patch(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Install/update Mr.Stack modules into claude-code-telegram."""
    from .patcher import patch_install

    patch_install(force=force)


# ── update ─────────────────────────────────────────────
@app.command()
def update() -> None:
    """Update Mr.Stack to the latest version."""
    console.print("Updating Mr.Stack...")
    if shutil.which("uv"):
        subprocess.run(["uv", "tool", "upgrade", "mrstack"], check=True)
    elif shutil.which("pipx"):
        subprocess.run(["pipx", "upgrade", "mrstack"], check=True)
    else:
        subprocess.run(["pip", "install", "--upgrade", "mrstack"], check=True)

    # Re-patch after update
    console.print("Re-applying patches...")
    from .patcher import patch_install

    patch_install(force=True)
    console.print("[green]Update complete.[/]")


# ── version (explicit command) ─────────────────────────
@app.command(name="version")
def version_cmd() -> None:
    """Show version information."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Mr.Stack", f"v{__version__}")

    # claude-code-telegram version
    try:
        from importlib.metadata import version as pkg_version

        cct_ver = pkg_version("claude-code-telegram")
        table.add_row("claude-code-telegram", f"v{cct_ver}")
    except Exception:
        table.add_row("claude-code-telegram", "[dim]not installed[/]")

    # Claude Code version
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            table.add_row("Claude Code", result.stdout.strip())
    except Exception:
        table.add_row("Claude Code", "[dim]not found[/]")

    # Platform
    import platform

    table.add_row("Platform", f"{platform.system()} {platform.machine()}")
    table.add_row("Python", platform.python_version())

    console.print(table)
