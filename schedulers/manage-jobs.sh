#!/bin/bash
# Manage scheduled jobs in the bot's SQLite database
DB="$HOME/claude-telegram/data/bot.db"

usage() {
  echo "Usage: $0 {list|add|remove|toggle|update-cron}"
  echo ""
  echo "  list                          List all registered jobs"
  echo "  add <name> <cron> <prompt>    Add a new job"
  echo "  remove <job-name>             Remove a job by name"
  echo "  toggle <job-name>             Toggle job active/inactive"
  echo "  update-cron <job-name> <cron> Update a job's cron expression"
  echo ""
  echo "Note: Restart bot after changes for scheduler to reload."
}

case "${1:-}" in
  list)
    echo "=== Scheduled Jobs ==="
    sqlite3 -header -column "$DB" \
      "SELECT job_name, cron_expression, is_active,
              substr(prompt, 1, 50) || '...' as prompt_preview
       FROM scheduled_jobs
       ORDER BY job_name"
    echo ""
    echo "Total: $(sqlite3 "$DB" "SELECT COUNT(*) FROM scheduled_jobs") jobs"
    echo "Active: $(sqlite3 "$DB" "SELECT COUNT(*) FROM scheduled_jobs WHERE is_active=1") jobs"
    ;;

  add)
    if [ $# -lt 4 ]; then
      echo "Usage: $0 add <name> <cron> <prompt>"
      exit 1
    fi
    JOB_NAME="$2"
    CRON="$3"
    PROMPT="$4"
    JOB_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
    NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    sqlite3 "$DB" "INSERT INTO scheduled_jobs
      (job_id, job_name, cron_expression, prompt, target_chat_ids, working_directory, is_active, created_at, updated_at)
      VALUES ('$JOB_ID', '$JOB_NAME', '$CRON', '$PROMPT', 'YOUR_CHAT_ID', '$HOME', 1, '$NOW', '$NOW')"
    echo "Created: $JOB_NAME ($CRON) -> $JOB_ID"
    echo "Restart bot to apply."
    ;;

  remove)
    if [ $# -lt 2 ]; then
      echo "Usage: $0 remove <job-name>"
      exit 1
    fi
    JOB_NAME="$2"
    sqlite3 "$DB" "DELETE FROM scheduled_jobs WHERE job_name='$JOB_NAME'"
    echo "Removed: $JOB_NAME"
    echo "Restart bot to apply."
    ;;

  toggle)
    if [ $# -lt 2 ]; then
      echo "Usage: $0 toggle <job-name>"
      exit 1
    fi
    JOB_NAME="$2"
    sqlite3 "$DB" "UPDATE scheduled_jobs SET is_active = NOT is_active WHERE job_name='$JOB_NAME'"
    STATUS=$(sqlite3 "$DB" "SELECT CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END FROM scheduled_jobs WHERE job_name='$JOB_NAME'")
    echo "$JOB_NAME -> $STATUS"
    echo "Restart bot to apply."
    ;;

  update-cron)
    if [ $# -lt 3 ]; then
      echo "Usage: $0 update-cron <job-name> <new-cron>"
      exit 1
    fi
    JOB_NAME="$2"
    NEW_CRON="$3"
    sqlite3 "$DB" "UPDATE scheduled_jobs SET cron_expression='$NEW_CRON' WHERE job_name='$JOB_NAME'"
    echo "$JOB_NAME cron -> $NEW_CRON"
    echo "Restart bot to apply."
    ;;

  *)
    usage
    exit 1
    ;;
esac
