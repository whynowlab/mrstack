# Mr.Stack Integration Guide

> **Recommended:** Use `./install.sh` which automates all steps below.
> This guide is for manual installation or for understanding what the installer does.

## What gets installed

**5 new files** → `src/jarvis/`
```
__init__.py          # JarvisEngine facade
persona.py           # Context states + tone builder
context_engine.py    # System polling + triggers
pattern_learner.py   # Interaction logging + patterns
coach.py             # Daily coaching reports
```

**3 patched files:**
```
src/config/settings.py     # +enable_jarvis field
src/main.py                # +JarvisEngine lifecycle (start/stop)
src/bot/orchestrator.py    # +/jarvis, /coach commands + logging hook
```

## Finding your installation path

```bash
# uv (most common)
ls ~/.local/share/uv/tools/claude-code-telegram/lib/python3.*/site-packages/src/

# pipx
ls ~/.local/pipx/venvs/claude-code-telegram/lib/python3.*/site-packages/src/
```

The directory containing `src/` is your `SITE_PKG`. For example:
```
~/.local/share/uv/tools/claude-code-telegram/lib/python3.11/site-packages/
```

## Manual Steps

### Step 1: Copy source files

```bash
cp -r mrstack/src/jarvis/ $SITE_PKG/src/jarvis/
```

### Step 2: Patch settings.py

Add after `enable_clipboard_monitor` field:

```python
enable_jarvis: bool = Field(
    False,
    description="Enable Jarvis proactive context engine",
)
```

### Step 3: Patch main.py

**3a.** Add variable declaration next to `clipboard_monitor = None`:
```python
jarvis_engine = None
```

**3b.** Add startup block after clipboard monitor initialization:
```python
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
```

**3c.** Add shutdown (before `clipboard_monitor.stop()`):
```python
if jarvis_engine:
    await jarvis_engine.stop()
```

### Step 4: Patch orchestrator.py

**4a.** In `_register_agentic_handlers`, add to handlers list:
```python
("jarvis", self.agentic_jarvis_toggle),
("coach", self.agentic_coach),
```

**4b.** In `get_bot_commands`, add:
```python
BotCommand("jarvis", "Jarvis 토글"),
BotCommand("coach", "코칭 리포트"),
```

**4c.** In `agentic_help`, add to help text:
```python
"/jarvis — Jarvis 상시 대기 모드\n"
"/coach — 일일 코칭 리포트\n"
```

**4d.** Add these two methods to the orchestrator class:

```python
async def agentic_jarvis_toggle(
    self, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Toggle Jarvis proactive context engine on/off."""
    engine = context.bot_data.get("jarvis_engine")
    if not engine:
        await update.message.reply_text(
            "Jarvis 엔진이 비활성화되어 있습니다.\n"
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
        f"Jarvis: <b>{state_str}</b>\n{desc}",
        parse_mode="HTML",
    )

async def agentic_coach(
    self, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Generate and send daily coaching report."""
    engine = context.bot_data.get("jarvis_engine")
    if not engine:
        await update.message.reply_text(
            "Jarvis 엔진이 비활성화되어 있습니다.\n"
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
```

**4e.** In `agentic_text`, after `storage.save_claude_interaction()` block:
```python
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
```

### Step 5: Configure .env

```bash
# Required
ENABLE_JARVIS=true

# Required for proactive notifications
NOTIFICATION_CHAT_IDS=<your_telegram_user_id>
```

Find your Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot) on Telegram.

### Step 6: Create memory directory

```bash
mkdir -p ~/claude-telegram/memory/patterns
```

### Step 7: Restart your bot

Mr.Stack starts immediately — no need to run `/jarvis` to activate.
