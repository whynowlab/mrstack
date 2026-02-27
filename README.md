# Mr.Stack

> 대화할수록 성장하는 AI 집사.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Mr.Stack이 뭔가요?

[Claude Code](https://claude.ai) 기반 텔레그램 AI 비서입니다.

터미널에서만 쓰는 Claude Code를 **텔레그램으로 꺼내서**,
맥북을 덮어놔도, 외출 중이어도, 자고 있어도 24시간 동작합니다.

단순한 챗봇이 아닙니다.
**내 맥북을 관찰하고, 내 작업 패턴을 학습하고, 먼저 말을 거는** AI 파트너입니다.

---

## 주요 기능

### 1. 텔레그램 AI 비서
텔레그램 메시지 하나로 Claude에게 지시합니다.

- 코드 작성 / 수정 / 디버깅 / 리팩토링
- 파일, 사진, 음성 메시지 전부 처리
- 음성으로 지시하면 음성으로 답변 (Whisper + TTS)
- 복사한 내용 자동 분석 (에러→원인 분석, URL→요약, 코드→리뷰)

### 2. 상시 대기 시스템 (Jarvis Mode)
5분마다 맥북 상태를 스캔하고, 상황에 맞게 선제적으로 알림을 보냅니다.

| 상황 | Mr.Stack의 반응 |
|------|----------------|
| 배터리 20% 이하 | "배터리 12% — 저장하세요" |
| 자리 비웠다 돌아옴 | "돌아오셨네요. feature/auth 브랜치 작업 중이었습니다" |
| 코딩 3시간 연속 | "3시간째 코딩 중 — 잠깐 쉬어가시죠" |
| 앱 전환 10분에 5번+ | "컨텍스트 전환이 잦습니다. 집중해보세요" |
| 같은 파일 30분, 커밋 없음 | "막히신 부분이 있나요?" |
| 터미널에 에러 감지 | "에러를 분석해드릴까요?" |
| 딥워크 모드 (2시간+ 집중) | 중요한 것만 통과, 나머지 알림 차단 |

### 3. 패턴 학습
매 대화가 기록되고 분석됩니다. 시간이 지나면:

- 내가 가장 생산적인 시간대를 파악
- 요청 유형 분포 (디버깅 / 기능개발 / 질문 / 브레인스톰)
- 컨텍스트 전환 패턴 분석
- 반복되는 루틴 감지 → 선제적 준비

### 4. 일일 코칭 리포트
매일 밤 이런 리포트가 텔레그램으로 옵니다:

```
[Daily Coach] 2026-02-28

생산성: 8/10 (어제 대비 +1)

잘한 점:
• 오전 집중 블록 2시간 유지 → 커밋 4개
• 스펙을 구체적으로 줌 → 재작업 0

개선 포인트:
• 14-16시 컨텍스트 전환 7회 — 가장 비효율 구간
  → 내일은 이 시간에 단일 작업 블록 추천
• 디버깅 비율 40% — 테스트 먼저 작성하면 절반으로 줄일 수 있음
```

아첨 없이 직설적으로. 매일 데이터 기반으로 개선점을 알려줍니다.

### 5. 상황별 톤 조절
Mr.Stack은 지금 내 상태에 맞게 말투를 바꿉니다.

| 상태 | 톤 | 예시 |
|------|-----|------|
| 코딩 중 | 기술적, 간결 | `"auth.py:42 — null check 누락"` |
| 딥워크 | 침묵 (긴급만 전달) | — |
| 휴식 복귀 | 따뜻, 요약 | `"돌아오셨네요. PR #23 리뷰 대기 중"` |
| 밤 10시 이후 | 걱정 | `"오늘 충분히 하셨습니다. 내일 이어하시죠"` |

### 6. 스케줄 작업 (9개 자동 실행)
| 작업 | 시간 |
|------|------|
| 아침 브리핑 (일정+할일+뉴스) | 평일 08:00 |
| 저녁 요약 + 코칭 리포트 | 매일 21:00 |
| 주간 회고 | 금요일 18:00 |
| 캘린더 리마인더 | 평일 09/12/15/18시 |
| 대화 → 메모리 업데이트 | 3시간마다 |
| GitHub 알림 확인 | 2시간마다 |
| Notion 업무 로그 저장 | 매일 22:00 |

### 7. 외부 서비스 연동
- **Google Calendar** — 일정 조회/생성
- **Notion** — 업무 로그 자동 기록
- **GitHub** — PR, 이슈, 알림
- **Playwright** — 웹 자동화
- **AppleScript** — macOS 제어

### 8. 메모리 시스템
대화를 기억합니다. 세션이 끝나도 사라지지 않습니다.

- 사람, 프로젝트, 결정사항, 선호도 자동 분류 저장
- 다음 세션에서 이전 맥락을 이어감
- 쓸수록 나를 더 잘 이해하는 비서로 성장

---

## 기존 솔루션과 뭐가 다른가요?

| | 기존 AI 봇 | Mr.Stack |
|---|-----------|----------|
| **동작 방식** | 물어봐야 답함 | **먼저 알림을 보냄** |
| **보안** | API 키를 외부 서버에 전송 | **내 맥북에서만 동작. 서버 없음** |
| **상시성** | 터미널 열어야 사용 | **맥북 덮어도 24시간 동작** |
| **학습** | 매번 새로 시작 | **대화가 쌓일수록 성장** |
| **코칭** | 없음 | **매일 생산성 분석 + 개선 제안** |
| **데이터** | 클라우드 저장 | **100% 로컬 (SQLite, JSONL)** |

---

## 준비물

시작하기 전에 이것들이 필요합니다:

| 준비물 | 설명 | 어디서 |
|--------|------|--------|
| **macOS** | Apple Silicon 또는 Intel | — |
| **Claude Code** | Anthropic의 AI 코딩 도구 (Max 플랜 권장) | [claude.ai/download](https://claude.ai/download) |
| **Telegram 계정** | 봇에게 지시를 보낼 메신저 | [telegram.org](https://telegram.org) |
| **Telegram Bot Token** | BotFather에서 봇 생성 후 발급 | [@BotFather](https://t.me/botfather)에게 `/newbot` 전송 |
| **Telegram User ID** | 알림을 받을 내 ID | [@userinfobot](https://t.me/userinfobot)에게 아무 메시지 전송 |
| **claude-code-telegram** | 기반 봇 프레임워크 | [github.com/nicepkg/claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) |

### Telegram Bot Token 받기 (2분)

1. Telegram에서 [@BotFather](https://t.me/botfather) 검색
2. `/newbot` 입력
3. 봇 이름 입력 (예: `My Stack Bot`)
4. 봇 username 입력 (예: `my_stack_bot`)
5. 받은 토큰 (`1234567890:ABCdef...`) 저장

### Telegram User ID 확인 (30초)

1. Telegram에서 [@userinfobot](https://t.me/userinfobot) 검색
2. 아무 메시지 전송
3. 받은 숫자 ID 저장

---

## 설치

### 1단계: 기반 봇 설치

[claude-code-telegram 설치 가이드](https://github.com/nicepkg/claude-code-telegram)를 따라 기반 봇을 먼저 설치합니다.

```bash
uv tool install claude-code-telegram
```

`.env` 파일을 설정하고 봇이 정상 동작하는지 확인합니다.

### 2단계: Mr.Stack 설치

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
./install.sh
```

설치 스크립트가 자동으로:
- claude-code-telegram 설치 경로를 찾습니다 (uv / pipx)
- Jarvis 모듈을 복사합니다
- 설정 파일 3개를 자동 패치합니다
- `.env`에 `ENABLE_JARVIS=true`를 추가합니다
- Telegram User ID를 물어보고 설정합니다
- 메모리 디렉토리를 생성합니다

### 3단계: 봇 재시작

```bash
# launchd 데몬으로 실행 중이면:
launchctl stop <your-service-name>
launchctl start <your-service-name>

# 직접 실행 중이면:
# 프로세스 종료 후 다시 시작
```

### 4단계: 확인

```bash
# 헬스 체크 (API 서버 활성화된 경우)
curl http://localhost:8080/health
```

텔레그램에서 봇에게 아무 메시지를 보내보세요.
`/jarvis` — 상태 확인 | `/coach` — 코칭 리포트

---

## 커맨드 목록

| 커맨드 | 설명 |
|--------|------|
| `/new` | 새 대화 시작 |
| `/status` | 세션·비용 현황 |
| `/repo` | 프로젝트 전환 |
| `/jobs` | 스케줄 작업 목록 |
| `/usage` | 사용량 리포트 |
| `/help` | 명령어 안내 |
| `/verbose` | 출력 상세도 (0/1/2) |
| `/voice` | 음성 응답 토글 |
| `/clipboard` | 클립보드 자동 분석 |
| `/jarvis` | Jarvis 일시정지/재개 |
| `/coach` | 일일 코칭 리포트 |
| `/propose` | 스펙 기반 변경 제안 |
| `/apply` | 스펙 구현 실행 |
| `/archive` | 완료 아카이브 |
| `/explore` | 탐색 모드 |

---

## 데이터 & 프라이버시

- 모든 데이터는 **내 맥북에만 저장** (`~/claude-telegram/memory/`)
- 외부 서버 전송 없음. 클라우드 없음. 텔레메트리 없음.
- 시스템 스냅샷은 5분마다 갱신되고 영구 저장하지 않음
- Claude API 호출은 트리거 발동 시에만 (시간당 최대 10회)

---

## 기술 스택

- Python 3.11 + Claude Code SDK
- Telegram Bot API
- macOS LaunchAgent (데몬)
- FastAPI (API 서버)
- SQLite + JSONL (로컬 스토리지)
- MCP (Google Calendar, Notion, Playwright, AppleScript)
- Whisper (음성 인식) + TTS (음성 합성)

---

## 호환성

| 항목 | 버전 |
|------|------|
| claude-code-telegram | v1.3.0+ |
| Python | 3.11+ |
| macOS | Ventura / Sonoma / Sequoia |

---

## 로드맵

- [ ] Linux 지원 (xdotool)
- [ ] 캘린더 연동 미팅 준비 트리거
- [ ] 주간 트렌드 시각화 리포트
- [ ] 학습된 루틴 기반 선제적 행동
- [ ] `pip install mrstack` 원라인 설치

---

## 만든 사람

**[@thestack_ai](https://www.threads.net/@thestack_ai)**

---

## 라이선스

MIT

---

*[English version →](docs/README_EN.md)*
