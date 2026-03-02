<div align="center">

<img src="assets/logo-256.png" alt="Mr.Stack" width="140" />

# Mr.Stack

**Claude that works while your MacBook sleeps.**

Claude Code + Telegram = Your 24/7 AI development partner

[![PyPI](https://img.shields.io/pypi/v/mrstack.svg)](https://pypi.org/project/mrstack/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![macOS](https://img.shields.io/badge/macOS-Ventura%20%7C%20Sonoma%20%7C%20Sequoia-black.svg)](https://apple.com/macos)
[![Linux](https://img.shields.io/badge/Linux-supported-orange.svg)](#compatibility)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://t.me/botfather)

</div>

---

## 30-Second Install

```bash
uv tool install mrstack        # 1. Install
mrstack init                    # 2. Setup (enter Telegram token + User ID)
mrstack start                   # 3. Go!
```

Send any message to your bot on Telegram. If it replies, you're done.

> No `uv`? Use `pip install mrstack` instead.
> `mrstack init` automatically checks and installs dependencies (including claude-code-telegram).

<details>
<summary><b>All CLI commands</b></summary>

```
mrstack init          # Setup wizard
mrstack start         # Start bot
mrstack start --bg    # Start in background
mrstack stop          # Stop bot
mrstack daemon        # Register as system daemon (auto-start on reboot)
mrstack daemon -u     # Unregister daemon
mrstack status        # Show status
mrstack logs -f       # Follow logs
mrstack config        # Edit settings
mrstack jarvis on/off # Toggle Jarvis mode
mrstack patch         # Re-install modules
mrstack update        # Update to latest version
mrstack version       # Show version info
```

</details>

---

## What is Mr.Stack?

An **always-on** Telegram AI partner built on [Claude Code](https://claude.ai).

It works 24/7 — even when your terminal is closed, your MacBook lid is shut, or you're away.
If Claude Code is chained to the terminal, Mr.Stack is **Claude in your pocket**.

> A typical AI assistant is a call center — it answers only when asked.
> Mr.Stack is **a senior colleague sitting next to you, looking at the same screen**.

---

## Key Features

### 1. Telegram AI Assistant

Give Claude instructions with a single Telegram message.

- Write / edit / debug / refactor code
- Process files, photos, and voice messages
- Voice in, voice out (Whisper + TTS)
- Auto-analyze clipboard content (error → root cause, URL → summary, code → review)

### 2. Learning — Send a Link, Say "Learn This"

**The easiest way to use Mr.Stack.** Drop any link, doc, or file into Telegram and say **"learn this"**.

```
[You]       https://docs.example.com/api-guide
            Learn this

[Mr.Stack]  Analyzed the API guide:
            - Auth: Bearer token
            - Rate limit: 100req/min
            - 12 main endpoints
            Saved to memory. Ask me anything about this API later.
```

PDFs, web pages, code files, images — send anything and it reads and remembers.
Later, ask **"what was the auth method in that API doc?"** and it answers instantly.

### 3. Persistent Memory — An AI That Doesn't Forget

Most AIs reset when you close the window. Mr.Stack **remembers**.

- Every 3 hours, conversations are analyzed and meaningful info is saved permanently
- Project progress, tech decisions, people, preferences — auto-updated
- **"Continue what I was working on yesterday"** → picks up exactly where you left off
- 1 year of use = ~10-15MB total storage (less than a single photo)

```
~/claude-telegram/memory/
  people/       → People info (overwrite)
  projects/     → Project progress (overwrite)
  decisions/    → Decisions and reasoning (append)
  preferences/  → Your preferences (overwrite)
  daily/        → Daily summaries (1/day)
  knowledge/    → Learned knowledge (overwrite)
  patterns/     → Work pattern data
```

### 4. Always-On System (Jarvis Mode)

Scans your Mac **every 5 minutes** and reaches out when something needs attention.

| Situation | Mr.Stack's Response |
|-----------|-------------------|
| Battery below 20% | "Battery at 12% — save your work" |
| Returned from away | "Welcome back. You were on feature/auth branch" |
| 3+ hours of continuous coding | "Take a break" |
| Same file for 30 min, no commits | "Are you stuck?" |
| Deep work mode (2+ hours focused) | Only critical alerts pass through |

> Jarvis works best on macOS. On Linux, CPU/battery/Git monitoring works normally; active app and Chrome tab detection are macOS-only.

### 5. Pattern Learning + Daily Coaching

Analyzes your work habits and sends data-driven coaching every night:

```
[Daily Coach] 2026-02-28

Productivity: 8/10 (+1 from yesterday)

What went well:
  2-hour morning focus block → 4 commits

Areas to improve:
  7 context switches between 2-4pm — least efficient window
  → Try a single-task block during this time tomorrow
```

### 6. Scheduled Automations

Set once, runs daily:

| Job | Schedule |
|-----|----------|
| Morning briefing (calendar + tasks + news) | Weekdays 08:00 |
| Evening summary + coaching report | Daily 21:00 |
| Weekly review | Fridays 18:00 |
| Calendar reminder | Weekdays 09/12/15/18 |
| Conversation → memory auto-update | Every 3 hours |
| GitHub notification check | Every 2 hours |

> Model routing: Haiku for simple lookups, Sonnet for analysis, Opus for deep reviews. Costs auto-optimized.

### 7. Context-Aware Tone

| State | Tone | Example |
|-------|------|---------|
| Coding | Concise | `"auth.py:42 — missing null check"` |
| Deep work | Silent | Urgent only |
| Returning | Summary | `"Welcome back. PR #23 awaiting review"` |
| After 10pm | Concerned | `"You've done enough today"` |

### 8. External Integrations (Optional)

Connect external services via MCP. **Core features work without them.**

| Service | Capability |
|---------|-----------|
| Google Calendar | Events, reminders |
| Notion | Auto work log |
| GitHub | PR/issue/notification monitoring |
| Playwright | Web automation |

---

## How Is This Different?

| | Typical AI Bot | Mr.Stack |
|---|---------------|----------|
| **Interaction** | Responds when asked | **Proactive alerts** |
| **Security** | API keys sent externally | **Runs only on your machine** |
| **Availability** | Tied to terminal | **24/7 background daemon** |
| **Memory** | Resets on close | **Persistent memory** |
| **Learning** | None | **Pattern analysis + routine prediction** |
| **Coaching** | None | **Daily data-driven coaching** |
| **Data** | Cloud | **100% local** |

---

## Installation Details

### Prerequisites

| Need | Where |
|------|-------|
| **Claude Code** | [claude.ai/download](https://claude.ai/download) — Max plan recommended |
| **Telegram account** | [telegram.org](https://telegram.org) |

### Create a Telegram Bot (2 min)

1. Search **[@BotFather](https://t.me/botfather)** in Telegram → send `/newbot`
2. Enter bot name (e.g., `My Stack Bot`)
3. Enter bot username (e.g., `my_stack_bot`)
4. Save the **token** (`1234567890:ABCdef...`)

### Find Your Telegram User ID (30 sec)

1. Send any message to **[@userinfobot](https://t.me/userinfobot)**
2. Save the **numeric ID**

### Install & Start

```bash
uv tool install mrstack    # Install
mrstack init               # Enter token + User ID, auto-configure
mrstack start              # Start!
```

`mrstack init` automatically handles:
- Claude Code installation check
- claude-code-telegram install (if missing)
- `.env` configuration file creation
- Memory directory setup
- Jarvis mode configuration (macOS)

### Run as Background Daemon

```bash
mrstack daemon    # Register system daemon → auto-starts on reboot
```

### Set Bot Profile Photo (Optional)

1. Send `/mybots` to [@BotFather](https://t.me/botfather) → select your bot → Edit Botpic
2. Send `assets/bot-profile.png`

<details>
<summary><b>Advanced: Install from source</b></summary>

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
pip install -e .
mrstack init
```

For development contributions or customization.

</details>

<details>
<summary><b>Advanced: Install with Claude Code</b></summary>

In Claude Code terminal:
```
Look at github.com/whynowlab/mrstack and install Mr.Stack for me.
```

Claude reads the README and guides you through setup.

</details>

<details>
<summary><b>Optional: External service integrations</b></summary>

**Google Calendar**
```json
// mcp-config.json
{
  "mcpServers": {
    "google-calendar": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-google-calendar"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-id",
        "GOOGLE_CLIENT_SECRET": "your-secret"
      }
    }
  }
}
```

**Notion**
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-notion"],
      "env": { "NOTION_API_KEY": "ntn_..." }
    }
  }
}
```

**GitHub** — Just run `gh auth login`.

**Playwright** — `npx playwright install chromium`

</details>

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/new` | Start new conversation |
| `/status` | Session & cost overview |
| `/repo` | Switch project |
| `/jarvis` | Pause/resume Jarvis |
| `/coach` | Daily coaching report |
| `/jobs` | List scheduled jobs |
| `/voice` | Toggle voice responses |
| `/clipboard` | Clipboard auto-analysis |
| `/help` | Full command reference |

---

## Compatibility

| Platform | Support Level |
|----------|--------------|
| **macOS** (Ventura / Sonoma / Sequoia) | 100% — all features |
| **Linux** | 95% — Jarvis active app/Chrome tab detection unavailable, everything else works |
| **Windows (WSL2)** | 95% — same as Linux |
| **Windows (native)** | Roadmap |

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| claude-code-telegram | v1.3.0+ |
| Claude Code | Max plan recommended |

---

## Security & Privacy

- **100% local** — all data stored on your machine only. No external server transmission
- **User auth** — only Telegram IDs in `ALLOWED_USERS` are permitted
- **Sandbox** — Claude's file access restricted to `APPROVED_DIRECTORY`
- **Quality gate** — dangerous commands (`rm -rf`, `sudo`, `curl | sh`) blocked
- Only Claude API calls go through Anthropic servers (same as Claude Code itself)

---

## FAQ

<details>
<summary><b>Does it work with free Claude Code?</b></summary>

It works but hits rate limits quickly. **Max plan strongly recommended.**
Mr.Stack itself is free (open source) with zero server costs.

</details>

<details>
<summary><b>Do I need an Anthropic API key?</b></summary>

No. It uses Claude Code's built-in authentication.

</details>

<details>
<summary><b>Does it really work with the lid closed?</b></summary>

Yes. `mrstack daemon` registers a system daemon:
- Auto-starts on boot, auto-restarts on crash
- Runs in background with lid closed (when connected to power)
- Accessible via Telegram from anywhere

</details>

<details>
<summary><b>Does it use a lot of tokens?</b></summary>

About 15-20 extra API calls per day. Negligible on Max plan.
5-min polling, pattern logging, and state classification use **zero tokens** (local only).

</details>

<details>
<summary><b>Is my data sent externally?</b></summary>

**Absolutely not.** All data in local files (SQLite, JSONL, Markdown).

</details>

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11 + asyncio |
| AI Engine | Claude Code SDK (Opus / Sonnet / Haiku) |
| Interface | Telegram Bot API |
| Process Mgmt | macOS LaunchAgent / Linux systemd |
| Storage | SQLite + JSONL + Markdown |
| Integrations | MCP (Google Calendar, Notion, Playwright) |

---

## Links

- [Threads @thestack_ai](https://www.threads.net/@thestack_ai) — Updates and dev stories
- [GitHub Issues](https://github.com/whynowlab/mrstack/issues) — Bug reports, feature requests
- [PyPI](https://pypi.org/project/mrstack/) — Package
- [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) — Base framework

---

## License

MIT

---

*[한국어 버전 →](README.md)*
