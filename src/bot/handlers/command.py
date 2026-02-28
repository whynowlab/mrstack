"""Command handlers for bot operations."""

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...projects import PrivateTopicsUnavailableError, load_project_registry
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator
from ..utils.html_format import escape_html

logger = structlog.get_logger()


def _is_within_root(path: Path, root: Path) -> bool:
    """Check whether path is within root directory."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _get_thread_project_root(
    settings: Settings, context: ContextTypes.DEFAULT_TYPE
) -> Optional[Path]:
    """Get thread project root when strict thread mode is active."""
    if not settings.enable_project_threads:
        return None
    thread_context = context.user_data.get("_thread_context")
    if not thread_context:
        return None
    return Path(thread_context["project_root"]).resolve()


def _is_private_chat(update: Update) -> bool:
    """Return True when update is from a private chat."""
    chat = update.effective_chat
    return bool(chat and getattr(chat, "type", "") == "private")


def _read_oauth_token() -> Optional[str]:
    """Read Claude OAuth token from macOS Keychain via Swift subprocess."""
    try:
        swift_code = """
import Foundation
import Security
let q: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: "Claude Code-credentials",
    kSecReturnData as String: true,
    kSecMatchLimit as String: kSecMatchLimitOne
]
var r: AnyObject?
guard SecItemCopyMatching(q as CFDictionary, &r) == errSecSuccess,
      let d = r as? Data, let s = String(data: d, encoding: .utf8) else { exit(1) }
if let range = s.range(of: "sk-ant-oat01-[A-Za-z0-9_-]+", options: .regularExpression) {
    print(s[range])
}
"""
        result = subprocess.run(
            ["swift", "-"],
            input=swift_code,
            capture_output=True,
            text=True,
            timeout=15,
        )
        token = result.stdout.strip()
        if token and token.startswith("sk-ant-oat01-"):
            return token
        return None
    except Exception:
        return None


async def _get_claude_usage() -> Optional[dict[str, Any]]:
    """Fetch Claude Code plan usage from Anthropic OAuth API."""
    try:
        token = _read_oauth_token()
        if not token:
            logger.warning("Failed to read OAuth token from Keychain")
            return None

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.anthropic.com/api/oauth/usage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "anthropic-beta": "oauth-2025-04-20",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch Claude usage", error=str(e))
        return None


def _format_usage_bar(utilization_pct: float, width: int = 10) -> str:
    """Format a utilization percentage (0-100) as a progress bar."""
    filled = round(utilization_pct / 100 * width)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def _format_reset_time(resets_at: str) -> str:
    """Format ISO reset time as human-readable remaining duration."""
    try:
        reset_dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = reset_dt - now
        if delta.total_seconds() <= 0:
            return "곧 리셋"
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return resets_at


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    settings: Settings = context.bot_data["settings"]
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")
    manager = context.bot_data.get("project_threads_manager")
    sync_section = ""

    if settings.enable_project_threads and settings.project_threads_mode == "private":
        if not _is_private_chat(update):
            await update.message.reply_text(
                "🚫 <b>Private Topics Mode</b>\n\n"
                "Use this bot in a private chat and run <code>/start</code> there.",
                parse_mode="HTML",
            )
            return

    if (
        settings.enable_project_threads
        and settings.project_threads_mode == "private"
        and _is_private_chat(update)
    ):
        if manager is None:
            await update.message.reply_text(
                "❌ <b>Project thread mode is misconfigured</b>\n\n"
                "Thread manager is not initialized.",
                parse_mode="HTML",
            )
            return

        try:
            sync_result = await manager.sync_topics(
                context.bot,
                chat_id=update.effective_chat.id,
            )
            sync_section = (
                "\n\n🧵 <b>Project Topics Synced</b>\n"
                f"• Created: <b>{sync_result.created}</b>\n"
                f"• Reused: <b>{sync_result.reused}</b>\n"
                f"• Renamed: <b>{sync_result.renamed}</b>\n"
                f"• Failed: <b>{sync_result.failed}</b>\n\n"
                "Use a project topic thread to start coding."
            )
        except PrivateTopicsUnavailableError:
            await update.message.reply_text(
                manager.private_topics_unavailable_message(),
                parse_mode="HTML",
            )
            if audit_logger:
                await audit_logger.log_command(
                    user_id=user.id,
                    command="start",
                    args=[],
                    success=False,
                )
            return
        except Exception as e:
            sync_section = (
                "\n\n⚠️ <b>Topic Sync Warning</b>\n"
                f"{escape_html(str(e))}\n\n"
                "Run <code>/sync_threads</code> to retry."
            )

    welcome_message = (
        f"👋 Welcome to Claude Code Telegram Bot, {escape_html(user.first_name)}!\n\n"
        f"🤖 I help you access Claude Code remotely through Telegram.\n\n"
        f"<b>Available Commands:</b>\n"
        f"• <code>/help</code> - Show detailed help\n"
        f"• <code>/new</code> - Start a new Claude session\n"
        f"• <code>/ls</code> - List files in current directory\n"
        f"• <code>/cd &lt;dir&gt;</code> - Change directory\n"
        f"• <code>/projects</code> - Show available projects\n"
        f"• <code>/status</code> - Show session status\n"
        f"• <code>/actions</code> - Show quick actions\n"
        f"• <code>/git</code> - Git repository commands\n\n"
        f"<b>Quick Start:</b>\n"
        f"1. Use <code>/projects</code> to see available projects\n"
        f"2. Use <code>/cd &lt;project&gt;</code> to navigate to a project\n"
        f"3. Send any message to start coding with Claude!\n\n"
        f"🔒 Your access is secured and all actions are logged.\n"
        f"📊 Use <code>/status</code> to check your usage limits."
        f"{sync_section}"
    )

    # Add quick action buttons
    keyboard = [
        [
            InlineKeyboardButton(
                "📁 Show Projects", callback_data="action:show_projects"
            ),
            InlineKeyboardButton("❓ Get Help", callback_data="action:help"),
        ],
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton("📊 Check Status", callback_data="action:status"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message, parse_mode="HTML", reply_markup=reply_markup
    )

    # Log command
    if audit_logger:
        await audit_logger.log_command(
            user_id=user.id, command="start", args=[], success=True
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "🤖 <b>Claude Code Telegram Bot Help</b>\n\n"
        "<b>Navigation Commands:</b>\n"
        "• <code>/ls</code> - List files and directories\n"
        "• <code>/cd &lt;directory&gt;</code> - Change to directory\n"
        "• <code>/pwd</code> - Show current directory\n"
        "• <code>/projects</code> - Show available projects\n\n"
        "<b>Session Commands:</b>\n"
        "• <code>/new</code> - Clear context and start a fresh session\n"
        "• <code>/continue [message]</code> - Explicitly continue last session\n"
        "• <code>/end</code> - End current session and clear context\n"
        "• <code>/status</code> - Show session and usage status\n"
        "• <code>/export</code> - Export session history\n"
        "• <code>/actions</code> - Show context-aware quick actions\n"
        "• <code>/git</code> - Git repository information\n\n"
        "<b>Session Behavior:</b>\n"
        "• Sessions are automatically maintained per project directory\n"
        "• Switching directories with <code>/cd</code> resumes the session for that project\n"
        "• Use <code>/new</code> or <code>/end</code> to explicitly clear session context\n"
        "• Sessions persist across bot restarts\n\n"
        "<b>Usage Examples:</b>\n"
        "• <code>cd myproject</code> - Enter project directory\n"
        "• <code>ls</code> - See what's in current directory\n"
        "• <code>Create a simple Python script</code> - Ask Claude to code\n"
        "• Send a file to have Claude review it\n\n"
        "<b>File Operations:</b>\n"
        "• Send text files (.py, .js, .md, etc.) for review\n"
        "• Claude can read, modify, and create files\n"
        "• All file operations are within your approved directory\n\n"
        "<b>Security Features:</b>\n"
        "• 🔒 Path traversal protection\n"
        "• ⏱️ Rate limiting to prevent abuse\n"
        "• 📊 Usage tracking and limits\n"
        "• 🛡️ Input validation and sanitization\n\n"
        "<b>Tips:</b>\n"
        "• Use specific, clear requests for best results\n"
        "• Check <code>/status</code> to monitor your usage\n"
        "• Use quick action buttons when available\n"
        "• File uploads are automatically processed by Claude\n\n"
        "Need more help? Contact your administrator."
    )

    await update.message.reply_text(help_text, parse_mode="HTML")


async def sync_threads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Synchronize project topics in the configured forum chat."""
    settings: Settings = context.bot_data["settings"]
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")
    user_id = update.effective_user.id

    if not settings.enable_project_threads:
        await update.message.reply_text(
            "ℹ️ <b>Project thread mode is disabled.</b>", parse_mode="HTML"
        )
        return

    manager = context.bot_data.get("project_threads_manager")
    if not manager:
        await update.message.reply_text(
            "❌ <b>Project thread manager not initialized.</b>", parse_mode="HTML"
        )
        return

    status_msg = await update.message.reply_text(
        "🔄 <b>Syncing project topics...</b>", parse_mode="HTML"
    )

    if settings.project_threads_mode == "private":
        if not _is_private_chat(update):
            await status_msg.edit_text(
                "❌ <b>Private Thread Mode</b>\n\n"
                "Run <code>/sync_threads</code> in your private chat with the bot.",
                parse_mode="HTML",
            )
            return
        target_chat_id = update.effective_chat.id
    else:
        if settings.project_threads_chat_id is None:
            await status_msg.edit_text(
                "❌ <b>Group Thread Mode Misconfigured</b>\n\n"
                "Set <code>PROJECT_THREADS_CHAT_ID</code> first.",
                parse_mode="HTML",
            )
            return
        if (
            not update.effective_chat
            or update.effective_chat.id != settings.project_threads_chat_id
        ):
            await status_msg.edit_text(
                "❌ <b>Group Thread Mode</b>\n\n"
                "Run <code>/sync_threads</code> in the configured project threads group.",
                parse_mode="HTML",
            )
            return
        target_chat_id = settings.project_threads_chat_id

    try:
        if not settings.projects_config_path:
            await status_msg.edit_text(
                "❌ <b>Project thread mode is misconfigured</b>\n\n"
                "Set <code>PROJECTS_CONFIG_PATH</code> to a valid YAML file.",
                parse_mode="HTML",
            )
            if audit_logger:
                await audit_logger.log_command(user_id, "sync_threads", [], False)
            return

        registry = load_project_registry(
            config_path=settings.projects_config_path,
            approved_directory=settings.approved_directory,
        )
        manager.registry = registry
        context.bot_data["project_registry"] = registry

        result = await manager.sync_topics(context.bot, chat_id=target_chat_id)
        await status_msg.edit_text(
            "✅ <b>Project topic sync complete</b>\n\n"
            f"• Created: <b>{result.created}</b>\n"
            f"• Reused: <b>{result.reused}</b>\n"
            f"• Renamed: <b>{result.renamed}</b>\n"
            f"• Reopened: <b>{result.reopened}</b>\n"
            f"• Closed: <b>{result.closed}</b>\n"
            f"• Deactivated: <b>{result.deactivated}</b>\n"
            f"• Failed: <b>{result.failed}</b>",
            parse_mode="HTML",
        )
        if audit_logger:
            await audit_logger.log_command(user_id, "sync_threads", [], True)
    except PrivateTopicsUnavailableError:
        await status_msg.edit_text(
            manager.private_topics_unavailable_message(),
            parse_mode="HTML",
        )
        if audit_logger:
            await audit_logger.log_command(user_id, "sync_threads", [], False)
    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Project topic sync failed</b>\n\n{escape_html(str(e))}",
            parse_mode="HTML",
        )
        if audit_logger:
            await audit_logger.log_command(user_id, "sync_threads", [], False)


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command - explicitly starts a fresh session, clearing previous context."""
    settings: Settings = context.bot_data["settings"]

    # Get current directory (default to approved directory)
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Track what was cleared for user feedback
    old_session_id = context.user_data.get("claude_session_id")

    # Clear existing session data - this is the explicit way to reset context
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = True
    context.user_data["force_new_session"] = True

    cleared_info = ""
    if old_session_id:
        cleared_info = (
            f"\n🗑️ Previous session <code>{old_session_id[:8]}...</code> cleared."
        )

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Start Coding", callback_data="action:start_coding"
            ),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 Quick Actions", callback_data="action:quick_actions"
            ),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🆕 <b>New Claude Code Session</b>\n\n"
        f"📂 Working directory: <code>{relative_path}/</code>{cleared_info}\n\n"
        f"Context has been cleared. Send a message to start fresh, "
        f"or use the buttons below:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def continue_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /continue command with optional prompt."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse optional prompt from command arguments
    # If no prompt provided, use a default to continue the conversation
    prompt = " ".join(context.args) if context.args else None
    default_prompt = "Please continue where we left off"

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        if not claude_integration:
            await update.message.reply_text(
                "❌ <b>Claude Integration Not Available</b>\n\n"
                "Claude integration is not properly configured."
            )
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id")

        if claude_session_id:
            # We have a session in context, continue it directly
            status_msg = await update.message.reply_text(
                f"🔄 <b>Continuing Session</b>\n\n"
                f"Session ID: <code>{claude_session_id[:8]}...</code>\n"
                f"Directory: <code>{current_dir.relative_to(settings.approved_directory)}/</code>\n\n"
                f"{'Processing your message...' if prompt else 'Continuing where you left off...'}",
                parse_mode="HTML",
            )

            # Continue with the existing session
            # Use default prompt if none provided (Claude CLI requires a prompt)
            claude_response = await claude_integration.run_command(
                prompt=prompt or default_prompt,
                working_directory=current_dir,
                user_id=user_id,
                session_id=claude_session_id,
            )
        else:
            # No session in context, try to find the most recent session
            status_msg = await update.message.reply_text(
                "🔍 <b>Looking for Recent Session</b>\n\n"
                "Searching for your most recent session in this directory...",
                parse_mode="HTML",
            )

            # Use default prompt if none provided
            claude_response = await claude_integration.continue_session(
                user_id=user_id,
                working_directory=current_dir,
                prompt=prompt or default_prompt,
            )

        if claude_response:
            # Update session ID in context
            context.user_data["claude_session_id"] = claude_response.session_id

            # Delete status message and send response
            await status_msg.delete()

            # Format and send Claude's response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

            for msg in formatted_messages:
                await update.message.reply_text(
                    msg.text,
                    parse_mode=msg.parse_mode,
                    reply_markup=msg.reply_markup,
                )

            # Log successful continue
            if audit_logger:
                await audit_logger.log_command(
                    user_id=user_id,
                    command="continue",
                    args=context.args or [],
                    success=True,
                )

        else:
            # No session found to continue
            await status_msg.edit_text(
                "❌ <b>No Session Found</b>\n\n"
                f"No recent Claude session found in this directory.\n"
                f"Directory: <code>{current_dir.relative_to(settings.approved_directory)}/</code>\n\n"
                f"<b>What you can do:</b>\n"
                f"• Use <code>/new</code> to start a fresh session\n"
                f"• Use <code>/status</code> to check your sessions\n"
                f"• Navigate to a different directory with <code>/cd</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🆕 New Session", callback_data="action:new_session"
                            ),
                            InlineKeyboardButton(
                                "📊 Status", callback_data="action:status"
                            ),
                        ]
                    ]
                ),
            )

    except Exception as e:
        error_msg = str(e)
        logger.error("Error in continue command", error=error_msg, user_id=user_id)

        # Delete status message if it exists
        try:
            if "status_msg" in locals():
                await status_msg.delete()
        except Exception:
            pass

        # Send error response
        await update.message.reply_text(
            f"❌ <b>Error Continuing Session</b>\n\n"
            f"An error occurred while trying to continue your session:\n\n"
            f"<code>{error_msg}</code>\n\n"
            f"<b>Suggestions:</b>\n"
            f"• Try starting a new session with <code>/new</code>\n"
            f"• Check your session status with <code>/status</code>\n"
            f"• Contact support if the issue persists",
            parse_mode="HTML",
        )

        # Log failed continue
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="continue",
                args=context.args or [],
                success=False,
            )


async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # List directory contents
        items = []
        directories = []
        files = []

        for item in sorted(current_dir.iterdir()):
            # Skip hidden files (starting with .)
            if item.name.startswith("."):
                continue

            # Escape HTML special characters in filenames
            safe_name = _escape_markdown(item.name)

            if item.is_dir():
                directories.append(f"📁 {safe_name}/")
            else:
                # Get file size
                try:
                    size = item.stat().st_size
                    size_str = _format_file_size(size)
                    files.append(f"📄 {safe_name} ({size_str})")
                except OSError:
                    files.append(f"📄 {safe_name}")

        # Combine directories first, then files
        items = directories + files

        # Format response
        relative_path = current_dir.relative_to(settings.approved_directory)
        if not items:
            message = f"📂 <code>{relative_path}/</code>\n\n<i>(empty directory)</i>"
        else:
            message = f"📂 <code>{relative_path}/</code>\n\n"

            # Limit items shown to prevent message being too long
            max_items = 50
            if len(items) > max_items:
                shown_items = items[:max_items]
                message += "\n".join(shown_items)
                message += f"\n\n<i>... and {len(items) - max_items} more items</i>"
            else:
                message += "\n".join(items)

        # Add navigation buttons if not at root
        keyboard = []
        if current_dir != settings.approved_directory:
            keyboard.append(
                [
                    InlineKeyboardButton("⬆️ Go Up", callback_data="cd:.."),
                    InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    "📁 Projects", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await update.message.reply_text(
            message, parse_mode="HTML", reply_markup=reply_markup
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], True)

    except Exception as e:
        error_msg = f"❌ Error listing directory: {str(e)}"
        await update.message.reply_text(error_msg)

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], False)

        logger.error("Error in list_files command", error=str(e), user_id=user_id)


async def change_directory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    security_validator: SecurityValidator = context.bot_data.get("security_validator")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse arguments
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> <code>/cd &lt;directory&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/cd myproject</code> - Enter subdirectory\n"
            "• <code>/cd ..</code> - Go up one level\n"
            "• <code>/cd /</code> - Go to root of approved directory\n\n"
            "<b>Tips:</b>\n"
            "• Use <code>/ls</code> to see available directories\n"
            "• Use <code>/projects</code> to see all projects",
            parse_mode="HTML",
        )
        return

    target_path = " ".join(context.args)
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    project_root = _get_thread_project_root(settings, context)
    directory_root = project_root or settings.approved_directory

    try:
        # Handle known navigation shortcuts first
        if target_path == "/":
            resolved_path = directory_root
        elif target_path == "..":
            resolved_path = current_dir.parent
            if not _is_within_root(resolved_path, directory_root):
                resolved_path = directory_root
        else:
            # Validate path using security validator
            if security_validator:
                valid, resolved_path, error = security_validator.validate_path(
                    target_path, current_dir
                )

                if not valid:
                    await update.message.reply_text(
                        f"❌ <b>Access Denied</b>\n\n{error}"
                    )

                    # Log security violation
                    if audit_logger:
                        await audit_logger.log_security_violation(
                            user_id=user_id,
                            violation_type="path_traversal_attempt",
                            details=f"Attempted path: {target_path}",
                            severity="medium",
                        )
                    return
            else:
                resolved_path = current_dir / target_path
                resolved_path = resolved_path.resolve()

        if project_root and not _is_within_root(resolved_path, project_root):
            await update.message.reply_text(
                "❌ <b>Access Denied</b>\n\n"
                "In thread mode, navigation is limited to the current project root.",
                parse_mode="HTML",
            )
            return

        # Check if directory exists and is actually a directory
        if not resolved_path.exists():
            await update.message.reply_text(
                f"❌ <b>Directory Not Found</b>\n\n<code>{target_path}</code> does not exist."
            )
            return

        if not resolved_path.is_dir():
            await update.message.reply_text(
                f"❌ <b>Not a Directory</b>\n\n<code>{target_path}</code> is not a directory."
            )
            return

        # Update current directory in user data
        context.user_data["current_directory"] = resolved_path

        # Look up existing session for the new directory instead of clearing
        claude_integration: ClaudeIntegration = context.bot_data.get(
            "claude_integration"
        )
        resumed_session_info = ""
        if claude_integration:
            existing_session = await claude_integration._find_resumable_session(
                user_id, resolved_path
            )
            if existing_session:
                context.user_data["claude_session_id"] = existing_session.session_id
                resumed_session_info = (
                    f"\n🔄 Resumed session <code>{existing_session.session_id[:8]}...</code> "
                    f"({existing_session.message_count} messages)"
                )
            else:
                # No session for this directory - clear the current one
                context.user_data["claude_session_id"] = None
                resumed_session_info = (
                    "\n🆕 No existing session. Send a message to start a new one."
                )

        # Send confirmation
        relative_base = project_root or settings.approved_directory
        relative_path = resolved_path.relative_to(relative_base)
        relative_display = "/" if str(relative_path) == "." else f"{relative_path}/"
        await update.message.reply_text(
            f"✅ <b>Directory Changed</b>\n\n"
            f"📂 Current directory: <code>{relative_display}</code>"
            f"{resumed_session_info}",
            parse_mode="HTML",
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], True)

    except Exception as e:
        error_msg = f"❌ <b>Error changing directory</b>\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode="HTML")

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], False)

        logger.error("Error in change_directory command", error=str(e), user_id=user_id)


async def print_working_directory(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /pwd command."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    relative_path = current_dir.relative_to(settings.approved_directory)
    absolute_path = str(current_dir)

    # Add quick navigation buttons
    keyboard = [
        [
            InlineKeyboardButton("📁 List Files", callback_data="action:ls"),
            InlineKeyboardButton("📋 Projects", callback_data="action:show_projects"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📍 <b>Current Directory</b>\n\n"
        f"Relative: <code>{relative_path}/</code>\n"
        f"Absolute: <code>{absolute_path}</code>",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projects command."""
    settings: Settings = context.bot_data["settings"]

    try:
        if settings.enable_project_threads:
            registry = context.bot_data.get("project_registry")
            manager = context.bot_data.get("project_threads_manager")
            if manager and getattr(manager, "registry", None):
                registry = manager.registry
            if not registry:
                await update.message.reply_text(
                    "❌ <b>Project registry is not initialized.</b>",
                    parse_mode="HTML",
                )
                return

            projects = registry.list_enabled()
            if not projects:
                await update.message.reply_text(
                    "📁 <b>No Projects Found</b>\n\n"
                    "No enabled projects found in projects config.",
                    parse_mode="HTML",
                )
                return

            project_list = "\n".join(
                [
                    f"• <b>{escape_html(p.name)}</b> "
                    f"(<code>{escape_html(p.slug)}</code>) "
                    f"→ <code>{escape_html(str(p.relative_path))}</code>"
                    for p in projects
                ]
            )

            await update.message.reply_text(
                f"📁 <b>Configured Projects</b>\n\n{project_list}",
                parse_mode="HTML",
            )
            return

        # Get directories in approved directory (these are "projects")
        projects = []
        for item in sorted(settings.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await update.message.reply_text(
                "📁 <b>No Projects Found</b>\n\n"
                "No subdirectories found in your approved directory.\n"
                "Create some directories to organize your projects!"
            )
            return

        # Create inline keyboard with project buttons
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for j in range(2):
                if i + j < len(projects):
                    project = projects[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"📁 {project}", callback_data=f"cd:{project}"
                        )
                    )
            keyboard.append(row)

        # Add navigation buttons
        keyboard.append(
            [
                InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        project_list = "\n".join([f"• <code>{project}/</code>" for project in projects])

        await update.message.reply_text(
            f"📁 <b>Available Projects</b>\n\n"
            f"{project_list}\n\n"
            f"Click a project below to navigate to it:",
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error loading projects: {str(e)}")
        logger.error("Error in show_projects command", error=str(e))


async def session_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Get session info
    claude_session_id = context.user_data.get("claude_session_id")
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get session usage info
    usage_info = ""
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    if claude_integration and claude_session_id:
        try:
            session_info = await claude_integration.session_manager.get_session_info(
                claude_session_id
            )
            if session_info:
                turns = session_info.get("turns", 0)
                msgs = session_info.get("messages", 0)
                tools = session_info.get("tools_used", [])
                usage_info = (
                    f"📈 Session: {msgs} messages, {turns} turns\n"
                    f"🔧 Tools: {', '.join(tools[:5]) if tools else 'None'}\n"
                )
        except Exception:
            usage_info = ""

    # Check if there's a resumable session from the database
    resumable_info = ""
    if not claude_session_id:
        claude_integration: ClaudeIntegration = context.bot_data.get(
            "claude_integration"
        )
        if claude_integration:
            existing = await claude_integration._find_resumable_session(
                user_id, current_dir
            )
            if existing:
                resumable_info = (
                    f"🔄 Resumable: <code>{existing.session_id[:8]}...</code> "
                    f"({existing.message_count} msgs)"
                )

    # Format status message
    status_lines = [
        "📊 <b>Session Status</b>",
        "",
        f"📂 Directory: <code>{relative_path}/</code>",
        f"🤖 Claude Session: {'✅ Active' if claude_session_id else '❌ None'}",
        usage_info.rstrip(),
        f"🕐 Last Update: {update.message.date.strftime('%H:%M:%S UTC')}",
    ]

    if claude_session_id:
        status_lines.append(f"🆔 Session ID: <code>{claude_session_id[:8]}...</code>")
    elif resumable_info:
        status_lines.append(resumable_info)
        status_lines.append("💡 Session will auto-resume on your next message")

    # Add action buttons
    keyboard = []
    if claude_session_id:
        keyboard.append(
            [
                InlineKeyboardButton("🔄 Continue", callback_data="action:continue"),
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🆕 Start Session", callback_data="action:new_session"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton("📤 Export", callback_data="action:export"),
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_status"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "\n".join(status_lines), parse_mode="HTML", reply_markup=reply_markup
    )


async def export_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command."""
    update.effective_user.id
    features = context.bot_data.get("features")

    # Check if session export is available
    session_exporter = features.get_session_export() if features else None

    if not session_exporter:
        await update.message.reply_text(
            "📤 <b>Export Session</b>\n\n"
            "Session export functionality is not available.\n\n"
            "<b>Planned features:</b>\n"
            "• Export conversation history\n"
            "• Save session state\n"
            "• Share conversations\n"
            "• Create session backups"
        )
        return

    # Get current session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
            "❌ <b>No Active Session</b>\n\n"
            "There's no active Claude session to export.\n\n"
            "<b>What you can do:</b>\n"
            "• Start a new session with <code>/new</code>\n"
            "• Continue an existing session with <code>/continue</code>\n"
            "• Check your status with <code>/status</code>"
        )
        return

    # Create export format selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("📝 Markdown", callback_data="export:markdown"),
            InlineKeyboardButton("🌐 HTML", callback_data="export:html"),
        ],
        [
            InlineKeyboardButton("📋 JSON", callback_data="export:json"),
            InlineKeyboardButton("❌ Cancel", callback_data="export:cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📤 <b>Export Session</b>\n\n"
        f"Ready to export session: <code>{claude_session_id[:8]}...</code>\n\n"
        "<b>Choose export format:</b>",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /end command to terminate the current session."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
            "ℹ️ <b>No Active Session</b>\n\n"
            "There's no active Claude session to end.\n\n"
            "<b>What you can do:</b>\n"
            "• Use <code>/new</code> to start a new session\n"
            "• Use <code>/status</code> to check your session status\n"
            "• Send any message to start a conversation"
        )
        return

    # Get current directory for display
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear session data
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = False
    context.user_data["last_message"] = None

    # Create quick action buttons
    keyboard = [
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="action:status"),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ <b>Session Ended</b>\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"<b>Current Status:</b>\n"
        f"• Directory: <code>{relative_path}/</code>\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"<b>Next Steps:</b>\n"
        f"• Start a new session with <code>/new</code>\n"
        f"• Check status with <code>/status</code>\n"
        f"• Send any message to begin a new conversation",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

    logger.info("Session ended by user", user_id=user_id, session_id=claude_session_id)


async def quick_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /actions command to show quick actions."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("quick_actions"):
        await update.message.reply_text(
            "❌ <b>Quick Actions Disabled</b>\n\n"
            "Quick actions feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        quick_action_manager = features.get_quick_actions()
        if not quick_action_manager:
            await update.message.reply_text(
                "❌ <b>Quick Actions Unavailable</b>\n\n"
                "Quick actions service is not available."
            )
            return

        # Get context-aware actions
        actions = await quick_action_manager.get_suggestions(
            session_data={"working_directory": str(current_dir), "user_id": user_id}
        )

        if not actions:
            await update.message.reply_text(
                "🤖 <b>No Actions Available</b>\n\n"
                "No quick actions are available for the current context.\n\n"
                "<b>Try:</b>\n"
                "• Navigating to a project directory with <code>/cd</code>\n"
                "• Creating some code files\n"
                "• Starting a Claude session with <code>/new</code>"
            )
            return

        # Create inline keyboard
        keyboard = quick_action_manager.create_inline_keyboard(actions, max_columns=2)

        relative_path = current_dir.relative_to(settings.approved_directory)
        await update.message.reply_text(
            f"⚡ <b>Quick Actions</b>\n\n"
            f"📂 Context: <code>{relative_path}/</code>\n\n"
            f"Select an action to execute:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ <b>Error Loading Actions</b>\n\n{str(e)}")
        logger.error("Error in quick_actions command", error=str(e), user_id=user_id)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command to show git repository information."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await update.message.reply_text(
            "❌ <b>Git Integration Disabled</b>\n\n"
            "Git integration feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await update.message.reply_text(
                "❌ <b>Git Integration Unavailable</b>\n\n"
                "Git integration service is not available."
            )
            return

        # Check if current directory is a git repository
        if not (current_dir / ".git").exists():
            await update.message.reply_text(
                f"📂 <b>Not a Git Repository</b>\n\n"
                f"Current directory <code>{current_dir.relative_to(settings.approved_directory)}/</code> is not a git repository.\n\n"
                f"<b>Options:</b>\n"
                f"• Navigate to a git repository with <code>/cd</code>\n"
                f"• Initialize a new repository (ask Claude to help)\n"
                f"• Clone an existing repository (ask Claude to help)"
            )
            return

        # Get git status
        git_status = await git_integration.get_status(current_dir)

        # Format status message
        relative_path = current_dir.relative_to(settings.approved_directory)
        status_message = "🔗 <b>Git Repository Status</b>\n\n"
        status_message += f"📂 Directory: <code>{relative_path}/</code>\n"
        status_message += f"🌿 Branch: <code>{git_status.branch}</code>\n"

        if git_status.ahead > 0:
            status_message += f"⬆️ Ahead: {git_status.ahead} commits\n"
        if git_status.behind > 0:
            status_message += f"⬇️ Behind: {git_status.behind} commits\n"

        # Show file changes
        if not git_status.is_clean:
            status_message += "\n<b>Changes:</b>\n"
            if git_status.modified:
                status_message += f"📝 Modified: {len(git_status.modified)} files\n"
            if git_status.added:
                status_message += f"➕ Added: {len(git_status.added)} files\n"
            if git_status.deleted:
                status_message += f"➖ Deleted: {len(git_status.deleted)} files\n"
            if git_status.untracked:
                status_message += f"❓ Untracked: {len(git_status.untracked)} files\n"
        else:
            status_message += "\n✅ Working directory clean\n"

        # Create action buttons
        keyboard = [
            [
                InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="git:status"),
                InlineKeyboardButton("📁 Files", callback_data="action:ls"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            status_message, parse_mode="HTML", reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ <b>Git Error</b>\n\n{str(e)}")
        logger.error("Error in git_command", error=str(e), user_id=user_id)


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
        size /= 1024
    return f"{size:.1f}TB"


def _escape_markdown(text: str) -> str:
    """Escape HTML-special characters in text for Telegram.

    Legacy name kept for compatibility with callers; actually escapes HTML.
    """
    return escape_html(text)


async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /usage command - show daily and weekly usage statistics."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    try:
        db_manager = context.bot_data.get("db_manager")
        if not db_manager:
            await update.message.reply_text("❌ 데이터베이스에 연결할 수 없습니다.")
            return

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        async with db_manager.get_connection() as conn:
            # --- Today's stats ---
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as msg_count,
                       COALESCE(SUM(cost), 0) as total_cost,
                       COALESCE(AVG(duration_ms), 0) as avg_duration
                FROM messages
                WHERE user_id = ? AND date(timestamp) = date(?)
                """,
                (user_id, today),
            )
            today_row = await cursor.fetchone()
            today_msgs = today_row[0] if today_row else 0
            today_cost = today_row[1] if today_row else 0.0
            today_avg_ms = today_row[2] if today_row else 0.0

            # --- Today's sessions ---
            cursor = await conn.execute(
                """
                SELECT COUNT(DISTINCT session_id) as session_count
                FROM messages
                WHERE user_id = ? AND date(timestamp) = date(?)
                """,
                (user_id, today),
            )
            today_sessions_row = await cursor.fetchone()
            today_sessions = today_sessions_row[0] if today_sessions_row else 0

            # --- Weekly stats (last 7 days) ---
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as msg_count,
                       COALESCE(SUM(cost), 0) as total_cost,
                       COUNT(DISTINCT date(timestamp)) as active_days
                FROM messages
                WHERE user_id = ? AND date(timestamp) >= date(?)
                """,
                (user_id, week_ago),
            )
            week_row = await cursor.fetchone()
            week_msgs = week_row[0] if week_row else 0
            week_cost = week_row[1] if week_row else 0.0
            week_active_days = week_row[2] if week_row else 0

            # --- Weekly sessions ---
            cursor = await conn.execute(
                """
                SELECT COUNT(DISTINCT session_id) as session_count
                FROM messages
                WHERE user_id = ? AND date(timestamp) >= date(?)
                """,
                (user_id, week_ago),
            )
            week_sessions_row = await cursor.fetchone()
            week_sessions = week_sessions_row[0] if week_sessions_row else 0

            # --- Daily breakdown (last 7 days) ---
            cursor = await conn.execute(
                """
                SELECT date(timestamp) as day,
                       COUNT(*) as msg_count,
                       COALESCE(SUM(cost), 0) as daily_cost
                FROM messages
                WHERE user_id = ? AND date(timestamp) >= date(?)
                GROUP BY date(timestamp)
                ORDER BY day DESC
                """,
                (user_id, week_ago),
            )
            daily_rows = await cursor.fetchall()

            # --- Top tools (last 7 days) ---
            cursor = await conn.execute(
                """
                SELECT tool_name, COUNT(*) as cnt
                FROM tool_usage
                WHERE session_id IN (
                    SELECT DISTINCT session_id FROM messages
                    WHERE user_id = ? AND date(timestamp) >= date(?)
                )
                GROUP BY tool_name
                ORDER BY cnt DESC
                LIMIT 5
                """,
                (user_id, week_ago),
            )
            tool_rows = await cursor.fetchall()

            # --- All-time total ---
            cursor = await conn.execute(
                """
                SELECT COALESCE(SUM(cost), 0) as total_cost,
                       COUNT(*) as total_msgs
                FROM messages WHERE user_id = ?
                """,
                (user_id,),
            )
            all_row = await cursor.fetchone()
            all_cost = all_row[0] if all_row else 0.0
            all_msgs = all_row[1] if all_row else 0

        # --- Fetch Claude Code plan usage (non-blocking) ---
        claude_usage = await _get_claude_usage()

        # --- Build message ---
        lines = []
        lines.append("📊 <b>사용량 리포트</b>")
        lines.append("")

        # Claude Code Plan
        if claude_usage:
            lines.append("━━━ ⚡ <b>Claude Code 플랜</b> ━━━")
            lines.append("📋 플랜: <b>Max (5x)</b>")

            five = claude_usage.get("five_hour") or {}
            seven = claude_usage.get("seven_day") or {}

            if five:
                pct5 = five.get("utilization", 0)
                bar5 = _format_usage_bar(pct5)
                reset5 = _format_reset_time(five.get("resets_at", ""))
                lines.append(
                    f"🕐 5시간: <code>{bar5}</code> <b>{pct5:.0f}%</b> (리셋: {reset5})"
                )

            if seven:
                pct7 = seven.get("utilization", 0)
                bar7 = _format_usage_bar(pct7)
                reset7 = _format_reset_time(seven.get("resets_at", ""))
                lines.append(
                    f"📅 7일간: <code>{bar7}</code> <b>{pct7:.0f}%</b> (리셋: {reset7})"
                )

            lines.append("")

        # Today
        lines.append("━━━ 📅 <b>오늘</b> ━━━")
        lines.append(f"💬 메시지: <b>{today_msgs}</b>건")
        lines.append(f"🔄 세션: <b>{today_sessions}</b>개")
        lines.append(f"💰 비용: <b>${today_cost:.4f}</b>")
        if today_avg_ms > 0:
            lines.append(f"⏱ 평균 응답: <b>{today_avg_ms / 1000:.1f}s</b>")
        lines.append("")

        # Weekly
        lines.append("━━━ 📆 <b>최근 7일</b> ━━━")
        lines.append(f"💬 메시지: <b>{week_msgs}</b>건")
        lines.append(f"🔄 세션: <b>{week_sessions}</b>개")
        lines.append(f"📅 활동일: <b>{week_active_days}</b>일 / 7일")
        lines.append(f"💰 비용: <b>${week_cost:.4f}</b>")
        if week_active_days > 0:
            lines.append(f"📈 일평균: <b>${week_cost / week_active_days:.4f}</b>/일")
        lines.append("")

        # Daily breakdown chart
        if daily_rows:
            lines.append("━━━ 📉 <b>일별 추이</b> ━━━")
            max_msgs = max(row[1] for row in daily_rows) if daily_rows else 1
            for row in daily_rows:
                day_str = row[0]
                msg_count = row[1]
                day_cost = row[2]
                bar_len = int((msg_count / max_msgs) * 8) if max_msgs > 0 else 0
                bar = "█" * bar_len + "░" * (8 - bar_len)
                # Show month/day only
                short_date = day_str[5:]  # "MM-DD"
                lines.append(
                    f"<code>{short_date}</code> {bar} <b>{msg_count}</b>건 ${day_cost:.3f}"
                )
            lines.append("")

        # Top tools
        if tool_rows:
            lines.append("━━━ 🔧 <b>자주 쓴 도구 (7일)</b> ━━━")
            tool_icons = {
                "Read": "📖", "Write": "✏️", "Edit": "📝",
                "Bash": "💻", "Glob": "🔍", "Grep": "🔎",
                "Task": "🤖", "WebFetch": "🌐", "WebSearch": "🔍",
            }
            for row in tool_rows:
                tool_name = row[0]
                tool_count = row[1]
                icon = tool_icons.get(tool_name, "⚙️")
                lines.append(f"{icon} {tool_name}: <b>{tool_count}</b>회")
            lines.append("")

        # All-time
        lines.append(f"🏦 <b>누적</b>: ${all_cost:.4f} ({all_msgs}건)")

        await update.message.reply_text(
            "\n".join(lines), parse_mode="HTML"
        )

    except Exception as e:
        logger.error("Error in usage_command", error=str(e), user_id=user_id)
        await update.message.reply_text(f"❌ 사용량 조회 중 오류: {str(e)}")
