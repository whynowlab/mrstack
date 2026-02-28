# Mr.Stack

> Claude Code + Telegram = Your 24/7 AI development partner.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![macOS](https://img.shields.io/badge/macOS-Ventura%20%7C%20Sonoma%20%7C%20Sequoia-black.svg)](https://apple.com/macos)

**Observes your Mac | Remembers conversations | Learns your patterns | Speaks first** — an AI partner that doesn't wait to be asked.

### Quick Start

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack && ./install.sh
# Send any message to your bot on Telegram
```

> Prerequisites: [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) + Telegram bot token ([details below](#prerequisites))

---

## What is Mr.Stack?

An **always-on** Telegram AI partner built on [Claude Code](https://claude.ai).

It extends Claude Code beyond the terminal — through Telegram, it works 24/7, even when your MacBook lid is closed, you're away from your desk, or you're asleep.

> A typical AI assistant sits in an office waiting for your call.
> Mr.Stack is more like **a senior colleague sitting next to you, looking at the same screen**.

Three pillars:
- **Proactive alerts** — Scans your Mac every 5 minutes and reaches out via Telegram when something needs attention
- **Persistent memory** — Remembers conversations and carries context across sessions
- **Pattern learning** — Analyzes your work habits and sends data-driven coaching every night

---

## Key Features

### 1. Telegram AI Assistant
Give Claude instructions with a single Telegram message.

- Write / edit / debug / refactor code
- Process files, photos (image recognition), and voice messages
- Voice in, voice out (Whisper + TTS)
- Auto-analyze clipboard content (error → root cause, URL → summary, code → review)

### 2. Memory System — An AI That Doesn't Forget

Most AIs have **goldfish memory**. Close the window, everything resets.
Mr.Stack separates **working memory (volatile)** from **long-term memory (persistent)**, much like the human brain.

#### Working Memory (Volatile)
- **Context snapshots**: Last 1 hour of system state (in-memory only, 12-slot ring buffer)
- **Current session**: Lives within Claude's context window
- **Recent interactions**: Last 7 days from `interactions.jsonl` → used for pattern analysis

#### Long-Term Memory (Persistent)
Every 3 hours, recent conversations are analyzed and **only meaningful information is extracted** for permanent storage:

```
~/claude-telegram/memory/
  people/          → People mentioned in conversations (overwrite)
  projects/        → Project progress and technical decisions (overwrite)
  decisions/       → Decisions and their reasoning (append)
  preferences/     → Your preferences — coding style, tools, language (overwrite)
  daily/           → Daily summary archive (1 file per day)
  knowledge/       → Newly acquired knowledge (overwrite)
  patterns/        → Work pattern data (interactions.jsonl)
```

The key insight: **it updates, not accumulates.** Like Git's HEAD, `people/`, `projects/`, and `preferences/` always maintain **only the latest snapshot**. Files don't grow forever.

The only append-mode data is `daily/` (1 per day, ~1KB) and `interactions.jsonl` (~300B per conversation). After a full year of use, **total storage is 10–15MB**.

Say "continue what I was working on yesterday" and it picks up exactly where you left off.

### 3. Always-On System (Jarvis Mode)

Like a linter watching your code in real-time, Mr.Stack **scans your entire Mac every 5 minutes**:

- Active application (osascript)
- Battery level and charging state (pmset)
- CPU load (sysctl)
- Git branch and working tree status
- Chrome active tabs
- Recent terminal commands

From this data, your current context is classified into **7 states**:

```
CODING · BROWSING · MEETING · COMMUNICATION · BREAK · DEEP_WORK · AWAY
```

Based on state classification, **7 triggers fire proactively**:

| Situation | Mr.Stack's Response |
|-----------|-------------------|
| Battery below 20% | "Battery at 12% — save your work" |
| Returned from away | "Welcome back. You were on the feature/auth branch" |
| 3+ hours of continuous coding | "You've been coding for 3 hours — take a break" |
| 5+ app switches in 10 min | "Too many context switches. Try to focus" |
| Same file for 30 min, no commits | "Are you stuck? Need help?" |
| Terminal error detected | "Want me to analyze that error?" |
| Deep work mode (2+ hours focused) | Only critical alerts pass through |

Each trigger has a **debounce cooldown**. No alert spam.
During deep work: **interrupt masking** — everything blocked except battery warnings.

### 4. Pattern Learning — Logs Become Insights

Every conversation is logged as a structured event in `interactions.jsonl`:

```json
{
  "ts": "2026-02-28T10:00:00",
  "hour": 10,
  "state": "CODING",
  "request_type": "debug",
  "duration_ms": 5200,
  "tools_used": ["Read", "Edit", "Bash"]
}
```

Like Prometheus collecting metrics, these logs are analyzed as time-series data:
- **Peak hours**: "Most productive between 10–12" (max throughput window)
- **Request type distribution**: "40% debugging, 30% features, 20% questions" (work profiling)
- **Pattern detection**: "Requests weekly planning every Monday at 10am" (recurring event detection)
- **Routine learning**: Confidence > 0.7 triggers preemptive preparation (predictive prefetching)

### 5. Daily Coaching Report

Every night, a report like this arrives via Telegram:

```
[Daily Coach] 2026-02-28

Productivity: 8/10 (+1 from yesterday)

What went well:
• 2-hour focus block in the morning → 4 commits
• Clear specs → 0 rework

Areas to improve:
• 7 context switches between 2–4pm — least efficient window
  → Tomorrow: try a single-task block during this time
• 40% debugging ratio — writing tests first could cut this in half

Weekly trend:
• Instruction clarity improving (2.1 → 2.6)
• Most productive hours: 10–12 (consistent)
```

What a scrum master should say during sprint retro — **delivered nightly, backed by data.**
No flattery, just numbers. Manual access via `/coach`.

### 6. Context-Aware Tone (Persona Layer)

The same information should be delivered differently depending on context. Terse while coding, summary-first when returning.

| State | Tone | Example |
|-------|------|---------|
| Coding | Technical, concise | `"auth.py:42 — missing null check"` |
| Deep work | Silent (urgent only) | — |
| Returning from break | Warm, summary | `"Welcome back. PR #23 awaiting review"` |
| After 10pm | Concerned | `"You've done enough today. Pick it up tomorrow"` |

### 7. Scheduled Jobs (9 cron-based automations)

Like a CI/CD pipeline — configure once, runs automatically on schedule.

| Job | Schedule | Model |
|-----|----------|-------|
| Morning briefing (calendar + tasks + news) | Weekdays 08:00 | Sonnet |
| Evening summary + coaching report | Daily 21:00 | Opus |
| Weekly review | Fridays 18:00 | Opus |
| Calendar reminder | Weekdays 09/12/15/18 | Haiku |
| Conversation → memory auto-update | Every 3 hours | Sonnet |
| GitHub notification check | Every 2 hours | Haiku |
| Notion work log sync | Daily 22:00 | Sonnet |
| AI news summary + Notion save | Daily 08:30, 20:30 | Sonnet |
| OAuth token expiry monitor | Daily 10:00 | Haiku |

> **Model routing**: Automatically selects the right model per job complexity. Simple lookups (Haiku) → analysis/summary (Sonnet) → deep reflection (Opus). Reduces overnight usage by 60–70%.

### 8. External Integrations (MCP)

Mr.Stack connects to external services via MCP (Model Context Protocol).
**Each service is optional** — core features work fine without them.

| Service | Capability | Setup |
|---------|-----------|-------|
| **Google Calendar** | View/create events, reminders | Google Cloud OAuth 2.0 |
| **Notion** | Automatic work log recording | Notion Integration API key |
| **GitHub** | PR, issue, notification monitoring | `gh auth login` (CLI auth) |
| **Playwright** | Web automation | `npx playwright install` |
| **AppleScript** | macOS control | Accessibility permission |

Jobs for unconnected services are automatically skipped (no errors).

---

## How Is This Different?

| | Typical AI Bot | Mr.Stack |
|---|---------------|----------|
| **Interaction** | Request-response (must be asked) | **Event-driven (proactive alerts on conditions)** |
| **Security** | API keys sent to external servers | **Runs only on your Mac. Zero servers** |
| **Availability** | Tied to terminal session | **macOS daemon — 24h even with lid closed** |
| **Memory** | Stateless (session end = reset) | **Persistent memory (permanent storage, context carried)** |
| **Learning** | None | **Time-series pattern analysis + routine prediction** |
| **Coaching** | None | **Daily productivity metrics + data-driven suggestions** |
| **Data** | Cloud storage | **100% local (SQLite, JSONL, Markdown)** |

---

## Prerequisites

Before you begin:

| Requirement | Description | Where |
|-------------|-------------|-------|
| **macOS** | Apple Silicon or Intel | — |
| **Claude Code** | Anthropic's AI coding tool (Max plan recommended) | [claude.ai/download](https://claude.ai/download) |
| **Telegram account** | Messenger to communicate with the bot | [telegram.org](https://telegram.org) |
| **Telegram Bot Token** | Create a bot via BotFather | Send `/newbot` to [@BotFather](https://t.me/botfather) |
| **Telegram User ID** | Your ID for receiving notifications | Send any message to [@userinfobot](https://t.me/userinfobot) |
| **claude-code-telegram** | Base bot framework | [github.com/nicepkg/claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) |

### Get Your Telegram Bot Token (2 min)

1. Search for [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot`
3. Enter a bot name (e.g., `My Stack Bot`)
4. Enter a bot username (e.g., `my_stack_bot`)
5. Save the token (`1234567890:ABCdef...`)

### Find Your Telegram User ID (30 sec)

1. Search for [@userinfobot](https://t.me/userinfobot) in Telegram
2. Send any message
3. Save the numeric ID

---

## Installation

Choose one of two methods:

### Method A: Manual Install

#### Step 1: Install the base bot

Install [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) first.

```bash
uv tool install claude-code-telegram
```

Configure your `.env` file and verify the bot runs correctly.

#### Step 2: Install Mr.Stack

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
./install.sh
```

The install script automatically:
- Locates your claude-code-telegram install path (uv / pipx)
- Copies the Jarvis module
- Patches 3 config files
- Adds `ENABLE_JARVIS=true` to `.env`
- Prompts for your Telegram User ID
- Creates the memory directory

#### Step 3: Restart the bot

```bash
# If running as a launchd daemon:
launchctl stop <your-service-name>
launchctl start <your-service-name>

# If running manually:
# Stop the process and restart
```

#### Step 4: Verify

```bash
curl http://localhost:8080/health   # If API server is enabled
```

Send any message to your bot on Telegram.
`/jarvis` — check status | `/coach` — coaching report

---

### Method B: Install with Claude Code

If you have Claude Code installed, open it in your terminal and say:

```
Look at github.com/whynowlab/mrstack and install Mr.Stack for me.
```

Claude Code will read the README and install.sh, then guide you through setup.
If you don't have the base bot (claude-code-telegram) yet, just ask Claude to install that too.

---

### (Optional) External Service Integrations

MCP integrations are **optional**. Mr.Stack's core features work without them.
Set up only the services you need.

<details>
<summary><b>Google Calendar</b></summary>

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Calendar API
3. Create OAuth 2.0 Client ID (Desktop app)
4. Add `client_id` and `client_secret` to MCP config
5. Register the Google Calendar server in `mcp-config.json`:
```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-google-calendar"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-client-id",
        "GOOGLE_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```
6. Enable MCP in `.env`:
```bash
ENABLE_MCP=true
MCP_CONFIG_PATH=/path/to/mcp-config.json
```
</details>

<details>
<summary><b>Notion</b></summary>

1. Create a new integration at [Notion Integrations](https://www.notion.so/my-integrations)
2. Copy the Internal Integration Token
3. In your target Notion database, click "Connect" → add the integration
4. Add to `mcp-config.json`:
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-notion"],
      "env": {
        "NOTION_API_KEY": "ntn_your_api_key"
      }
    }
  }
}
```
</details>

<details>
<summary><b>GitHub</b></summary>

The easiest one. In your terminal:
```bash
gh auth login
```
That's it. Mr.Stack uses the `gh` CLI to check GitHub notifications, PRs, and issues.
</details>

<details>
<summary><b>Playwright (Web Automation)</b></summary>

```bash
npx playwright install chromium
```
</details>

---

## Commands

| Command | Description |
|---------|-------------|
| `/new` | Start new conversation |
| `/status` | Session & cost overview |
| `/repo` | Switch project |
| `/jobs` | List scheduled jobs |
| `/usage` | Usage report |
| `/help` | Command reference |
| `/verbose` | Output verbosity (0/1/2) |
| `/voice` | Toggle voice responses |
| `/clipboard` | Clipboard auto-analysis |
| `/jarvis` | Pause/resume Jarvis |
| `/coach` | Daily coaching report |
| `/propose` | Spec-based change proposal |
| `/apply` | Execute spec implementation |
| `/archive` | Archive completed work |
| `/explore` | Exploration mode |

---

## Data & Privacy

- All data stored **only on your Mac** (`~/claude-telegram/memory/`)
- No external server transmissions. No cloud. No telemetry. **Zero-trust architecture.**
- System snapshots are refreshed in-memory every 5 min, never persisted to disk
- Claude API calls only on trigger activation (max 10/hour, rate-limited)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.11 + asyncio (async event loop) |
| **AI Engine** | Claude Code SDK (Opus / Sonnet / Haiku) |
| **Interface** | Telegram Bot API |
| **Process Management** | macOS LaunchAgent (daemon, auto-restart) |
| **API Server** | FastAPI (health check, webhooks) |
| **Storage** | SQLite (conversations) + JSONL (event logs) + Markdown (memory) |
| **Integrations** | MCP — Google Calendar, Notion, Playwright, AppleScript |
| **Voice** | Whisper (STT) + TTS (speech synthesis) |

---

## Compatibility

| Item | Version |
|------|---------|
| claude-code-telegram | v1.3.0+ |
| Python | 3.11+ |
| macOS | Ventura / Sonoma / Sequoia |

---

## FAQ

### Does it work with the free version of Claude Code?

It works, but Mr.Stack calls Claude for scheduled jobs, Jarvis triggers, and regular conversations, so **Max plan is strongly recommended**. Free plans hit rate limits quickly.

### Do I need an Anthropic API key?

No. It uses Claude Code's built-in authentication. No separate API key or billing required.

### How much does it cost?

Mr.Stack itself is free (open source). You need:
- **Claude Code subscription**: Pro ($20/mo) or Max ($100/mo recommended)
- **Telegram**: Free
- **Server costs**: None (runs on your Mac)

### Does it work on Windows or Linux?

Currently **macOS only**. System state scanning uses macOS-specific tools (osascript, pmset, etc.). Linux support is on the roadmap.

### Does it really work with the MacBook lid closed?

Yes. When registered as a macOS LaunchAgent (daemon):
- Auto-starts on boot
- Auto-restarts on crash
- Runs in background with lid closed (Power Nap / connected to power)
- Accessible via Telegram while you're out

### Is my data sent externally?

**Absolutely not.** All data is stored in local files on your Mac (SQLite, JSONL). No external servers, no cloud storage, no telemetry whatsoever. The only external communication is Claude API calls to Anthropic's servers — identical to how Claude Code itself operates.

### Will installing this break my existing claude-code-telegram setup?

No. `install.sh` only **adds** Jarvis-related code to existing files. All your settings, conversation history, and scheduled jobs are preserved. If Jarvis is already installed, it will ask before overwriting.

### install.sh throws an error

Most common causes:
1. **claude-code-telegram not installed** → Run `uv tool install claude-code-telegram` first
2. **Python below 3.11** → Check with `python3 --version`
3. **Can't find site-packages path** → The script will prompt for manual input

If unresolved, file an issue at [GitHub Issues](https://github.com/whynowlab/mrstack/issues).

### Bot responses are slow

Claude is invoked via the Claude Code SDK, so complex requests can take 30 seconds to 2 minutes. This is Claude's processing time — Mr.Stack's overhead is negligible.

### Jarvis alerts are too frequent

Use `/jarvis` to pause, or increase `_TRIGGER_COOLDOWNS` values in `context_engine.py`. During deep work mode, everything except battery warnings is automatically blocked.

### Does it use a lot of storage? Will data pile up over time?

Mr.Stack separates short-term and long-term memory.

**Short-term (auto-recycled, no disk usage):**
- Context snapshots: 12-slot ring buffer in memory → 0 disk
- Session conversation: lives within Claude's context window only

**Long-term (disk, but barely grows):**
- `people/`, `projects/`, `preferences/` → **Overwrite mode**. Files don't grow; always latest state only
- `daily/` → 1 file/day, ~1KB. 1 year = ~365KB
- `interactions.jsonl` → ~300B per conversation. 50/day for 1 year = ~5MB
- `routines.json` → Periodically refreshed, stays at a few KB

**Estimated storage after 1 year: 10–15MB** (smaller than a single photo)

### Does it consume a lot of tokens?

**Mr.Stack adds about 15–20 Claude API calls per day.** Negligible on a Max plan.

| Component | Token Usage | Details |
|-----------|-----------|---------|
| **5-min polling (system scan)** | **Zero** | Local subprocesses only (osascript, pmset, git) |
| **Pattern logging** | **Zero** | Local JSONL file append |
| **State classification** | **Zero** | Simple if-else branching (app name → state mapping) |
| **Jarvis triggers** | 3–5/day | Only on condition match. Hard cap: 10/hour |
| **Scheduled jobs** | 10–15/day | Model routing auto-selects Haiku/Sonnet |

The most expensive operation (5-min polling) uses zero tokens. Scheduled jobs use **model routing** to assign Haiku for simple tasks and Sonnet for analysis, minimizing cost. Opus is reserved for evening summaries and weekly reviews only.

**Pro plan users** should consider disabling `memory-sync` (every 3h) and `github-check` (every 2h), or extending their intervals:

```bash
# Manage scheduled jobs
~/claude-telegram/schedulers/manage-jobs.sh list              # List all
~/claude-telegram/schedulers/manage-jobs.sh toggle memory-sync   # Toggle off
~/claude-telegram/schedulers/manage-jobs.sh toggle github-check  # Toggle off
```

### Can I use it on multiple Macs?

Install separately on each Mac. To sync memory data, share `~/claude-telegram/memory/` via iCloud or git.

---

## Roadmap

- [ ] Weekly trend visualization report
- [ ] `pip install mrstack` one-line install

---

## Author

**[@thestack_ai](https://www.threads.net/@thestack_ai)**

---

## License

MIT
