"""Telegram UI components — cards, blockquotes, icons.

Provides rich formatting primitives built on Telegram's HTML subset.
Uses <blockquote> (Telegram Bot API 7.3+) and expandable blockquotes
(Bot API 7.11+) for collapsible detail sections.
"""

from typing import List, Optional, Tuple

from .html_format import escape_html


class Icons:
    """Centralized emoji constants for consistent UI."""

    SUCCESS = "\u2705"
    ERROR = "\u274c"
    WARNING = "\u26a0\ufe0f"
    INFO = "\u2139\ufe0f"
    WORKING = "\u23f3"
    CODE = "\U0001f4cb"
    FILE = "\U0001f4c4"
    FOLDER = "\U0001f4c2"
    GIT = "\U0001f500"
    SESSION = "\U0001f4a1"
    COST = "\U0001f4b0"
    SCHEDULE = "\U0001f4c5"
    MEMORY = "\U0001f9e0"
    JARVIS = "\U0001f916"
    VOICE = "\U0001f3a4"
    CLIPBOARD = "\U0001f4cb"
    TOGGLE_ON = "\U0001f7e2"
    TOGGLE_OFF = "\u26aa"
    TOOL = "\U0001f527"
    ROCKET = "\U0001f680"


def blockquote(text: str) -> str:
    """Wrap text in a Telegram blockquote."""
    return f"<blockquote>{text}</blockquote>"


def expandable(text: str) -> str:
    """Wrap text in an expandable (collapsible) blockquote.

    Falls back to regular blockquote on older Telegram clients.
    """
    return f"<blockquote expandable>{text}</blockquote>"


def status_card(
    title: str,
    items: List[Tuple[str, str]],
    footer: Optional[str] = None,
) -> str:
    """Build a status card with icon-label pairs.

    Args:
        title: Card header (bold).
        items: List of (icon_or_label, value) tuples.
        footer: Optional footer text (italic).
    """
    lines = [f"<b>{escape_html(title)}</b>\n"]
    for label, value in items:
        lines.append(f"{label}  {escape_html(value)}")
    body = "\n".join(lines)

    if footer:
        body += f"\n\n<i>{escape_html(footer)}</i>"

    return blockquote(body)


def job_card(jobs: list) -> str:
    """Build a formatted job list card.

    Args:
        jobs: List of dicts with keys: name, cron, active, model (optional).
    """
    header = f"{Icons.SCHEDULE} <b>Schedule ({len(jobs)})</b>\n"
    lines = []
    for job in jobs:
        icon = Icons.TOGGLE_ON if job.get("active") else Icons.TOGGLE_OFF
        name = escape_html(job.get("name", "?"))
        cron = escape_html(job.get("cron", "?"))
        model = job.get("model", "")
        model_tag = f"  <i>{escape_html(model)}</i>" if model else ""
        lines.append(f"{icon} <code>{name}</code>  {cron}{model_tag}")

    return header + blockquote("\n".join(lines))


def error_card(
    title: str,
    summary: str,
    details: Optional[str] = None,
) -> str:
    """Build an error card with optional expandable details.

    Args:
        title: Error title (bold with error icon).
        summary: Brief error description.
        details: Optional detailed info (shown in expandable blockquote).
    """
    text = f"{Icons.ERROR} <b>{escape_html(title)}</b>\n\n{escape_html(summary)}"

    if details:
        safe_details = escape_html(details)
        # Truncate extremely long details
        if len(safe_details) > 2000:
            safe_details = safe_details[:2000] + "\n... (truncated)"
        text += f"\n\n{expandable(safe_details)}"

    return text


def code_card(
    code: str,
    language: str = "",
    filename: str = "",
) -> str:
    """Build a code display card.

    Args:
        code: The code content.
        language: Optional language for syntax highlighting.
        filename: Optional filename header.
    """
    header = ""
    if filename:
        header = f"{Icons.FILE} <code>{escape_html(filename)}</code>\n\n"

    escaped_code = escape_html(code)
    if language:
        code_block = f'<pre><code class="language-{escape_html(language)}">{escaped_code}</code></pre>'
    else:
        code_block = f"<pre><code>{escaped_code}</code></pre>"

    return f"{header}{code_block}"


def toggle_card(feature: str, enabled: bool, description: str) -> str:
    """Build a feature toggle status card.

    Args:
        feature: Feature name.
        enabled: Current state.
        description: Brief description of the feature.
    """
    icon = Icons.TOGGLE_ON if enabled else Icons.TOGGLE_OFF
    state = "ON" if enabled else "OFF"
    return f"{icon} <b>{escape_html(feature)}: {state}</b>\n{escape_html(description)}"


def help_card(sections: List[Tuple[str, List[str]]]) -> str:
    """Build a help display with sections.

    Args:
        sections: List of (section_title, [item_lines]) tuples.
    """
    parts = []
    for title, items in sections:
        section_lines = [f"<b>{escape_html(title)}</b>"]
        section_lines.extend(items)
        parts.append(blockquote("\n".join(section_lines)))
    return "\n\n".join(parts)
