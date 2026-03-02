"""Interactive setup wizard for first-time configuration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .constants import (
    BOT_COMMAND,
    CLAUDE_TELEGRAM_PKG,
    DATA_DIR,
    ENV_FILE,
    IS_MACOS,
    LOG_DIR,
    MEMORY_DIR,
    TEMPLATES_DIR,
    find_site_packages,
)
from .patcher import patch_install

console = Console()


def run_wizard() -> None:
    """Run the interactive setup wizard."""
    from .banner import print_banner, print_divider, status_icon

    print_banner(console)
    print_divider(console)
    console.print("  [bold]Setup Wizard[/] — Let's configure your AI butler.")
    print_divider(console)
    console.print()

    # Step 1: Check prerequisites
    _step("Checking prerequisites")
    _check_python()
    _check_claude_code()
    _check_claude_telegram()

    # Step 2: Telegram bot token
    _step("Telegram Bot Configuration")
    token = _ask_bot_token()
    user_id = _ask_user_id()

    # Step 3: Working directory setup
    _step("Setting up working directory")
    _setup_directories()

    # Step 4: Create .env
    _step("Creating configuration")
    jarvis_enabled = False
    if IS_MACOS:
        jarvis_enabled = Confirm.ask(
            "  Enable Jarvis mode? (proactive context engine, macOS only)",
            default=True,
        )

    _write_env(token, user_id, jarvis_enabled)

    # Step 5: Install overlay modules
    _step("Installing Mr.Stack modules")
    site_pkg = find_site_packages()
    if site_pkg:
        patch_install(site_pkg, force=True)
    else:
        console.print(
            "  [yellow]claude-code-telegram not found. "
            "Overlay installation skipped.[/]"
        )
        console.print(
            "  After installing claude-code-telegram, run: "
            "[bold]mrstack patch[/]"
        )

    # Step 6: Copy data files
    _step("Setting up templates and schedulers")
    _copy_data_files()

    # Done
    console.print()
    print_divider(console)
    console.print()
    console.print("  [green bold]Setup complete![/]")
    console.print()
    console.print(f"  {status_icon(True)} [bold]mrstack start[/]    Start the bot")
    console.print(f"  {status_icon(True)} [bold]mrstack daemon[/]   Register as background service")
    console.print(f"  {status_icon(True)} [bold]mrstack status[/]   Check status")
    console.print(f"  {status_icon(True)} [bold]mrstack logs -f[/]  Follow logs")
    console.print()
    print_divider(console)
    console.print()


def _step(msg: str) -> None:
    console.print(f"\n[bold cyan]>[/] {msg}")


def _check_python() -> None:
    v = sys.version_info
    if v >= (3, 11):
        console.print(f"  [green]Python {v.major}.{v.minor}.{v.micro}[/] found")
    else:
        console.print(
            f"  [red]Python {v.major}.{v.minor} detected — 3.11+ required.[/]"
        )
        console.print("  Install: [bold]brew install python[/] (macOS)")
        raise SystemExit(1)


def _check_claude_code() -> None:
    if shutil.which("claude"):
        console.print("  [green]Claude Code[/] found")
        return

    console.print("  [yellow]Claude Code not found.[/]")
    console.print()
    console.print(
        Panel(
            "[bold]Claude Code is required.[/]\n\n"
            "Install it with:\n"
            "  [bold cyan]npm install -g @anthropic-ai/claude-code[/]\n\n"
            "You need a Claude Pro or Max subscription.\n"
            "Sign up at: [bold]https://claude.ai[/]",
            title="Missing: Claude Code",
            border_style="yellow",
            padding=(1, 2),
        )
    )
    if not Confirm.ask("  Continue without Claude Code?", default=False):
        raise SystemExit(0)


def _check_claude_telegram() -> None:
    if shutil.which(BOT_COMMAND):
        console.print(f"  [green]{CLAUDE_TELEGRAM_PKG}[/] found")
        return

    console.print(f"  [yellow]{CLAUDE_TELEGRAM_PKG} not found.[/]")
    if Confirm.ask("  Install it now? (takes ~30 seconds)", default=True):
        console.print("  Installing... please wait.")
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "tool", "install", CLAUDE_TELEGRAM_PKG],
                check=True,
            )
        elif shutil.which("pipx"):
            subprocess.run(
                ["pipx", "install", CLAUDE_TELEGRAM_PKG],
                check=True,
            )
        else:
            subprocess.run(
                ["pip", "install", CLAUDE_TELEGRAM_PKG],
                check=True,
            )
        console.print(f"  [green]{CLAUDE_TELEGRAM_PKG} installed[/]")
    else:
        console.print("  Skipping — you can install it later.")


def _ask_bot_token() -> str:
    console.print()
    console.print(
        Panel(
            "[bold]How to get a bot token:[/]\n\n"
            "1. Open Telegram and search for [bold cyan]@BotFather[/]\n"
            "2. Send [bold]/newbot[/]\n"
            "3. Enter a name (e.g. [dim]My Stack Bot[/])\n"
            "4. Enter a username (e.g. [dim]my_stack_bot[/])\n"
            "5. Copy the token below",
            title="Telegram Bot Token",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    while True:
        token = Prompt.ask("  Paste your bot token").strip()
        if not token:
            continue
        if ":" not in token:
            console.print("  [red]Invalid format. Should look like: 1234567890:ABCdef...[/]")
            continue
        if _validate_token(token):
            return token
        console.print("  [red]Token validation failed. Double-check and try again.[/]")


def _validate_token(token: str) -> bool:
    try:
        import urllib.request

        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                bot_name = data["result"].get("username", "unknown")
                console.print(f"  [green]Verified: @{bot_name}[/]")
                return True
    except Exception:
        pass
    return False


def _ask_user_id() -> str:
    console.print()
    console.print(
        Panel(
            "[bold]How to find your User ID:[/]\n\n"
            "1. Open Telegram and search for [bold cyan]@userinfobot[/]\n"
            "2. Send any message\n"
            "3. Copy the number it replies with",
            title="Telegram User ID",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    while True:
        uid = Prompt.ask("  Paste your User ID (number)").strip()
        if uid.isdigit():
            return uid
        console.print("  [red]Must be a number (e.g. 123456789)[/]")


def _setup_directories() -> None:
    for d in [DATA_DIR, DATA_DIR / "data", LOG_DIR, MEMORY_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    console.print(f"  [green]Data directory:[/] {DATA_DIR}")


def _write_env(token: str, user_id: str, jarvis: bool) -> None:
    import secrets

    webhook_secret = secrets.token_hex(32)

    env_content = textwrap.dedent(f"""\
    # Mr.Stack Configuration
    # Generated by mrstack init

    # Telegram
    TELEGRAM_BOT_TOKEN={token}
    TELEGRAM_BOT_USERNAME=
    APPROVED_DIRECTORY={Path.home()}
    ALLOWED_USERS={user_id}
    NOTIFICATION_CHAT_IDS={user_id}

    # Claude
    CLAUDE_MAX_TURNS=30
    CLAUDE_TIMEOUT_SECONDS=600
    AGENTIC_MODE=true

    # Features
    ENABLE_JARVIS={'true' if jarvis else 'false'}
    ENABLE_GIT_INTEGRATION=true
    ENABLE_FILE_UPLOADS=true
    ENABLE_IMAGE_UPLOADS=true
    ENABLE_QUICK_ACTIONS=true
    ENABLE_CLIPBOARD_MONITOR={'true' if IS_MACOS else 'false'}
    ENABLE_SCHEDULER=true
    ENABLE_API_SERVER=true
    ENABLE_MCP=false

    # API Server
    API_SERVER_PORT=8080
    WEBHOOK_API_SECRET={webhook_secret}

    # Database
    DATABASE_URL=sqlite:///{DATA_DIR}/data/bot.db
    """)

    if ENV_FILE.is_file():
        if not Confirm.ask(
            f"  .env already exists at {ENV_FILE}. Overwrite?", default=False
        ):
            console.print("  [yellow]Keeping existing .env[/]")
            return

    fd = os.open(str(ENV_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(env_content)
    console.print(f"  [green].env created[/] ({ENV_FILE})")


def _copy_data_files() -> None:
    """Copy templates and scheduler scripts to the data directory."""
    from .constants import DATA_TEMPLATES_DIR, DATA_SCHEDULERS_DIR

    # Templates
    src_templates = DATA_TEMPLATES_DIR
    if not src_templates.is_dir():
        # Fallback: repo-local
        src_templates = Path(__file__).parent.parent / "templates"
    if src_templates.is_dir():
        dst = TEMPLATES_DIR
        dst.mkdir(parents=True, exist_ok=True)
        for f in src_templates.iterdir():
            if f.is_file():
                target = dst / f.name
                if not target.exists():
                    shutil.copy2(f, target)
        console.print(f"  [green]Templates[/] -> {dst}")

    # Memory subdirs
    for sub in ["daily", "decisions", "knowledge", "patterns", "people", "projects", "preferences"]:
        (MEMORY_DIR / sub).mkdir(parents=True, exist_ok=True)
    console.print(f"  [green]Memory dirs[/] -> {MEMORY_DIR}")
