"""Install Mr.Stack overlay modules into claude-code-telegram."""

from __future__ import annotations

import re
import shutil
import textwrap
from pathlib import Path

from rich.console import Console

from .constants import OVERLAY_DIR, find_site_packages

console = Console()

# Directories inside the overlay that should be copied into site-packages/src/
OVERLAY_MODULES = ["jarvis", "knowledge", "bot", "api", "claude"]


def locate_overlay_dir() -> Path:
    """Return the overlay directory, checking both bundled and repo-local paths."""
    # Bundled (pip/uv install)
    if OVERLAY_DIR.is_dir() and any(
        p for p in OVERLAY_DIR.iterdir() if p.name != "__pycache__"
    ):
        return OVERLAY_DIR
    # Repo-local (git clone)
    repo_src = Path(__file__).parent.parent / "src"
    if repo_src.is_dir():
        return repo_src
    raise FileNotFoundError(
        "Overlay files not found.  Reinstall mrstack or run from the git repo."
    )


def patch_install(site_pkg: Path | None = None, force: bool = False) -> bool:
    """Copy overlay modules into the claude-code-telegram installation.

    Returns True on success.
    """
    if site_pkg is None:
        site_pkg = find_site_packages()
    if site_pkg is None:
        console.print(
            "[red]claude-code-telegram not found.[/]  "
            "Install it first:  [bold]uv tool install claude-code-telegram[/]"
        )
        return False

    src_dir = site_pkg / "src"
    if not (src_dir / "bot" / "orchestrator.py").is_file():
        console.print(f"[red]Invalid installation at {site_pkg}[/]")
        return False

    overlay = locate_overlay_dir()

    for mod in OVERLAY_MODULES:
        mod_src = overlay / mod
        if not mod_src.is_dir():
            continue
        mod_dst = src_dir / mod
        if mod_dst.is_dir() and not force:
            # Merge: copy individual files, don't nuke the whole directory
            for f in mod_src.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(mod_src)
                    dst = mod_dst / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
        else:
            if mod_dst.is_dir():
                shutil.rmtree(mod_dst)
            shutil.copytree(mod_src, mod_dst)

    console.print("[green]Overlay modules installed.[/]")

    # Patch settings.py — add enable_jarvis field
    _patch_settings(src_dir)
    # Patch main.py — wire up Jarvis engine
    _patch_main(src_dir)
    return True


def _patch_settings(src_dir: Path) -> None:
    settings = src_dir / "config" / "settings.py"
    if not settings.is_file():
        return
    text = settings.read_text()
    if "enable_jarvis" in text:
        console.print("  settings.py — enable_jarvis already present")
        return
    # Insert after enable_clipboard_monitor field
    marker = "enable_clipboard_monitor"
    if marker not in text:
        console.print("[yellow]  settings.py — marker not found, skip patch[/]")
        return
    # Find the closing ')' of that Field(...)
    idx = text.index(marker)
    # Find next unmatched ')' after the marker
    depth = 0
    i = text.index("Field(", idx)
    for i in range(i, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                break
    insert_pos = i + 1
    patch = textwrap.dedent("""
    enable_jarvis: bool = Field(
        False,
        description="Enable Jarvis proactive context engine",
    )""")
    text = text[:insert_pos] + "\n" + patch + text[insert_pos:]
    settings.write_text(text)
    console.print("  settings.py — patched")


def _patch_main(src_dir: Path) -> None:
    main = src_dir / "main.py"
    if not main.is_file():
        return
    text = main.read_text()
    if "jarvis_engine" in text:
        console.print("  main.py — jarvis_engine already present")
        return

    # Add variable declaration
    text = text.replace(
        "clipboard_monitor = None",
        "clipboard_monitor = None\n    jarvis_engine = None",
    )

    # Add startup block after clipboard monitor
    startup = textwrap.dedent("""\

        # Jarvis engine (if enabled)
        if config.enable_jarvis:
            from src.jarvis import JarvisEngine

            jarvis_engine = JarvisEngine(
                event_bus=event_bus,
                target_chat_ids=config.notification_chat_ids or [],
                working_directory=str(config.approved_directory),
            )
            await jarvis_engine.start()
            bot.deps["jarvis_engine"] = jarvis_engine
            logger.info("Jarvis engine enabled")
    """)
    clipboard_marker = 'logger.info("Clipboard monitor enabled")'
    shutdown_marker = "# Shutdown task"
    if clipboard_marker in text:
        text = text.replace(clipboard_marker, clipboard_marker + "\n" + startup)
    elif shutdown_marker in text:
        text = text.replace(shutdown_marker, startup + "\n        " + shutdown_marker)
    else:
        console.print("[red]  main.py — no known injection point found, skipping[/]")
        return

    # Add shutdown
    text = text.replace(
        "if clipboard_monitor:\n                await clipboard_monitor.stop()",
        "if jarvis_engine:\n                await jarvis_engine.stop()\n"
        "            if clipboard_monitor:\n                await clipboard_monitor.stop()",
    )

    main.write_text(text)
    console.print("  main.py — patched")
