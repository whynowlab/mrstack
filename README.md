# Mr.Stack

> Your AI butler that grows with every conversation.
> 대화할수록 성장하는 AI 집사.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

Mr.Stack turns [Claude Code Telegram Bot](https://github.com/nicepkg/claude-code-telegram) into a **proactive, context-aware AI partner** that learns your work patterns and coaches you daily.

It's not a chatbot. It's a butler that **watches, learns, and speaks up when it matters.**

## What Mr.Stack Does

### Context Engine — always watching, never intrusive
Polls your Mac every 5 minutes (osascript, git, battery, CPU) to understand what you're doing.

```
CODING → BROWSING → MEETING → DEEP_WORK → AWAY → ...
```

7 smart triggers fire only when they matter:

| Trigger | Example |
|---------|---------|
| Battery warning | "배터리 12% — 저장하세요" |
| Return from away | "돌아오셨네요. feature/auth 브랜치 작업 중이었습니다" |
| Long coding session | "3시간째 코딩 중 — 잠깐 쉬어가시죠" |
| Context switch overload | "10분간 앱 전환 7회. 하나에 집중해보세요" |
| Stuck detection | "같은 파일 30분째 커밋 없음. 도움이 필요하신가요?" |
| Terminal error | Auto-detect errors in your terminal |
| Deep work protection | Suppresses non-critical notifications |

### Pattern Learner — remembers how you work
Every interaction is logged to `interactions.jsonl`. Over time, Mr.Stack learns:

- Your peak productivity hours
- Request types (debug vs feature vs brainstorm)
- Context switching patterns
- What time you usually ask for what

### Daily Coach — direct, no fluff
```
[Daily Coach] 2026-02-28

생산성: 8/10

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
| CODING | Minimal, technical. "auth.py:42 — null check 누락" |
| DEEP_WORK | Silent unless critical |
| BREAK | Warm. "돌아오셨네요. PR #23 리뷰 대기 중" |
| Late night (22+) | Concerned. "오늘 충분히 하셨습니다" |

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

## Stack

- **Runtime:** Python 3.11+
- **Base:** [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) (Telegram + Claude Code SDK)
- **AI:** Claude (Anthropic) — called only on meaningful triggers
- **Platform:** macOS (osascript, pmset, sysctl)
- **Data:** Local JSONL files (no cloud, no tracking)

## Installation

### Prerequisites
- macOS
- [Claude Code Telegram Bot](https://github.com/nicepkg/claude-code-telegram) installed and running
- Telegram bot token from [@BotFather](https://t.me/botfather)

### Setup

1. **Clone**
```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
```

2. **Copy Mr.Stack modules into your bot**
```bash
cp -r src/jarvis/ <your-bot-packages>/src/jarvis/
```

3. **Add to your `.env`**
```bash
ENABLE_JARVIS=true
```

4. **Restart your bot**
```bash
launchctl stop com.dd.claude-telegram
launchctl start com.dd.claude-telegram
```

5. **That's it.** Mr.Stack starts watching immediately.

## Commands

| Command | Description |
|---------|-------------|
| `/jarvis` | Pause/resume Mr.Stack |
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

## Data Privacy

- All data stays local (`~/memory/patterns/`)
- No cloud sync, no telemetry, no tracking
- Snapshots rotate every 5 minutes (not stored permanently)
- You own your data. Period.

## Roadmap

- [ ] Linux support (xdotool for active window)
- [ ] Calendar integration for meeting prep trigger
- [ ] Weekly trend reports
- [ ] Preemptive actions (prepare before you ask)
- [ ] `pip install mrstack` one-line setup

## Built by

**[@thestack_ai](https://www.threads.net/@thestack_ai)** — Building AI tools that actually help.

## License

MIT
