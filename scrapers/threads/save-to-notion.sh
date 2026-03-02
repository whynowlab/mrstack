#!/bin/bash
# Save scraped Threads data to Notion via Claude Code
# Usage: ./save-to-notion.sh <scraper-output.json>

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

INPUT_FILE="$1"
if [ -z "$INPUT_FILE" ]; then
  echo "Usage: ./save-to-notion.sh <scraper-output.json>"
  exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
  echo "File not found: $INPUT_FILE"
  exit 1
fi

POST_COUNT=$(python3 -c "import json; print(len(json.load(open('$INPUT_FILE'))))")
echo "Saving $POST_COUNT posts to Notion..."

# Use Claude Code to save to Notion via MCP
CLAUDECODE= claude --print --output-format text "
Read the file $INPUT_FILE which contains scraped Threads AI posts in JSON format.
Save each post to the Notion database 'AI Threads 수집'.

For each post, create a Notion page with:
- 제목: First 80 chars of the text (clean, no newlines)
- 카테고리: Map category to Korean (model-release→모델출시, tool→AI도구, tip→팁, news→뉴스, research→연구, opinion→의견, general→기타)
- 작성자: author field
- 내용: FULL original text (do NOT truncate)
- 링크: link field (use authorProfile if link is empty)
- 수집일: today's date
- 작성일: time field

Also format the page content nicely with the full post text.
Do this in batches of 20 max per API call.
" 2>/dev/null

echo "Done saving to Notion"
