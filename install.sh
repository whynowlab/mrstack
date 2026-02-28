#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Mr.Stack Installer
# Installs Jarvis mode into claude-code-telegram
# ──────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()  { echo -e "\n${BOLD}→ $1${NC}"; }

echo -e "${BOLD}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║  Mr.Stack Installer               ║"
echo "  ║  Your AI butler, fully stacked.   ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Find claude-code-telegram site-packages ──
step "Detecting claude-code-telegram installation..."

SITE_PKG=""

# Method 1: uv tools (most common)
UV_PATH="$HOME/.local/share/uv/tools/claude-code-telegram"
if [[ -d "$UV_PATH" ]]; then
    # Find the python version directory
    for d in "$UV_PATH"/lib/python3.*/site-packages/src; do
        if [[ -d "$d" ]]; then
            SITE_PKG="$(dirname "$d")"
            break
        fi
    done
fi

# Method 2: pipx
if [[ -z "$SITE_PKG" ]]; then
    PIPX_PATH="$HOME/.local/pipx/venvs/claude-code-telegram"
    if [[ -d "$PIPX_PATH" ]]; then
        for d in "$PIPX_PATH"/lib/python3.*/site-packages/src; do
            if [[ -d "$d" ]]; then
                SITE_PKG="$(dirname "$d")"
                break
            fi
        done
    fi
fi

# Method 3: manual input
if [[ -z "$SITE_PKG" ]]; then
    warn "Auto-detection failed."
    echo "Enter the path to your claude-code-telegram site-packages directory:"
    echo "(It should contain a 'src/' folder with 'bot/', 'config/', etc.)"
    read -r SITE_PKG
    if [[ ! -d "$SITE_PKG/src/bot" ]]; then
        error "Invalid path: $SITE_PKG/src/bot not found"
    fi
fi

SRC="$SITE_PKG/src"
info "Found: $SRC"

# Verify it's a real claude-code-telegram install
if [[ ! -f "$SRC/bot/orchestrator.py" ]]; then
    error "Not a valid claude-code-telegram install: orchestrator.py not found"
fi

# ── Step 2: Check if already installed ──
step "Checking existing installation..."

if [[ -d "$SRC/jarvis" ]]; then
    warn "Mr.Stack (src/jarvis/) already exists."
    read -rp "Overwrite? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    rm -rf "$SRC/jarvis"
fi

# ── Step 3: Copy jarvis module ──
step "Installing jarvis module..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR/src/jarvis" "$SRC/jarvis"
info "Copied src/jarvis/ (5 files)"

# ── Step 4: Patch settings.py ──
step "Patching settings.py..."

SETTINGS="$SRC/config/settings.py"
if grep -q "enable_jarvis" "$SETTINGS" 2>/dev/null; then
    info "enable_jarvis already present — skipping"
else
    # Insert after enable_clipboard_monitor field
    sed -i.bak '/enable_clipboard_monitor.*Field/,/^    )$/{
        /^    )$/a\
    enable_jarvis: bool = Field(\
        False,\
        description="Enable Jarvis proactive context engine",\
    )
    }' "$SETTINGS"
    rm -f "$SETTINGS.bak"
    info "Added enable_jarvis field"
fi

# ── Step 5: Patch main.py ──
step "Patching main.py..."

MAIN="$SRC/main.py"

# 5a: Add jarvis_engine = None
if grep -q "jarvis_engine" "$MAIN" 2>/dev/null; then
    info "jarvis_engine already present — skipping"
else
    # Add variable declaration after clipboard_monitor = None
    sed -i.bak 's/clipboard_monitor = None/clipboard_monitor = None\
    jarvis_engine = None/' "$MAIN"

    # Add startup block after clipboard monitor enabled log
    cat > /tmp/mrstack_main_patch.py << 'PYEOF'
import re

with open("MAIN_FILE", "r") as f:
    content = f.read()

startup_block = '''
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
'''

shutdown_line = '''            if jarvis_engine:
                await jarvis_engine.stop()
'''

# Insert startup block after clipboard monitor
marker = 'logger.info("Clipboard monitor enabled")'
if marker in content:
    content = content.replace(marker, marker + "\n" + startup_block)
else:
    # Fallback: insert before "# Shutdown task"
    content = content.replace("# Shutdown task", startup_block + "\n        # Shutdown task")

# Insert shutdown before clipboard_monitor.stop()
content = content.replace(
    "if clipboard_monitor:\n                await clipboard_monitor.stop()",
    "if jarvis_engine:\n                await jarvis_engine.stop()\n            if clipboard_monitor:\n                await clipboard_monitor.stop()"
)

with open("MAIN_FILE", "w") as f:
    f.write(content)
PYEOF

    sed -i '' "s|MAIN_FILE|$MAIN|g" /tmp/mrstack_main_patch.py
    python3 /tmp/mrstack_main_patch.py
    rm -f /tmp/mrstack_main_patch.py "$MAIN.bak"
    info "Added JarvisEngine lifecycle"
fi

# ── Step 6: Patch orchestrator.py ──
step "Patching orchestrator.py..."

ORCH="$SRC/bot/orchestrator.py"

if grep -q "agentic_jarvis_toggle" "$ORCH" 2>/dev/null; then
    info "Jarvis handlers already present — skipping"
else
    cat > /tmp/mrstack_orch_patch.py << 'PYEOF'
import re

with open("ORCH_FILE", "r") as f:
    content = f.read()

# 1. Add handler registrations
content = content.replace(
    '("clipboard", self.agentic_clipboard_toggle),',
    '("clipboard", self.agentic_clipboard_toggle),\n            ("jarvis", self.agentic_jarvis_toggle),\n            ("coach", self.agentic_coach),'
)

# 2. Add BotCommand entries
content = content.replace(
    'BotCommand("clipboard", "클립보드 인텔리전스"),',
    'BotCommand("clipboard", "클립보드 인텔리전스"),\n                BotCommand("jarvis", "Jarvis 토글"),\n                BotCommand("coach", "코칭 리포트"),'
)

# 3. Add help text
content = content.replace(
    "/clipboard — 클립보드 인텔리전스\\n\"\n",
    '/clipboard — 클립보드 인텔리전스\\n"\n'
    '            "/jarvis — Jarvis 상시 대기 모드\\n"\n'
    '            "/coach — 일일 코칭 리포트\\n"\n'
)

# 4. Add handler methods after agentic_clipboard_toggle
jarvis_methods = '''
    async def agentic_jarvis_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Toggle Jarvis proactive context engine on/off."""
        engine = context.bot_data.get("jarvis_engine")
        if not engine:
            await update.message.reply_text(
                "Jarvis 엔진이 비활성화되어 있습니다.\\n"
                "<code>ENABLE_JARVIS=true</code>를 .env에 추가하세요.",
                parse_mode="HTML",
            )
            return

        new_state = engine.toggle()
        state_str = "ON" if new_state else "OFF"
        desc = (
            "맥락 인식, 패턴 학습, 선제적 알림이 활성화됩니다."
            if new_state
            else "Jarvis 상시 대기를 중지합니다."
        )
        await update.message.reply_text(
            f"Jarvis: <b>{state_str}</b>\\n{desc}",
            parse_mode="HTML",
        )

    async def agentic_coach(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Generate and send daily coaching report."""
        engine = context.bot_data.get("jarvis_engine")
        if not engine:
            await update.message.reply_text(
                "Jarvis 엔진이 비활성화되어 있습니다.\\n"
                "<code>ENABLE_JARVIS=true</code>를 .env에 추가하세요.",
                parse_mode="HTML",
            )
            return

        progress_msg = await update.message.reply_text("코칭 리포트 생성 중...")
        try:
            prompt = engine.coach.generate_report()
            claude_integration = context.bot_data.get("claude_integration")
            if not claude_integration:
                await progress_msg.edit_text("Claude 연동을 사용할 수 없습니다.")
                return

            user_id = update.effective_user.id
            working_dir = context.user_data.get(
                "working_directory", str(self.settings.approved_directory)
            )

            claude_response = await claude_integration.run_command(
                user_id=user_id,
                prompt=prompt,
                working_directory=working_dir,
                force_new=True,
            )

            from .utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(self.settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

            await progress_msg.delete()
            for msg in formatted_messages:
                await update.message.reply_text(
                    msg.text,
                    parse_mode=msg.parse_mode,
                )
        except Exception as e:
            logger.error("Coach report failed", error=str(e))
            await progress_msg.edit_text(f"코칭 리포트 생성 실패: {e}")

'''

# Find the agentic_voice method and insert before it
content = content.replace(
    "    async def agentic_voice(",
    jarvis_methods + "    async def agentic_voice("
)

# 5. Add interaction logging after save_claude_interaction in agentic_text
log_block = '''
            # Jarvis interaction logging
            try:
                jarvis_engine = context.bot_data.get("jarvis_engine")
                if jarvis_engine:
                    duration_ms = int((time.time() - start_time) * 1000)
                    jarvis_engine.pattern_learner.log_interaction(
                        user_id=user_id,
                        prompt=message_text,
                        response=claude_response.content[:500],
                        duration_ms=duration_ms,
                        state=jarvis_engine.current_state,
                    )
            except Exception:
                pass  # Never break main flow for Jarvis logging
'''

# Insert after the save_claude_interaction except block
content = content.replace(
    '                    logger.warning("Failed to log interaction", error=str(e))\n\n            # Format response',
    '                    logger.warning("Failed to log interaction", error=str(e))\n' + log_block + '\n            # Format response'
)

with open("ORCH_FILE", "w") as f:
    f.write(content)
PYEOF

    sed -i '' "s|ORCH_FILE|$ORCH|g" /tmp/mrstack_orch_patch.py
    python3 /tmp/mrstack_orch_patch.py
    rm -f /tmp/mrstack_orch_patch.py
    info "Added /jarvis, /coach commands + interaction logging"
fi

# ── Step 6b: Patch agentic_photo for image vision ──
step "Patching image handler..."

if grep -q "image_prompt" "$ORCH" 2>/dev/null; then
    info "Image vision patch already applied — skipping"
else
    cat > /tmp/mrstack_photo_patch.py << 'PYEOF'
with open("ORCH_FILE", "r") as f:
    content = f.read()

OLD_PHOTO = '''            verbose_level = self._get_verbose_level(context)
            tool_log: List[Dict[str, Any]] = []
            on_stream = self._make_stream_callback(
                verbose_level, progress_msg, tool_log, time.time()
            )

            heartbeat = self._start_typing_heartbeat(chat)
            try:
                claude_response = await claude_integration.run_command(
                    prompt=processed_image.prompt,'''

NEW_PHOTO = '''            # Save image to temp file so Claude can read it with the Read tool
            import tempfile
            import base64 as b64mod

            image_format = processed_image.metadata.get("format", "png") if processed_image.metadata else "png"
            with tempfile.NamedTemporaryFile(
                suffix=f".{image_format}", delete=False, dir=str(current_dir)
            ) as tmp:
                tmp.write(b64mod.b64decode(processed_image.base64_data))
                image_path = tmp.name

            caption = update.message.caption or ""
            image_prompt = (
                f"사용자가 이미지를 보냈습니다. 이미지 파일 경로: {image_path}\\n"
                f"Read 도구로 이 이미지 파일을 읽어서 내용을 확인하고 분석해주세요.\\n"
            )
            if caption:
                image_prompt += f"사용자 메시지: {caption}\\n"
            else:
                image_prompt += "이미지를 분석하고 관련 인사이트를 제공해주세요.\\n"

            verbose_level = self._get_verbose_level(context)
            tool_log: List[Dict[str, Any]] = []
            on_stream = self._make_stream_callback(
                verbose_level, progress_msg, tool_log, time.time()
            )

            heartbeat = self._start_typing_heartbeat(chat)
            try:
                claude_response = await claude_integration.run_command(
                    prompt=image_prompt,'''

if OLD_PHOTO in content:
    content = content.replace(OLD_PHOTO, NEW_PHOTO)

    # Add cleanup after heartbeat.cancel()
    content = content.replace(
        "            finally:\n                heartbeat.cancel()\n\n            if force_new:",
        "            finally:\n                heartbeat.cancel()\n                # Clean up temp image file\n                import os as _os\n                try:\n                    _os.unlink(image_path)\n                except OSError:\n                    pass\n\n            if force_new:",
        1,  # Only replace the first occurrence (in agentic_photo)
    )

    with open("ORCH_FILE", "w") as f:
        f.write(content)
    print("OK")
else:
    print("SKIP: agentic_photo pattern not found")
PYEOF

    sed -i '' "s|ORCH_FILE|$ORCH|g" /tmp/mrstack_photo_patch.py
    RESULT=$(python3 /tmp/mrstack_photo_patch.py)
    rm -f /tmp/mrstack_photo_patch.py
    if [ "$RESULT" = "OK" ]; then
        info "Patched agentic_photo for image vision"
    else
        warn "Could not patch agentic_photo (pattern mismatch) — image vision not applied"
    fi
fi

# ── Step 7: Patch model routing (Sonnet/Haiku for scheduled jobs) ──
step "Patching model routing into pipeline..."

# 7a: ScheduledEvent — add model field
EVENTS_TYPES="$SRC/events/types.py"
if grep -q 'model: Optional' "$EVENTS_TYPES" 2>/dev/null; then
    info "ScheduledEvent.model already present — skipping"
else
    sed -i.bak 's/skill_name: Optional\[str\] = None/skill_name: Optional[str] = None\n    model: Optional[str] = None/' "$EVENTS_TYPES"
    rm -f "$EVENTS_TYPES.bak"
    info "Added model field to ScheduledEvent"
fi

# 7b: scheduler.py — pass model through _fire_event and _load_jobs_from_db
SCHEDULER="$SRC/scheduler/scheduler.py"
if grep -q 'model: Optional' "$SCHEDULER" 2>/dev/null; then
    info "Scheduler model routing already present — skipping"
else
    cat > /tmp/mrstack_scheduler_patch.py << 'PYEOF'
with open("SCHED_FILE", "r") as f:
    content = f.read()

# Patch _fire_event signature
content = content.replace(
    "skill_name: Optional[str],\n    ) -> None:",
    "skill_name: Optional[str],\n        model: Optional[str] = None,\n    ) -> None:"
)

# Patch ScheduledEvent constructor in _fire_event
content = content.replace(
    "skill_name=skill_name,\n        )\n\n        logger.info(\n            \"Scheduled job fired\",",
    "skill_name=skill_name,\n            model=model,\n        )\n\n        logger.info(\n            \"Scheduled job fired\","
)

# Patch _load_jobs_from_db kwargs
content = content.replace(
    '"skill_name": row_dict.get("skill_name"),\n                        },',
    '"skill_name": row_dict.get("skill_name"),\n                            "model": row_dict.get("model"),\n                        },'
)

with open("SCHED_FILE", "w") as f:
    f.write(content)
PYEOF
    sed -i '' "s|SCHED_FILE|$SCHEDULER|g" /tmp/mrstack_scheduler_patch.py
    python3 /tmp/mrstack_scheduler_patch.py
    rm -f /tmp/mrstack_scheduler_patch.py
    info "Patched scheduler for model routing"
fi

# 7c: handlers.py — pass model to run_command
HANDLERS="$SRC/events/handlers.py"
if grep -q 'model=event.model' "$HANDLERS" 2>/dev/null; then
    info "Handler model passthrough already present — skipping"
else
    sed -i.bak 's/user_id=self.default_user_id,\n            )/user_id=self.default_user_id,\n                model=event.model,\n            )/' "$HANDLERS"
    # If sed didn't work (multiline), use python
    if ! grep -q 'model=event.model' "$HANDLERS"; then
        python3 -c "
with open('$HANDLERS', 'r') as f:
    content = f.read()
content = content.replace(
    'user_id=self.default_user_id,\n            )',
    'user_id=self.default_user_id,\n                model=event.model,\n            )',
    1  # Only replace in handle_scheduled, not handle_webhook
)
with open('$HANDLERS', 'w') as f:
    f.write(content)
"
    fi
    rm -f "$HANDLERS.bak"
    info "Patched handler to pass model"
fi

# 7d: facade.py — add model param to run_command and _execute
FACADE="$SRC/claude/facade.py"
if grep -q 'model: Optional\[str\]' "$FACADE" 2>/dev/null; then
    info "Facade model param already present — skipping"
else
    python3 -c "
with open('$FACADE', 'r') as f:
    content = f.read()

# Add model param to run_command
content = content.replace(
    'force_new: bool = False,\n    ) -> ClaudeResponse:',
    'force_new: bool = False,\n        model: Optional[str] = None,\n    ) -> ClaudeResponse:'
)

# Pass model to _execute (both calls)
content = content.replace(
    'stream_callback=stream_handler,\n                )\n            except Exception as resume_error:',
    'stream_callback=stream_handler,\n                    model=model,\n                )\n            except Exception as resume_error:'
)
content = content.replace(
    'stream_callback=stream_handler,\n                    )\n                else:',
    'stream_callback=stream_handler,\n                        model=model,\n                    )\n                else:'
)

# Add model param to _execute
content = content.replace(
    'stream_callback: Optional[Callable] = None,\n    ) -> ClaudeResponse:\n        \"\"\"Execute command via SDK.\"\"\"\n        return await self.sdk_manager.execute_command(',
    'stream_callback: Optional[Callable] = None,\n        model: Optional[str] = None,\n    ) -> ClaudeResponse:\n        \"\"\"Execute command via SDK.\"\"\"\n        return await self.sdk_manager.execute_command('
)

# Pass model in _execute body
content = content.replace(
    'stream_callback=stream_callback,\n        )',
    'stream_callback=stream_callback,\n            model=model,\n        )'
)

with open('$FACADE', 'w') as f:
    f.write(content)
"
    info "Patched facade for model routing"
fi

# 7e: sdk_integration.py — add model to execute_command and ClaudeAgentOptions
SDK="$SRC/claude/sdk_integration.py"
if grep -q 'model=model' "$SDK" 2>/dev/null; then
    info "SDK model param already present — skipping"
else
    python3 -c "
with open('$SDK', 'r') as f:
    content = f.read()

# Add model param to execute_command
content = content.replace(
    'stream_callback: Optional[Callable[[StreamUpdate], None]] = None,\n    ) -> ClaudeResponse:',
    'stream_callback: Optional[Callable[[StreamUpdate], None]] = None,\n        model: Optional[str] = None,\n    ) -> ClaudeResponse:'
)

# Add model to ClaudeAgentOptions
content = content.replace(
    'cli_path=cli_path,\n                sandbox=',
    'cli_path=cli_path,\n                model=model,\n                sandbox='
)

with open('$SDK', 'w') as f:
    f.write(content)
"
    info "Patched SDK for model routing"
fi

# 7f: Add model column to DB if not exists
step "Adding model column to database..."

# Find bot.db
BOT_DB=""
for candidate in \
    "$HOME/claude-telegram/data/bot.db" \
    "$BOT_DIR/data/bot.db"; do
    if [[ -f "$candidate" ]]; then
        BOT_DB="$candidate"
        break
    fi
done

if [[ -n "$BOT_DB" ]]; then
    if sqlite3 "$BOT_DB" "PRAGMA table_info(scheduled_jobs);" | grep -q "model"; then
        info "model column already exists"
    else
        sqlite3 "$BOT_DB" "ALTER TABLE scheduled_jobs ADD COLUMN model TEXT DEFAULT NULL;"
        info "Added model column to scheduled_jobs"
    fi
else
    warn "Could not find bot.db — model column will be created on first run"
fi

# ── Step 8: Patch headless mode (block interactive tools) ──
step "Configuring headless mode..."

SDK="$SRC/claude/sdk_integration.py"
if grep -q 'headless remote bot' "$SDK" 2>/dev/null; then
    info "Headless mode already configured — skipping"
else
    python3 -c "
with open('$SDK', 'r') as f:
    content = f.read()

content = content.replace(
    'f\"All file operations must stay within {working_directory}. \"'
    '\n                    \"Use relative paths.\"',
    'f\"All file operations must stay within {working_directory}. \"'
    '\n                    \"Use relative paths. \"'
    '\n                    \"IMPORTANT: You are running as a headless remote bot via Telegram. \"'
    '\n                    \"There is no human at the terminal to approve interactive prompts. \"'
    '\n                    \"NEVER use interactive tools: EnterPlanMode, ExitPlanMode, AskUserQuestion, Skill. \"'
    '\n                    \"Do NOT ask clarifying questions — make reasonable assumptions and proceed. \"'
    '\n                    \"Do NOT enter plan mode — just execute the task directly.\"'
)

with open('$SDK', 'w') as f:
    f.write(content)
"
    info "Patched system prompt for headless mode"
fi

# Add interactive tools to disallowed list
SETTINGS="$SRC/config/settings.py"
if grep -q 'EnterPlanMode' "$SETTINGS" 2>/dev/null; then
    info "Interactive tools already in disallowed list — skipping"
else
    python3 -c "
with open('$SETTINGS', 'r') as f:
    content = f.read()

content = content.replace(
    'claude_disallowed_tools: Optional[List[str]] = Field(\n        default=[],',
    'claude_disallowed_tools: Optional[List[str]] = Field(\n        default=[\n            \"EnterPlanMode\",\n            \"ExitPlanMode\",\n            \"AskUserQuestion\",\n            \"Skill\",\n            \"EnterWorktree\",\n        ],'
)

with open('$SETTINGS', 'w') as f:
    f.write(content)
"
    info "Added interactive tools to disallowed list"
fi

# ── Step 9: Configure .env ──

step "Configuring environment..."

# Find .env file
ENV_FILE=""
BOT_DIR="$(dirname "$SITE_PKG")"

# Check common locations
for candidate in \
    "$HOME/claude-telegram/.env" \
    "$BOT_DIR/.env" \
    "$SITE_PKG/.env" \
    ".env"; do
    if [[ -f "$candidate" ]]; then
        ENV_FILE="$candidate"
        break
    fi
done

if [[ -z "$ENV_FILE" ]]; then
    warn "Could not find .env file."
    echo "Enter the path to your claude-code-telegram .env file:"
    read -r ENV_FILE
fi

if [[ -f "$ENV_FILE" ]]; then
    # Add ENABLE_JARVIS if not present
    if grep -q "ENABLE_JARVIS" "$ENV_FILE"; then
        info "ENABLE_JARVIS already set"
    else
        echo "" >> "$ENV_FILE"
        echo "# Mr.Stack (Jarvis Mode)" >> "$ENV_FILE"
        echo "ENABLE_JARVIS=true" >> "$ENV_FILE"
        info "Added ENABLE_JARVIS=true"
    fi

    # Check NOTIFICATION_CHAT_IDS
    if grep -q "NOTIFICATION_CHAT_IDS" "$ENV_FILE"; then
        info "NOTIFICATION_CHAT_IDS already configured"
    else
        echo ""
        warn "NOTIFICATION_CHAT_IDS is not set."
        echo "This is your Telegram user ID — Mr.Stack sends proactive notifications here."
        echo "You can find it by messaging @userinfobot on Telegram."
        echo ""
        read -rp "Enter your Telegram user ID (or press Enter to skip): " chat_id
        if [[ -n "$chat_id" ]]; then
            echo "NOTIFICATION_CHAT_IDS=$chat_id" >> "$ENV_FILE"
            info "Set NOTIFICATION_CHAT_IDS=$chat_id"
        else
            warn "Skipped. Mr.Stack won't send proactive notifications until you set this."
        fi
    fi
else
    warn "Could not write to .env. Add these manually:"
    echo "  ENABLE_JARVIS=true"
    echo "  NOTIFICATION_CHAT_IDS=<your_telegram_user_id>"
fi

# ── Step 10: Create memory directory ──
step "Setting up memory directory..."

MEMORY_DIR="$HOME/claude-telegram/memory/patterns"
mkdir -p "$MEMORY_DIR"
info "Created $MEMORY_DIR"

# ── Step 11: Claude HUD (optional) ──
step "Setting up Claude HUD statusline..."

# Check if Node.js is available
NODE_PATH=$(command -v node 2>/dev/null)
if [[ -z "$NODE_PATH" ]]; then
    warn "Node.js not found — skipping Claude HUD setup"
    warn "Install Node.js 18+ and re-run to enable HUD"
else
    HUD_DIR="$HOME/.claude/plugins/cache/claude-hud"
    if [[ -d "$HUD_DIR/dist" ]]; then
        info "Claude HUD already installed"
    else
        info "Installing Claude HUD..."
        git clone https://github.com/jarrodwatts/claude-hud.git "$HUD_DIR" 2>/dev/null || true
        if [[ -d "$HUD_DIR" ]]; then
            cd "$HUD_DIR" && npm install --silent 2>/dev/null
            cd "$SCRIPT_DIR"
            info "Claude HUD installed"
        else
            warn "Failed to clone Claude HUD — skipping"
        fi
    fi

    # Configure statusline in settings.json
    if [[ -d "$HUD_DIR/dist" ]]; then
        SETTINGS_JSON="$HOME/.claude/settings.json"
        HUD_CMD="bash -c '\"$NODE_PATH\" \"\$HOME/.claude/plugins/cache/claude-hud/dist/index.js\"'"

        if [[ -f "$SETTINGS_JSON" ]]; then
            if grep -q "claude-hud" "$SETTINGS_JSON" 2>/dev/null; then
                info "Claude HUD statusline already configured"
            else
                # Use python to safely merge JSON
                python3 -c "
import json
with open('$SETTINGS_JSON', 'r') as f:
    settings = json.load(f)
settings['statusLine'] = {
    'type': 'command',
    'command': '''$HUD_CMD'''
}
with open('$SETTINGS_JSON', 'w') as f:
    json.dump(settings, f, indent=2)
"
                info "Claude HUD statusline configured"
            fi
        else
            mkdir -p "$(dirname "$SETTINGS_JSON")"
            echo "{\"statusLine\":{\"type\":\"command\",\"command\":\"$HUD_CMD\"}}" | python3 -m json.tool > "$SETTINGS_JSON"
            info "Created settings.json with Claude HUD"
        fi

        # Create HUD config
        HUD_CONFIG_DIR="$HOME/.claude/plugins/claude-hud"
        mkdir -p "$HUD_CONFIG_DIR"
        if [[ ! -f "$HUD_CONFIG_DIR/config.json" ]]; then
            cat > "$HUD_CONFIG_DIR/config.json" << 'HUDEOF'
{
  "lineLayout": "expanded",
  "display": {
    "showModel": true,
    "showContextBar": true,
    "showUsage": true,
    "showTools": true,
    "showAgents": true,
    "showTodos": true
  }
}
HUDEOF
            info "Created HUD config"
        fi
    fi
fi

# ── Done ──
echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  Mr.Stack installed successfully!     ${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart your bot"
echo "  2. Mr.Stack is ON by default — no manual activation needed"
echo "  3. Send /jarvis to pause/resume"
echo "  4. Send /coach for a coaching report"
echo "  5. Claude Code statusline shows real-time usage (Claude HUD)"
echo ""
echo -e "${YELLOW}[!] Scheduled jobs (morning briefing, coaching, etc.) need registration.${NC}"
echo "    If you have register-jobs.py, run it now:"
echo "    python3 ~/claude-telegram/schedulers/register-jobs.py"
echo ""
echo "Commands added: /jarvis, /coach"
echo "Data location:  ~/claude-telegram/memory/patterns/"
echo ""
echo -e "GitHub: ${BOLD}github.com/whynowlab/mrstack${NC}"
