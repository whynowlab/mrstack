#!/bin/bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
cd "$HOME/claude-telegram/scrapers/threads"

# Source env
set -a
source "$HOME/claude-telegram/.env"
set +a

# Run scraper
node scraper.js 2>&1 | tee -a "$HOME/claude-telegram/logs/threads.log"

# Get latest output file
LATEST=$(ls -t output/*.json 2>/dev/null | head -1)

if [ -n "$LATEST" ]; then
  POST_COUNT=$(python3 -c "import json; print(len(json.load(open('$LATEST'))))" 2>/dev/null || echo "0")

  # Send to bot's webhook API for Claude-powered analysis
  WEBHOOK_RESULT=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8080/webhooks/threads \
    -H "Authorization: Bearer $WEBHOOK_API_SECRET" \
    -H "Content-Type: application/json" \
    -d "{\"file\": \"$LATEST\", \"count\": $POST_COUNT}" 2>/dev/null)

  if [ "$WEBHOOK_RESULT" = "200" ] || [ "$WEBHOOK_RESULT" = "202" ]; then
    echo "Webhook sent successfully (HTTP $WEBHOOK_RESULT)" | tee -a "$HOME/claude-telegram/logs/threads.log"
  else
    echo "Webhook failed (HTTP $WEBHOOK_RESULT), falling back to direct briefing" | tee -a "$HOME/claude-telegram/logs/threads.log"
    # Fallback: direct briefing
    node briefing.js "$LATEST" 2>&1 | tee -a "$HOME/claude-telegram/logs/threads.log"
  fi

  # Save to Notion via Claude Code
  bash "$HOME/claude-telegram/scrapers/threads/save-to-notion.sh" "$LATEST" 2>&1 | tee -a "$HOME/claude-telegram/logs/threads.log"
fi
