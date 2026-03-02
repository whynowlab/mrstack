"""Mr.Stack ASCII art banner and branding elements."""

from rich.console import Console
from rich.text import Text

from . import __version__

# ── Brand colors (rich markup) ─────────────────────────
# Matches the app icon: blue → cyan → green → magenta layers
BRAND_CYAN = "cyan"
BRAND_MAGENTA = "magenta"
BRAND_GREEN = "green"
BRAND_DIM = "dim"

# ── Stack icon (terminal version of the app icon) ─────
STACK_ICON = (
    "        [bold blue]▄▄▄▄▄▄▄▄▄▄[/]\n"
    "       [bold cyan]▄▄▄▄▄▄▄▄▄▄▄▄[/]\n"
    "      [bold green]▄▄▄▄▄▄▄▄▄▄▄▄▄▄[/]\n"
    "     [bold magenta]▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄[/]"
)

# ── ASCII Logo ─────────────────────────────────────────
LOGO = r"""
  [cyan] __  __      [/][magenta]____  _             _    [/]
  [cyan]|  \/  |_ __ [/][magenta]/ ___|| |_ __ _  ___| | __[/]
  [cyan]| |\/| | '__|[/][magenta]\___ \| __/ _` |/ __| |/ /[/]
  [cyan]| |  | | |  _[/][magenta] ___) | || (_| | (__|   < [/]
  [cyan]|_|  |_|_| [/][magenta](_)____/ \__\__,_|\___|_|[/]\_\
"""

TAGLINE = "  [dim]Your AI butler, fully stacked.[/]"

# ── Compact banner (for status, start, etc.) ───────────
# Inline stack: 4 colored blocks representing the layered icon
COMPACT_LOGO = (
    "  [bold blue]▮[/][bold cyan]▮[/][bold green]▮[/][bold magenta]▮[/]"
    "  [bold]Mr.Stack[/]"
)


def print_banner(console: Console, compact: bool = False) -> None:
    """Print the Mr.Stack banner."""
    if compact:
        console.print()
        console.print(COMPACT_LOGO)
        console.print(f"  [dim]v{__version__}[/]")
    else:
        console.print(STACK_ICON)
        console.print(LOGO)
        console.print(TAGLINE)
        console.print(f"  [dim]v{__version__}[/]")
    console.print()


def print_divider(console: Console) -> None:
    """Print a branded divider line."""
    console.print("  [dim]─────────────────────────────────────────[/]")


def status_icon(ok: bool) -> str:
    """Return a branded status icon."""
    return "[cyan]◆[/]" if ok else "[dim]◇[/]"
