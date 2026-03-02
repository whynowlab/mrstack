"""Mr.Stack ASCII art banner and branding elements."""

from rich.console import Console
from rich.text import Text

from . import __version__

# ── Brand colors (rich markup) ─────────────────────────
# Cyan = primary, Magenta = accent, Green = success
BRAND_CYAN = "cyan"
BRAND_MAGENTA = "magenta"
BRAND_GREEN = "green"
BRAND_DIM = "dim"

# ── ASCII Logo ─────────────────────────────────────────
LOGO = r"""
  [cyan]███╗   ███╗██████╗   [magenta]███████╗████████╗ █████╗  ██████╗██╗  ██╗[/]
  [cyan]████╗ ████║██╔══██╗  [magenta]██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝[/]
  [cyan]██╔████╔██║██████╔╝  [magenta]███████╗   ██║   ███████║██║     █████╔╝[/]
  [cyan]██║╚██╔╝██║██╔══██╗  [magenta]╚════██║   ██║   ██╔══██║██║     ██╔═██╗[/]
  [cyan]██║ ╚═╝ ██║██║  ██║██╗███████║   ██║   ██║  ██║╚██████╗██║  ██╗[/]
  [cyan]╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝[/]
"""

TAGLINE = "  [dim]Your AI butler, fully stacked.[/]"

# ── Compact banner (for status, start, etc.) ───────────
COMPACT_LOGO = (
    "  [cyan bold]◆ ◆ ◆[/]  [bold]Mr.Stack[/]  [cyan bold]◆ ◆ ◆[/]"
)


def print_banner(console: Console, compact: bool = False) -> None:
    """Print the Mr.Stack banner."""
    if compact:
        console.print()
        console.print(COMPACT_LOGO)
        console.print(f"  [dim]v{__version__}[/]")
    else:
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
