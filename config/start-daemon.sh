#!/bin/bash
# Daemon startup script for launchd (foreground execution)
# Use start.sh for manual/tmux execution instead

cd "$HOME/claude-telegram"

# Load environment variables
set -a
source .env
set +a

# Ensure claude CLI and other tools are in PATH
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# Sleep prevention: only on AC power
# Bot always runs; caffeinate runs alongside only when on AC.
# A background loop checks power state every 60s and toggles caffeinate.

CAFF_PID=""

cleanup() {
    [ -n "$CAFF_PID" ] && kill "$CAFF_PID" 2>/dev/null
    kill "$BOT_PID" 2>/dev/null
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

is_on_ac() {
    pmset -g batt | grep -q "AC Power"
}

# Start the bot in background
claude-telegram-bot &
BOT_PID=$!

# Power monitor loop
while kill -0 "$BOT_PID" 2>/dev/null; do
    if is_on_ac; then
        if [ -z "$CAFF_PID" ] || ! kill -0 "$CAFF_PID" 2>/dev/null; then
            caffeinate -s -i -w "$BOT_PID" &
            CAFF_PID=$!
        fi
    else
        if [ -n "$CAFF_PID" ] && kill -0 "$CAFF_PID" 2>/dev/null; then
            kill "$CAFF_PID" 2>/dev/null
            CAFF_PID=""
        fi
    fi
    sleep 60
done

wait "$BOT_PID"
