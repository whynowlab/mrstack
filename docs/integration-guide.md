# Mr.Stack Integration Guide

This guide explains how to integrate Mr.Stack into your [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) bot.

## Overview

Mr.Stack adds 5 files to your bot and modifies 3 existing files:

**New files** → `src/jarvis/`
```
__init__.py          # JarvisEngine facade
persona.py           # Context states + tone builder
context_engine.py    # System polling + triggers
pattern_learner.py   # Interaction logging + patterns
coach.py             # Daily coaching reports
```

**Modified files:**
```
src/config/settings.py     # Add enable_jarvis field
src/main.py                # JarvisEngine lifecycle
src/bot/orchestrator.py    # /jarvis, /coach commands + logging hook
```

## Step 1: Copy Source Files

```bash
cp -r mrstack/src/jarvis/ <your-bot-packages>/src/jarvis/
```

Where `<your-bot-packages>` is your bot's site-packages directory.
For uv-installed bots, this is typically:
```
~/.local/share/uv/tools/claude-code-telegram/lib/python3.11/site-packages/
```

## Step 2: Modify settings.py

Add after `enable_clipboard_monitor`:

```python
enable_jarvis: bool = Field(
    False,
    description="Enable Jarvis proactive context engine",
)
```

## Step 3: Modify main.py

Add `jarvis_engine = None` next to `clipboard_monitor = None`.

After the clipboard_monitor block, add:

```python
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
```

In the shutdown block, add before clipboard_monitor.stop():

```python
if jarvis_engine:
    await jarvis_engine.stop()
```

## Step 4: Modify orchestrator.py

### 4a. Register commands

In `_register_agentic_handlers`, add to the handlers list:
```python
("jarvis", self.agentic_jarvis_toggle),
("coach", self.agentic_coach),
```

### 4b. Add bot commands

In `get_bot_commands`, add:
```python
BotCommand("jarvis", "Jarvis 토글"),
BotCommand("coach", "코칭 리포트"),
```

### 4c. Update help text

In `agentic_help`, add:
```python
"/jarvis — Jarvis 상시 대기 모드\n"
"/coach — 일일 코칭 리포트\n"
```

### 4d. Add handler methods

Add these methods to the orchestrator class (see source for full implementation):
- `agentic_jarvis_toggle()` — toggle engine on/off
- `agentic_coach()` — generate coaching report via Claude

### 4e. Add interaction logging

In `agentic_text`, after `storage.save_claude_interaction()`:
```python
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
    pass
```

## Step 5: Enable

Add to your `.env`:
```bash
ENABLE_JARVIS=true
```

Restart your bot. Mr.Stack starts immediately.

## Customization

### Trigger cooldowns

Edit `context_engine.py` `_TRIGGER_COOLDOWNS` dict:
```python
_TRIGGER_COOLDOWNS = {
    "battery_warning": 1800,        # 30 min
    "long_coding_session": 3600,    # 1 hour
    ...
}
```

### App-to-state mapping

Edit `context_engine.py` `_APP_STATE_MAP` to add your apps:
```python
_APP_STATE_MAP = {
    "cursor": ContextState.CODING,
    "obsidian": ContextState.BROWSING,
    ...
}
```

### Persona tone

Edit `persona.py` `build_prompt_prefix()` to change how Mr.Stack speaks in each state.

### Memory location

Default: `~/claude-telegram/memory/patterns/`

Change by passing `memory_base` to `JarvisEngine()` in `main.py`.
