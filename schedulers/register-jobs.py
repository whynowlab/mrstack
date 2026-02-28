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
        "prompt": """아침 브리핑을 작성해주세요. 다음 순서로:

1. 오늘 날짜와 요일
2. Google Calendar MCP로 오늘 일정 확인 (MCP 도구 사용 가능하면 활용)
3. ~/claude-telegram/memory/ 에서 어제 daily 요약과 pending 항목 확인
4. 최근 ~/claude-telegram/scrapers/threads/output/ 에서 AI 관련 뉴스 요약 (최신 파일 1개)
5. 오늘의 할 일 제안

형식: 간결하게 bullet point로. 한국어로 작성.
~/claude-telegram/templates/morning-briefing.md 템플릿이 있으면 해당 형식을 따라주세요.""",
    },
    {
        "job_name": "evening-summary",
        "cron_expression": "0 21 * * *",
        "model": "opus",
        "prompt": """오늘 하루 일일 요약을 작성하고 저장해주세요.

1. 오늘 대화 내역을 분석해서 핵심 내용 정리
2. 내린 결정사항, 완료한 작업, 새로 알게 된 정보
3. 내일 할 일 또는 이어서 해야 할 것
4. 결과를 ~/claude-telegram/memory/daily/ 폴더에 오늘 날짜(YYYY-MM-DD.md) 파일로 저장
5. ~/claude-telegram/memory/decisions/log.md 에 오늘의 결정사항 추가 (있으면)
6. 중요 프로젝트 진행상황이 있으면 ~/claude-telegram/memory/projects/ 해당 파일 업데이트

7. [Daily Coach] ~/claude-telegram/memory/patterns/interactions.jsonl 파일을 분석해서 코칭 리포트 추가:
   - 오늘 총 요청 수, 요청 유형 분포, 피크 시간대
   - 디버깅 비율이 높으면 지적 (코드 품질 개선 제안)
   - 컨텍스트 전환 패턴 분석 (집중 블록 vs 분산)
   - 직설적 코칭 포인트 2-3개 (개선 방향 + 내일 실천 항목)
   - interactions.jsonl이 없으면 이 섹션은 건너뛰기

한국어로 작성. 파일 저장 후 텔레그램으로도 요약을 보내주세요.
~/claude-telegram/templates/morning-briefing.md 를 참고해 깔끔한 형식으로.""",
    },
    {
        "job_name": "weekly-review",
        "cron_expression": "0 18 * * 5",
        "model": "opus",
        "prompt": """주간 회고를 작성해주세요.

1. ~/claude-telegram/memory/daily/ 에서 이번 주 daily 파일들 읽기
2. 이번 주 성과 요약
3. 주요 결정사항과 그 이유
4. 배운 것 / 개선점
5. 다음 주 계획 제안

~/claude-telegram/templates/weekly-review.md 템플릿이 있으면 해당 형식을 따라주세요.
한국어로 작성.""",
    },
    {
        "job_name": "calendar-check",
        "cron_expression": "0 9,12,15,18 * * 1-5",
        "model": "haiku",
        "prompt": """Google Calendar MCP로 앞으로 3시간 내 일정을 확인해주세요.

일정이 있으면:
- 시간, 제목, 장소(있으면) 알려주기
- 준비가 필요한 미팅이면 간단히 알려주기

일정이 없으면 아무것도 출력하지 마세요 (빈 응답).""",
    },
    {
        "job_name": "threads-notify",
        "cron_expression": "30 8,20 * * *",
        "model": "sonnet",
        "prompt": """~/claude-telegram/scrapers/threads/output/ 에서 최신 JSON 파일을 분석해주세요.

1. 가장 최근 파일 1개 읽기
2. 주요 AI/테크 관련 포스트 요약 (최대 5개)
3. 각 포스트별: 제목/주제, 핵심 내용 1-2줄, 링크(있으면)
4. 전체 트렌드 한줄 요약

5. Notion MCP를 사용해서 "AI 업무 로그" 데이터베이스(data_source_id: 14e322c2-110e-4cce-9a22-f2c529abb54e)에 저장:
   - 제목: "[Threads] YYYY-MM-DD 오전/오후 AI 뉴스"
   - 카테고리: "학습"
   - 날짜: 오늘
   - 요약: 트렌드 한줄 요약
   - content: 위 요약 전체를 Notion Markdown으로 작성
   - Notion MCP 사용 불가시 이 단계는 건너뛰기 (텔레그램 알림은 정상 전송)

새로운 파일이 없거나 이미 브리핑한 파일이면 아무것도 출력하지 마세요.
한국어로 작성.""",
    },
    {
        "job_name": "memory-sync",
        "cron_expression": "0 */3 * * *",
        "model": "sonnet",
        "prompt": """메모리 동기화 작업입니다. 최근 대화를 분석해서 메모리를 업데이트하세요.

1. 최근 대화에서 새로운 사람, 프로젝트, 결정사항, 선호도 정보를 추출
2. 해당하는 메모리 파일 업데이트:
   - 새 사람 → ~/claude-telegram/memory/people/{name}.md
   - 프로젝트 정보 → ~/claude-telegram/memory/projects/{name}.md
   - 새로운 선호도 → ~/claude-telegram/memory/preferences/ 해당 파일
   - 중요 지식 → ~/claude-telegram/memory/knowledge/ 해당 파일
   - 결정사항 → ~/claude-telegram/memory/decisions/log.md에 추가

변경사항이 없으면 아무것도 출력하지 마세요 (빈 응답).""",
    },
    {
        "job_name": "notion-sync",
        "cron_expression": "0 22 * * *",
        "model": "sonnet",
        "prompt": """오늘의 중요 대화와 결정사항을 Notion에 저장해주세요.

1. 오늘 대화 내역에서 중요한 내용 추출 (기술 결정, 프로젝트 진행상황, 학습 내용)
2. Notion MCP를 사용해서 "AI 업무 로그" 데이터베이스(data_source_id: 14e322c2-110e-4cce-9a22-f2c529abb54e)에 새 페이지 생성
3. 페이지 properties: 제목(TITLE), 카테고리(결정/진행/학습/이슈/아이디어), 날짜(오늘), 요약(1-2줄)
4. 페이지 content: 상세 내용을 Notion Markdown으로 작성

Notion MCP가 사용 불가능하면 ~/claude-telegram/memory/daily/ 파일에 기록하고,
Notion 연동 불가 상태를 알려주세요.
한국어로 작성.""",
    },
    {
        "job_name": "github-check",
        "cron_expression": "0 */2 * * *",
        "model": "haiku",
        "prompt": """GitHub 알림을 확인해주세요.

1. `gh notification list` 또는 `gh api notifications` 명령으로 읽지 않은 알림 확인
2. 새 PR, 이슈, 코멘트가 있으면 요약해서 알려주기
3. 중요한 것 (PR review 요청, 멘션, 실패한 CI 등)은 강조 표시

새 알림이 없으면 아무것도 출력하지 마세요 (빈 응답).
한국어로 작성.""",
    },
    {
        "job_name": "token-check",
        "cron_expression": "0 10 * * *",
        "model": "haiku",
        "prompt": """Claude OAuth 토큰 상태를 확인해주세요.

1. ~/.claude/.credentials.json 파일을 읽어서 토큰 정보 확인
2. expiresAt 필드가 있으면 만료 시간 확인
3. 만료까지 7일 이내이면 경고 메시지 전송
4. 만료되었거나 파일이 없으면 즉시 알림: "claude CLI를 한번 실행해서 토큰을 갱신하세요"
5. 토큰이 정상이면 아무것도 출력하지 마세요 (빈 응답)

한국어로 작성.""",
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
