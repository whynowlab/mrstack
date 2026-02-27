# Mr.Stack

> Your AI butler that grows with every conversation.
> 대화할수록 성장하는 AI 집사.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

Mr.Stack turns [Claude Code Telegram Bot](https://github.com/nicepkg/claude-code-telegram) into a **proactive, context-aware AI partner** that learns your work patterns and coaches you daily.

It's not a chatbot. It's a butler that watches, learns, and speaks up when it matters.

## What Mr.Stack Does

### Context Engine — always watching, never intrusive
Polls your Mac every 5 minutes (active app, battery, CPU, git status, Chrome tabs) and classifies your state:

```
CODING → BROWSING → MEETING → DEEP_WORK → AWAY → ...
```

7 smart triggers fire only when they matter:

| Trigger | When | What |
|---------|------|------|
| Battery warning | < 20%, not charging | "배터리 12% — 저장하세요" |
| Return from away | Screen unlock detected | "돌아오셨네요. feature/auth 브랜치 작업 중이었습니다" |
| Long coding session | 3hr+ continuous | "3시간째 코딩 중 — 잠깐 쉬어가시죠" |
| Context switch overload | 5+ app switches / 10min | "컨텍스트 전환이 잦습니다. 집중해보세요" |
| Stuck detection | Same file 30min, no commits | "막히신 부분이 있나요?" |
| Terminal error | Error pattern in terminal | Auto-suggests debug |
| Deep work protection | 2hr+ focused coding | Suppresses non-critical notifications |

### Pattern Learner — remembers how you work
Every interaction is logged. Over time, Mr.Stack learns:
- Your peak productivity hours
- Request type distribution (debug / feature / brainstorm / question)
- Context switching patterns
- What you ask for and when

### Daily Coach — direct, no fluff
```
[Daily Coach] 2026-02-28

생산성: 8/10 (어제 대비 +1)

잘한 점:
• 오전 집중 블록 2시간 유지 → 커밋 4개
• 스펙을 구체적으로 줌 → 재작업 0

개선 포인트:
• 14-16시 컨텍스트 전환 7회 — 가장 비효율 구간
• 디버깅 비율 40% — 테스트 먼저 작성하면 절반으로 줄일 수 있음
```

### Persona Layer — adapts tone to context
| State | Tone |
|-------|------|
| CODING | Minimal, technical. `"auth.py:42 — null check 누락"` |
| DEEP_WORK | Silent unless critical |
| BREAK | Warm. `"돌아오셨네요. PR #23 리뷰 대기 중"` |
| Late night (22+) | Concerned. `"오늘 충분히 하셨습니다"` |

## Architecture

```
ContextEngine (5min poll)     PatternLearner (per interaction)
       |                              |
       v                              v
  ContextSnapshot              interactions.jsonl
       |                              |
       +--------→ JarvisEngine ←------+
                      |
              Trigger Rules (7 rules + cooldowns)
                      |
              Claude (only when triggered)
                      |
              Telegram Notification
                      |
              PersonaLayer (tone adapts to state)
```

## Installation

### Prerequisites
- **macOS** (Apple Silicon or Intel)
- **[claude-code-telegram](https://github.com/nicepkg/claude-code-telegram)** installed and running
- **Telegram bot token** from [@BotFather](https://t.me/botfather)

### One-line install

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
./install.sh
```

The installer automatically:
1. Detects your claude-code-telegram installation (uv / pipx)
2. Copies the jarvis module into your bot
3. Patches `settings.py`, `main.py`, `orchestrator.py`
4. Adds `ENABLE_JARVIS=true` to your `.env`
5. Prompts for your Telegram user ID (for proactive notifications)
6. Creates the memory directory

Then restart your bot:
```bash
# If running as a launchd daemon:
launchctl stop <your-service-name>
launchctl start <your-service-name>

# If running directly:
# Stop and re-run your bot process
```

### Verify

```bash
# Check if jarvis module loads
<your-bot-python> -c "from src.jarvis import JarvisEngine; print('OK')"

# Health check (if API server is enabled)
curl http://localhost:8080/health
```

## Commands

| Command | Description |
|---------|-------------|
| `/jarvis` | Pause/resume Mr.Stack (ON by default) |
| `/coach` | Get daily coaching report on demand |

## File Structure

```
src/jarvis/
  __init__.py          # JarvisEngine facade
  persona.py           # ContextState enum + tone builder
  context_engine.py    # 5min polling + state detection + trigger engine
  pattern_learner.py   # Interaction JSONL logging + pattern extraction
  coach.py             # Daily coaching report generator
```

## Data & Privacy

- **All data stays local** — `~/claude-telegram/memory/patterns/`
- No cloud sync, no telemetry, no tracking
- System snapshots rotate every 5 minutes (not stored permanently)
- Claude API is called only when a trigger fires (2-5 times/hour max)
- You own your data. Period.

## Configuration

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENABLE_JARVIS` | Yes | `true` to enable Mr.Stack |
| `NOTIFICATION_CHAT_IDS` | Yes | Your Telegram user ID (for proactive alerts) |

### Customization

**Trigger cooldowns** — edit `context_engine.py`:
```python
_TRIGGER_COOLDOWNS = {
    "battery_warning": 1800,        # 30 min
    "long_coding_session": 3600,    # 1 hour
    "stuck_detection": 3600,        # 1 hour
    ...
}
```

**App-to-state mapping** — edit `context_engine.py`:
```python
_APP_STATE_MAP = {
    "cursor": ContextState.CODING,
    "obsidian": ContextState.BROWSING,
    ...
}
```

**Persona tone** — edit `persona.py` `build_prompt_prefix()`.

**Memory location** — pass `memory_base` to `JarvisEngine()` in `main.py`.

## Compatibility

Tested with:
- claude-code-telegram **v1.3.0+**
- Python **3.11+**
- macOS **Ventura / Sonoma / Sequoia**

## Roadmap

- [ ] Linux support (xdotool / dbus for active window)
- [ ] Calendar integration for meeting prep trigger
- [ ] Weekly trend reports with visualizations
- [ ] Preemptive actions based on learned routines
- [ ] `pip install mrstack` one-line setup

## Built by

**[@thestack_ai](https://www.threads.net/@thestack_ai)** — Building AI tools that actually help.

## License

MIT
