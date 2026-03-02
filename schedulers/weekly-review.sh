#!/bin/bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

set -a
source "$HOME/claude-telegram/.env"
set +a

CLAUDECODE= claude --print --output-format text "
You are DD's personal assistant. Generate a weekly review.
Check:
1. This week's completed tasks and accomplishments
2. Next week's scheduled events from Google Calendar
3. AI trends summary from ~/claude-telegram/scrapers/threads/output/ (this week's files)
4. Any pending items that need attention

Format as a concise Telegram message in Korean.
Start with: 📊 주간 회고 (date range)
" 2>/dev/null > /tmp/weekly-review.txt

MSG=$(cat /tmp/weekly-review.txt)
if [ -n "$MSG" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${NOTIFICATION_CHAT_IDS}\",\"text\":$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
    > /dev/null
fi
