#!/bin/bash
cd "$HOME/claude-telegram"

# Load env for webhook secret
set -a
source .env
set +a

export PATH="$HOME/.local/bin:$PATH"

# Start bot in background, wait for health check, then notify
claude-telegram-bot &
BOT_PID=$!

# Wait for API server to be ready (max 30 seconds)
for i in $(seq 1 30); do
  if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    # Send startup notification via webhook
    curl -s -X POST http://localhost:8080/webhooks/system \
      -H "Authorization: Bearer $WEBHOOK_API_SECRET" \
      -H "Content-Type: application/json" \
      -d '{"event": "bot_started", "message": "Bot online and ready."}' >/dev/null 2>&1
    break
  fi
  sleep 1
done

# Wait for bot process
wait $BOT_PID
