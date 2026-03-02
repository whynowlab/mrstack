#!/usr/bin/env python3
"""Register scheduled jobs into the bot's SQLite database."""

import sqlite3
import uuid
from datetime import datetime

import os

DB_PATH = os.path.expanduser("~/claude-telegram/data/bot.db")
CHAT_ID = os.environ.get("NOTIFICATION_CHAT_IDS", "YOUR_CHAT_ID")
WORKING_DIR = os.path.expanduser("~")

# Model routing:
#   "sonnet" — simple lookups, status checks, no creative work
#   "opus"   — complex analysis, writing, multi-step reasoning
#   None     — inherit CLI default (opus)

JOBS = [
    {
        "job_name": "morning-briefing",
        "cron_expression": "0 8 * * 1-5",
        "model": "sonnet",
        "prompt": """아침 브리핑:
1. 오늘 날짜/요일
2. Google Calendar MCP로 오늘 일정
3. ~/claude-telegram/memory/ 어제 daily 요약 + pending
4. ~/claude-telegram/scrapers/threads/output/ 최신 AI 뉴스 (1파일)
5. 오늘 할 일 제안

~/claude-telegram/templates/morning-briefing.md 템플릿 참고.""",
    },
    {
        "job_name": "evening-summary",
        "cron_expression": "0 21 * * *",
        "model": "opus",
        "prompt": """일일 요약 작성 + 저장:
1. 오늘 대화 핵심 정리
2. 결정사항, 완료 작업, 새 정보
3. 내일 할 일
4. ~/claude-telegram/memory/daily/YYYY-MM-DD.md 저장
5. decisions/log.md 업데이트 (있으면)
6. projects/ 해당 파일 업데이트 (있으면)
7. [Coach] ~/claude-telegram/memory/patterns/interactions.jsonl 분석:
   - 총 요청 수, 유형 분포, 피크 시간대
   - 디버깅 비율 지적, 컨텍스트 전환 패턴
   - 코칭 포인트 2-3개 (interactions.jsonl 없으면 건너뛰기)

파일 저장 후 텔레그램으로 요약 전송. ~/claude-telegram/templates/morning-briefing.md 형식 참고.""",
    },
    {
        "job_name": "weekly-review",
        "cron_expression": "0 18 * * 5",
        "model": "opus",
        "prompt": """주간 회고:
1. ~/claude-telegram/memory/daily/ 이번 주 파일들
2. 성과 요약
3. 주요 결정사항 + 이유
4. 배운 것 / 개선점
5. 다음 주 계획

~/claude-telegram/templates/weekly-review.md 템플릿 참고.""",
    },
    {
        "job_name": "calendar-check",
        "cron_expression": "0 9,12,15,18 * * 1-5",
        "model": "haiku",
        "prompt": """Google Calendar MCP로 3시간 내 일정 확인.
있으면: 시간, 제목, 장소, 준비사항.
없으면 빈 응답.""",
    },
    {
        "job_name": "threads-notify",
        "cron_expression": "30 8,20 * * *",
        "model": "sonnet",
        "prompt": """~/claude-telegram/scrapers/threads/output/ 최신 JSON 분석:
1. 최근 1파일의 AI/테크 포스트 요약 (최대 5개)
2. 포스트별: 주제, 핵심 1-2줄, 링크
3. 트렌드 한줄 요약
4. Notion MCP → "AI 업무 로그" DB(data_source_id: 14e322c2-110e-4cce-9a22-f2c529abb54e) 저장:
   제목: "[Threads] YYYY-MM-DD 오전/오후 AI 뉴스", 카테고리: "학습"
   (Notion 불가시 건너뛰기)

새 파일 없거나 이미 브리핑한 파일이면 빈 응답.""",
    },
    {
        "job_name": "memory-sync",
        "cron_expression": "0 */3 * * *",
        "model": "sonnet",
        "prompt": """메모리 동기화 — 최근 대화에서 추출:
- 새 사람 → ~/claude-telegram/memory/people/{name}.md
- 프로젝트 → projects/{name}.md
- 선호도 → preferences/
- 지식 → knowledge/
- 결정 → decisions/log.md""",
    },
    {
        "job_name": "notion-sync",
        "cron_expression": "0 22 * * *",
        "model": "sonnet",
        "prompt": """오늘 중요 대화/결정을 Notion 저장:
1. 기술 결정, 진행상황, 학습 내용 추출
2. Notion MCP → "AI 업무 로그" DB(data_source_id: 14e322c2-110e-4cce-9a22-f2c529abb54e)
3. properties: 제목, 카테고리(결정/진행/학습/이슈/아이디어), 날짜, 요약
4. Notion 불가시 ~/claude-telegram/memory/daily/ 기록 + 상태 알림""",
    },
    {
        "job_name": "github-check",
        "cron_expression": "0 */2 * * *",
        "model": "haiku",
        "prompt": """`gh api notifications` 로 읽지 않은 알림 확인.
새 PR/이슈/코멘트 요약. PR review, 멘션, CI 실패 강조.""",
    },
    {
        "job_name": "token-check",
        "cron_expression": "0 10 * * *",
        "model": "haiku",
        "prompt": """~/.claude/.credentials.json 토큰 확인.
만료 7일 이내면 경고. 만료/파일없음이면 "claude CLI 실행하여 갱신" 알림.""",
    },
]


def register():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for job in JOBS:
        # Check if job already exists
        cursor.execute(
            "SELECT job_id FROM scheduled_jobs WHERE job_name = ?",
            (job["job_name"],),
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing job
            cursor.execute(
                """UPDATE scheduled_jobs
                   SET cron_expression = ?, prompt = ?, target_chat_ids = ?,
                       working_directory = ?, model = ?, is_active = 1, updated_at = ?
                   WHERE job_name = ?""",
                (
                    job["cron_expression"],
                    job["prompt"],
                    CHAT_ID,
                    WORKING_DIR,
                    job.get("model"),
                    datetime.now().isoformat(),
                    job["job_name"],
                ),
            )
            print(f"Updated: {job['job_name']} ({job['cron_expression']}) model={job.get('model', 'default')}")
        else:
            # Insert new job
            job_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO scheduled_jobs
                   (job_id, job_name, cron_expression, prompt, target_chat_ids,
                    working_directory, model, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    job_id,
                    job["job_name"],
                    job["cron_expression"],
                    job["prompt"],
                    CHAT_ID,
                    WORKING_DIR,
                    job.get("model"),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            print(f"Created: {job['job_name']} ({job['cron_expression']}) model={job.get('model', 'default')} -> {job_id}")

    conn.commit()
    conn.close()
    print(f"\nDone. {len(JOBS)} jobs registered.")


if __name__ == "__main__":
    register()
