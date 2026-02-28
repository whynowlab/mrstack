"""Inline keyboard builders for agentic mode.

Provides context-aware keyboard generation based on Claude response content.
Callback data format: ``agentic:<action>`` or ``job:<action>:<name>``.
All callbacks stay under Telegram's 64-byte limit.
"""

from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class AgenticKeyboards:
    """Build inline keyboards for agentic mode responses."""

    @staticmethod
    def for_code_change(has_tests: bool = False) -> InlineKeyboardMarkup:
        """Keyboard for code modification responses."""
        row1 = [
            InlineKeyboardButton("Run Tests", callback_data="agentic:run_tests"),
            InlineKeyboardButton("Diff", callback_data="agentic:show_diff"),
        ]
        row2 = [
            InlineKeyboardButton("Continue", callback_data="agentic:continue"),
            InlineKeyboardButton("New Task", callback_data="agentic:new_task"),
        ]
        return InlineKeyboardMarkup([row1, row2])

    @staticmethod
    def for_error(is_test_error: bool = False) -> InlineKeyboardMarkup:
        """Keyboard for error responses."""
        row1 = [
            InlineKeyboardButton("Debug", callback_data="agentic:debug"),
            InlineKeyboardButton("Full Error", callback_data="agentic:full_error"),
        ]
        row2 = [
            InlineKeyboardButton("Skip", callback_data="agentic:continue"),
            InlineKeyboardButton("New Session", callback_data="agentic:new_task"),
        ]
        return InlineKeyboardMarkup([row1, row2])

    @staticmethod
    def for_completion() -> InlineKeyboardMarkup:
        """Keyboard for task completion responses."""
        row = [
            InlineKeyboardButton("Continue", callback_data="agentic:continue"),
            InlineKeyboardButton("New Task", callback_data="agentic:new_task"),
            InlineKeyboardButton("Status", callback_data="agentic:status"),
        ]
        return InlineKeyboardMarkup([row])

    @staticmethod
    def for_search_results() -> InlineKeyboardMarkup:
        """Keyboard for search/grep results."""
        row = [
            InlineKeyboardButton("Refine", callback_data="agentic:continue"),
            InlineKeyboardButton("New Task", callback_data="agentic:new_task"),
        ]
        return InlineKeyboardMarkup([row])

    @staticmethod
    def for_job(job_name: str, is_active: bool) -> InlineKeyboardMarkup:
        """Keyboard for individual job control."""
        toggle_label = "Pause" if is_active else "Resume"
        row = [
            InlineKeyboardButton(
                toggle_label, callback_data=f"job:toggle:{job_name}"
            ),
            InlineKeyboardButton(
                "Run Now", callback_data=f"job:run:{job_name}"
            ),
        ]
        return InlineKeyboardMarkup([row])

    @classmethod
    def analyze_and_build(
        cls,
        content: str,
        tools_used: Optional[List[str]] = None,
    ) -> Optional[InlineKeyboardMarkup]:
        """Analyze response content and return appropriate keyboard.

        Args:
            content: The Claude response text.
            tools_used: List of tool names used during the response.

        Returns:
            InlineKeyboardMarkup or None if no keyboard is appropriate.
        """
        if not content:
            return None

        tools = set(tools_used or [])
        content_lower = content.lower()

        # Code changes detected
        if tools & {"Write", "Edit", "MultiEdit"}:
            has_tests = "test" in content_lower
            return cls.for_code_change(has_tests=has_tests)

        # Error/traceback detected
        if any(
            kw in content_lower
            for kw in ["error", "traceback", "exception", "failed"]
        ):
            is_test = "test" in content_lower
            return cls.for_error(is_test_error=is_test)

        # Search results
        if tools & {"Glob", "Grep"}:
            return cls.for_search_results()

        # Any tool usage = task completed
        if tools:
            return cls.for_completion()

        # Pure text response — no keyboard
        return None
