#!/bin/bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

set -a
source "$HOME/claude-telegram/.env"
set +a

# Use Claude Code to generate briefing
CLAUDECODE= claude --print --output-format text "
You are DD's personal assistant. Generate a morning briefing.
Check:
1. Today's calendar events (if Google Calendar MCP available)
2. Unread important emails (if Gmail MCP available)
3. Pending issues/tasks (if Linear/Jira MCP available)
4. Unread Slack mentions (if Slack MCP available)
5. Latest AI news from ~/claude-telegram/scrapers/threads/output/

Format as a concise Telegram message in Korean.
Start with: 🌅 오전 브리핑 (date)
" 2>/dev/null > /tmp/morning-briefing.txt

# Send via Telegram
MSG=$(cat /tmp/morning-briefing.txt)
if [ -n "$MSG" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${NOTIFICATION_CHAT_IDS}\",\"text\":$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
    > /dev/null
fi
