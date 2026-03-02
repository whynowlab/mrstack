<div align="center">

<img src="assets/logo-256.png" alt="Mr.Stack" width="140" />

# Mr.Stack

**맥북을 덮어도 일하는 Claude.**

Claude Code + Telegram = 24시간 AI 개발 파트너

[![PyPI](https://img.shields.io/pypi/v/mrstack.svg)](https://pypi.org/project/mrstack/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![macOS](https://img.shields.io/badge/macOS-Ventura%20%7C%20Sonoma%20%7C%20Sequoia-black.svg)](https://apple.com/macos)
[![Linux](https://img.shields.io/badge/Linux-supported-orange.svg)](#호환성)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://t.me/botfather)

</div>

---

## 30초 설치

```bash
uv tool install mrstack        # 1. 설치
mrstack init                    # 2. 설정 (텔레그램 토큰 + User ID 입력)
mrstack start                   # 3. 시작!
```

텔레그램에서 봇에게 아무 메시지를 보내보세요. 응답이 오면 성공입니다.

> `uv`가 없으면 `pip install mrstack`도 됩니다.
> `mrstack init`이 필요한 것들(claude-code-telegram 등)을 자동으로 확인하고 설치합니다.

<details>
<summary><b>mrstack CLI 전체 명령어</b></summary>

```
mrstack init          # 설정 마법사
mrstack start         # 봇 시작
mrstack start --bg    # 백그라운드 시작
mrstack stop          # 봇 중지
mrstack daemon        # 시스템 데몬 등록 (재부팅 시 자동 시작)
mrstack daemon -u     # 데몬 해제
mrstack status        # 상태 표시
mrstack logs -f       # 로그 실시간 추적
mrstack config        # 설정 편집
mrstack jarvis on/off # Jarvis 모드 토글
mrstack patch         # 모듈 재설치
mrstack update        # 최신 버전 업데이트
mrstack version       # 버전 정보
```

</details>

---

## Mr.Stack이 뭔가요?

[Claude Code](https://claude.ai)를 **텔레그램으로 확장**한 24시간 AI 파트너입니다.

터미널을 닫아도, 맥북을 덮어놔도, 외출 중이어도 동작합니다.
Claude Code가 터미널에 묶여있다면, Mr.Stack은 **주머니 안의 Claude**입니다.

> 일반 AI 비서는 물어봐야 대답하는 콜센터입니다.
> Mr.Stack은 **옆자리에서 같은 화면을 보고 있는 시니어 동료**입니다.

---

## 핵심 기능

### 1. 텔레그램 AI 비서

텔레그램 메시지 하나로 Claude에게 지시합니다.

- 코드 작성 / 수정 / 디버깅 / 리팩토링
- 파일, 사진, 음성 메시지 전부 처리
- 음성으로 지시하면 음성으로 답변
- 복사한 내용 자동 분석 (에러 → 원인, URL → 요약, 코드 → 리뷰)

### 2. 학습 기능 — 링크 던지고 "학습해줘"

**가장 쉬운 사용법입니다.** 링크, 문서, 자료를 텔레그램에 던지고 **"학습해줘"** 한마디면 끝.

```
[사용자] https://docs.example.com/api-guide
        이거 학습해줘

[Mr.Stack] API 가이드를 분석했습니다.
           - 인증: Bearer 토큰 방식
           - Rate limit: 100req/min
           - 주요 엔드포인트 12개
           메모리에 저장했습니다. 다음에 이 API 관련 질문하시면 바로 답변 가능합니다.
```

PDF, 웹페이지, 코드 파일, 이미지 — 뭐든 보내면 읽고 기억합니다.
나중에 **"저번에 학습한 API 문서에서 인증 방식이 뭐였지?"** 라고 물으면 바로 답합니다.

### 3. 영구 메모리 — 세션이 끝나도 잊지 않는 AI

대부분의 AI는 창을 닫으면 전부 리셋됩니다. Mr.Stack은 **기억합니다.**

- 3시간마다 대화를 분석해서 의미있는 정보만 영구 저장
- 프로젝트 진행상황, 기술 결정, 사람 정보, 선호도 자동 업데이트
- **"어제 작업하던 거 이어해줘"** → 정확히 이어감
- 1년 써도 총 용량 10~15MB (사진 1장보다 작음)

```
~/claude-telegram/memory/
  people/       → 사람 정보 (덮어쓰기)
  projects/     → 프로젝트별 진행상황 (덮어쓰기)
  decisions/    → 결정과 이유 (누적)
  preferences/  → 내 선호도 (덮어쓰기)
  daily/        → 일일 요약 (하루 1개)
  knowledge/    → 학습한 지식 (덮어쓰기)
  patterns/     → 작업 패턴 데이터
```

### 4. 상시 대기 (Jarvis Mode)

맥북 전체를 **5분마다 스캔**하고, 필요할 때 **먼저 말을 겁니다.**

| 상황 | Mr.Stack의 반응 |
|------|----------------|
| 배터리 20% 이하 | "배터리 12% — 저장하세요" |
| 자리 비웠다 돌아옴 | "돌아오셨네요. feature/auth 브랜치 작업 중이었습니다" |
| 코딩 3시간 연속 | "3시간째 코딩 중 — 잠깐 쉬어가시죠" |
| 같은 파일 30분, 커밋 없음 | "막히신 부분이 있나요?" |
| 딥워크 모드 (2시간+ 집중) | 중요한 것만 통과, 나머지 차단 |

> Jarvis는 macOS에서 가장 잘 동작합니다. Linux에서도 CPU/배터리/Git 모니터링은 정상 동작하며, 활성 앱/Chrome 탭 감지는 macOS 전용입니다.

### 5. 패턴 학습 + 데일리 코칭

작업 습관을 분석하고, 매일 밤 데이터 기반 코칭을 보내줍니다:

```
[Daily Coach] 2026-02-28

생산성: 8/10 (어제 대비 +1)

잘한 점:
  오전 집중 블록 2시간 유지 → 커밋 4개

개선 포인트:
  14-16시 컨텍스트 전환 7회 — 가장 비효율 구간
  → 내일은 이 시간에 단일 작업 블록 추천
```

### 6. 자동 스케줄 작업

설정해두면 매일 자동으로 실행됩니다:

| 작업 | 시간 |
|------|------|
| 아침 브리핑 (일정 + 할일 + 뉴스) | 평일 08:00 |
| 저녁 요약 + 코칭 리포트 | 매일 21:00 |
| 주간 회고 | 금요일 18:00 |
| 캘린더 리마인더 | 평일 09/12/15/18시 |
| 대화 → 메모리 자동 업데이트 | 3시간마다 |
| GitHub 알림 확인 | 2시간마다 |

> 모델 라우팅: 단순 조회는 Haiku, 분석은 Sonnet, 심층 회고는 Opus. 비용을 자동 최적화합니다.

### 7. 상황별 톤 조절

| 상태 | 톤 | 예시 |
|------|-----|------|
| 코딩 중 | 간결 | `"auth.py:42 — null check 누락"` |
| 딥워크 | 침묵 | 긴급만 전달 |
| 복귀 시 | 요약 | `"돌아오셨네요. PR #23 리뷰 대기 중"` |
| 밤 10시+ | 걱정 | `"오늘 충분히 하셨습니다"` |

### 8. 외부 연동 (선택)

MCP를 통해 외부 서비스를 연결할 수 있습니다. **없어도 핵심 기능은 전부 동작합니다.**

| 서비스 | 기능 |
|--------|------|
| Google Calendar | 일정 조회/생성/리마인더 |
| Notion | 업무 로그 자동 기록 |
| GitHub | PR/이슈/알림 모니터링 |
| Playwright | 웹 자동화 |

---

## 기존 AI와 뭐가 다른가요?

| | 기존 AI 봇 | Mr.Stack |
|---|-----------|----------|
| **동작** | 물어봐야 답함 | **조건 충족 시 먼저 알림** |
| **보안** | API 키를 외부 서버에 전송 | **내 맥북에서만 동작** |
| **상시성** | 터미널 세션에 묶임 | **24시간 백그라운드 동작** |
| **기억** | 창 닫으면 리셋 | **영구 메모리** |
| **학습** | 없음 | **패턴 분석 + 루틴 예측** |
| **코칭** | 없음 | **매일 데이터 기반 코칭** |
| **데이터** | 클라우드 | **100% 로컬** |

---

## 설치 상세

### 준비물

| 필요한 것 | 어디서 |
|-----------|--------|
| **Claude Code** | [claude.ai/download](https://claude.ai/download) — Max 플랜 권장 |
| **Telegram 계정** | [telegram.org](https://telegram.org) |

### Telegram 봇 만들기 (2분)

1. Telegram에서 **[@BotFather](https://t.me/botfather)** 검색 → `/newbot` 입력
2. 봇 이름 입력 (예: `My Stack Bot`)
3. 봇 username 입력 (예: `my_stack_bot`)
4. **토큰** 저장 (`1234567890:ABCdef...`)

### Telegram User ID 확인 (30초)

1. **[@userinfobot](https://t.me/userinfobot)** 에게 아무 메시지 전송
2. 받은 **숫자 ID** 저장

### 설치 & 시작

```bash
uv tool install mrstack    # 설치
mrstack init               # 토큰 + User ID 입력, 자동 설정
mrstack start              # 시작!
```

`mrstack init`이 다음을 자동으로 처리합니다:
- Claude Code 설치 확인
- claude-code-telegram 설치 (없으면 자동 설치)
- `.env` 설정 파일 생성
- 메모리 디렉토리 생성
- Jarvis 모드 설정 (macOS)

### 항상 백그라운드에서 실행하기

```bash
mrstack daemon    # 시스템 데몬 등록 → 재부팅해도 자동 시작
```

### 봇 프로필 사진 설정 (선택)

1. [@BotFather](https://t.me/botfather)에게 `/mybots` → 내 봇 선택 → Edit Botpic
2. `assets/bot-profile.png` 전송

<details>
<summary><b>고급: git clone으로 설치</b></summary>

```bash
git clone https://github.com/whynowlab/mrstack.git
cd mrstack
pip install -e .
mrstack init
```

개발 기여나 커스터마이징 시 사용합니다.

</details>

<details>
<summary><b>고급: Claude Code로 설치</b></summary>

Claude Code 터미널에서:
```
github.com/whynowlab/mrstack 이 레포를 보고 Mr.Stack을 설치해줘.
```

Claude가 README를 읽고 설치 과정을 안내합니다.

</details>

<details>
<summary><b>선택: 외부 서비스 연동</b></summary>

**Google Calendar**
```json
// mcp-config.json
{
  "mcpServers": {
    "google-calendar": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-google-calendar"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-id",
        "GOOGLE_CLIENT_SECRET": "your-secret"
      }
    }
  }
}
```

**Notion**
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-notion"],
      "env": { "NOTION_API_KEY": "ntn_..." }
    }
  }
}
```

**GitHub** — `gh auth login` 한 줄이면 끝.

**Playwright** — `npx playwright install chromium`

</details>

---

## 텔레그램 명령어

| 명령어 | 설명 |
|--------|------|
| `/new` | 새 대화 시작 |
| `/status` | 세션/비용 현황 |
| `/repo` | 프로젝트 전환 |
| `/jarvis` | Jarvis 일시정지/재개 |
| `/coach` | 일일 코칭 리포트 |
| `/jobs` | 스케줄 작업 목록 |
| `/voice` | 음성 응답 토글 |
| `/clipboard` | 클립보드 자동 분석 |
| `/help` | 전체 명령어 안내 |

---

## 호환성

| 플랫폼 | 지원 수준 |
|--------|----------|
| **macOS** (Ventura / Sonoma / Sequoia) | 100% — 모든 기능 |
| **Linux** | 95% — Jarvis의 활성 앱/Chrome 탭 감지 제외, 나머지 정상 |
| **Windows (WSL2)** | 95% — Linux와 동일 |
| **Windows (네이티브)** | 로드맵 |

| 요구사항 | 버전 |
|----------|------|
| Python | 3.11+ |
| claude-code-telegram | v1.3.0+ |
| Claude Code | Max 플랜 권장 |

---

## 보안 & 프라이버시

- **100% 로컬** — 모든 데이터는 맥북에만 저장. 외부 서버 전송 없음
- **사용자 인증** — `ALLOWED_USERS`에 등록된 Telegram ID만 허용
- **Sandbox** — Claude의 파일 접근은 `APPROVED_DIRECTORY`로 제한
- **Quality Gate** — `rm -rf`, `sudo`, `curl | sh` 등 위험 명령 사전 차단
- Claude API 호출만 Anthropic 서버 경유 (Claude Code 자체와 동일)

---

## FAQ

<details>
<summary><b>Claude Code 무료 버전으로도 되나요?</b></summary>

동작은 하지만 사용량 제한에 빠르게 걸립니다. **Max 플랜을 강력히 권장합니다.**
Mr.Stack 자체는 무료(오픈소스)이고, 서버 비용도 없습니다.

</details>

<details>
<summary><b>Anthropic API 키가 필요한가요?</b></summary>

아닙니다. Claude Code의 인증을 그대로 사용합니다.

</details>

<details>
<summary><b>맥북을 닫아도 정말 동작하나요?</b></summary>

네. `mrstack daemon`으로 등록하면:
- 부팅 시 자동 시작, 크래시 시 자동 재시작
- 덮개 닫아도 백그라운드 동작 (전원 연결 시)
- 외출 중에도 텔레그램으로 지시 가능

</details>

<details>
<summary><b>토큰(사용량)을 많이 잡아먹나요?</b></summary>

하루 15~20회 API 호출 추가. Max 플랜 기준 부담 없는 수준입니다.
5분 폴링, 패턴 로깅, 상태 분류는 **토큰 제로** (로컬 실행만).

</details>

<details>
<summary><b>내 데이터가 외부로 전송되나요?</b></summary>

**절대 아닙니다.** 모든 데이터는 로컬 파일(SQLite, JSONL, Markdown)에만 저장됩니다.

</details>

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 런타임 | Python 3.11 + asyncio |
| AI 엔진 | Claude Code SDK (Opus / Sonnet / Haiku) |
| 인터페이스 | Telegram Bot API |
| 프로세스 관리 | macOS LaunchAgent / Linux systemd |
| 스토리지 | SQLite + JSONL + Markdown |
| 외부 연동 | MCP (Google Calendar, Notion, Playwright) |

---

## 링크

- [Threads @thestack_ai](https://www.threads.net/@thestack_ai) — 개발 이야기, 업데이트
- [GitHub Issues](https://github.com/whynowlab/mrstack/issues) — 버그 리포트, 기능 요청
- [PyPI](https://pypi.org/project/mrstack/) — 패키지
- [claude-code-telegram](https://github.com/nicepkg/claude-code-telegram) — 기반 프레임워크

---

## 라이선스

MIT

---

*[English version →](README.en.md)*
