# Mr.Stack

> 대화할수록 성장하는 AI 집사.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Mr.Stack이 뭔가요?

[Claude Code](https://claude.ai) 기반 텔레그램 AI 비서입니다.

터미널에서만 쓰는 Claude Code를 **텔레그램으로 꺼내서**,
맥북을 덮어놔도, 외출 중이어도, 자고 있어도 24시간 동작합니다.

단순한 챗봇이 아닙니다.
**내 맥북을 관찰하고, 대화를 기억하고, 내 패턴을 학습하고, 먼저 말을 거는** AI 파트너입니다.

---

## 주요 기능

### 1. 텔레그램 AI 비서
텔레그램 메시지 하나로 Claude에게 지시합니다.

- 코드 작성 / 수정 / 디버깅 / 리팩토링
- 파일, 사진, 음성 메시지 전부 처리
- 음성으로 지시하면 음성으로 답변 (Whisper + TTS)
- 복사한 내용 자동 분석 (에러→원인 분석, URL→요약, 코드→리뷰)

### 2. 메모리 시스템 — 대화를 기억하는 AI

일반 AI는 세션이 끝나면 모든 걸 잊습니다.
Mr.Stack은 **단기 기억과 장기 기억을 분리**해서 관리합니다.

#### 단기 기억 (휘발성)
- **컨텍스트 스냅샷**: 최근 1시간 시스템 상태 (메모리에만 존재, 12개 순환)
- **현재 세션 대화**: Claude의 컨텍스트 윈도우 안에서 유지
- **최근 인터랙션**: `interactions.jsonl`의 최근 7일 데이터 → 패턴 분석에 사용

단기 기억은 자동으로 순환되며, 디스크를 차지하지 않거나 최소한으로 유지됩니다.

#### 장기 기억 (영구 저장)
3시간마다 최근 대화를 분석해서 **의미있는 정보만 추출**하여 영구 저장합니다:

```
~/claude-telegram/memory/
  people/          → 대화에서 언급된 사람 정보 (덮어쓰기)
  projects/        → 프로젝트별 진행상황, 기술 결정 (덮어쓰기)
  decisions/       → 내린 결정과 그 이유 (append)
  preferences/     → 내 선호도 — 코딩 스타일, 도구, 언어 (덮어쓰기)
  daily/           → 일일 요약 아카이브 (하루 1파일)
  knowledge/       → 새로 알게 된 정보 (덮어쓰기)
  patterns/        → 작업 패턴 데이터 (interactions.jsonl)
```

장기 기억의 핵심은 **"쌓이는 게 아니라 갱신된다"** 는 점입니다.
`people/`, `projects/`, `preferences/` 파일은 새 정보가 들어오면 **기존 파일을 덮어씁니다**.
파일이 무한히 커지지 않고, 항상 최신 상태만 유지합니다.

유일하게 계속 쌓이는 건 `daily/` (하루 1개, ~1KB)와 `interactions.jsonl` (대화당 ~300B)이며,
1년 사용해도 **총 용량은 10~15MB** 수준입니다.

다음 세션에서 "어제 작업하던 거 이어해줘"라고 하면 정확히 이어갑니다.
일주일 쓰면 내 프로젝트 구조, 선호하는 스택, 자주 쓰는 패턴을 다 알고 있습니다.
한 달 쓰면 나보다 내 업무 히스토리를 더 잘 기억합니다.

### 3. 상시 대기 시스템 (Jarvis Mode)

macOS 데몬으로 동작하며, **5분마다 맥북 상태를 스캔**합니다:

- 현재 활성 앱 (osascript)
- 배터리 잔량 및 충전 상태 (pmset)
- CPU 부하 (sysctl)
- Git 브랜치 및 변경 상태
- Chrome 활성 탭
- 터미널 최근 명령어

이 정보를 기반으로 현재 상태를 자동 분류합니다:

```
CODING → BROWSING → MEETING → COMMUNICATION → BREAK → DEEP_WORK → AWAY
```

그리고 **7가지 상황을 자동 감지**해서 선제적으로 알림을 보냅니다:

| 상황 | Mr.Stack의 반응 |
|------|----------------|
| 배터리 20% 이하 | "배터리 12% — 저장하세요" |
| 자리 비웠다 돌아옴 | "돌아오셨네요. feature/auth 브랜치 작업 중이었습니다" |
| 코딩 3시간 연속 | "3시간째 코딩 중 — 잠깐 쉬어가시죠" |
| 앱 전환 10분에 5번+ | "컨텍스트 전환이 잦습니다. 집중해보세요" |
| 같은 파일 30분, 커밋 없음 | "막히신 부분이 있나요?" |
| 터미널에 에러 감지 | "에러를 분석해드릴까요?" |
| 딥워크 모드 (2시간+ 집중) | 중요한 것만 통과, 나머지 알림 차단 |

각 트리거에는 **쿨다운**이 있어서 같은 알림이 반복되지 않습니다.
딥워크 상태에서는 배터리 경고 외에는 전부 차단합니다.

### 4. 패턴 학습 — 쓸수록 똑똑해지는 AI

모든 대화가 `interactions.jsonl`에 기록됩니다:

```json
{
  "ts": "2026-02-28T10:00:00",
  "hour": 10,
  "state": "CODING",
  "request_type": "debug",
  "duration_ms": 5200,
  "tools_used": ["Read", "Edit", "Bash"]
}
```

이 데이터를 분석해서:
- **피크 시간대**: "10-12시에 가장 생산적"
- **요청 유형 분포**: "디버깅 40%, 기능개발 30%, 질문 20%"
- **패턴 감지**: "매주 월요일 10시에 주간 계획을 요청함"
- **루틴 학습**: confidence > 0.7이면 선제적으로 준비

### 5. 일일 코칭 리포트

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

이번 주 트렌드:
• 평균 지시 명확도 향상 중 (2.1 → 2.6)
• 가장 생산적 시간대: 10-12시 (일관적)
```

아첨 없이 직설적. 매일 데이터로 증명합니다. `/coach` 명령으로 수동 조회도 가능합니다.

### 6. 상황별 톤 조절 (Persona Layer)

Mr.Stack은 지금 내 상태에 맞게 말투를 바꿉니다.

| 상태 | 톤 | 예시 |
|------|-----|------|
| 코딩 중 | 기술적, 간결 | `"auth.py:42 — null check 누락"` |
| 딥워크 | 침묵 (긴급만 전달) | — |
| 휴식 복귀 | 따뜻, 요약 | `"돌아오셨네요. PR #23 리뷰 대기 중"` |
| 밤 10시 이후 | 걱정 | `"오늘 충분히 하셨습니다. 내일 이어하시죠"` |

### 7. 스케줄 작업 (9개 자동 실행)

| 작업 | 시간 |
|------|------|
| 아침 브리핑 (일정+할일+뉴스) | 평일 08:00 |
| 저녁 요약 + 코칭 리포트 | 매일 21:00 |
| 주간 회고 | 금요일 18:00 |
| 캘린더 리마인더 | 평일 09/12/15/18시 |
| 대화 → 메모리 자동 업데이트 | 3시간마다 |
| GitHub 알림 확인 | 2시간마다 |
| Notion 업무 로그 저장 | 매일 22:00 |
| AI 뉴스 요약 | 매일 08:30, 20:30 |
| OAuth 토큰 만료 모니터링 | 매일 10:00 |

### 8. 외부 서비스 연동 (MCP)

- **Google Calendar** — 일정 조회/생성/리마인더
- **Notion** — 업무 로그 자동 기록
- **GitHub** — PR, 이슈, 알림 모니터링
- **Playwright** — 웹 자동화
- **AppleScript** — macOS 제어

---

## 기존 솔루션과 뭐가 다른가요?

| | 기존 AI 봇 | Mr.Stack |
|---|-----------|----------|
| **동작 방식** | 물어봐야 답함 | **먼저 알림을 보냄** |
| **보안** | API 키를 외부 서버에 전송 | **내 맥북에서만 동작. 서버 없음** |
| **상시성** | 터미널 열어야 사용 | **맥북 덮어도 24시간 동작** |
| **기억** | 매번 새로 시작 | **대화를 영구 저장, 맥락 유지** |
| **학습** | 학습 없음 | **작업 패턴을 분석하고 루틴 감지** |
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

## FAQ

### Claude Code 무료 버전으로도 되나요?

동작은 합니다. 하지만 Mr.Stack은 스케줄 작업, Jarvis 트리거, 일반 대화까지 Claude를 호출하기 때문에 **Max 플랜을 강력히 권장**합니다. 무료 플랜은 사용량 제한에 빠르게 걸립니다.

### Anthropic API 키가 필요한가요?

아닙니다. Claude Code의 인증을 그대로 사용합니다. 별도 API 키 발급이나 과금이 없습니다.

### 비용이 얼마나 드나요?

Mr.Stack 자체는 무료(오픈소스)입니다. 필요한 건:
- **Claude Code 구독**: Pro($20/월) 또는 Max($100/월 권장)
- **Telegram**: 무료
- **서버 비용**: 없음 (내 맥북에서 동작)

### Windows나 Linux에서도 되나요?

현재는 **macOS 전용**입니다. 시스템 상태 스캔에 osascript, pmset 등 macOS 전용 도구를 사용합니다. Linux 지원은 로드맵에 있습니다.

### 맥북을 닫아도 정말 동작하나요?

네. macOS LaunchAgent(데몬)로 등록하면:
- 맥북 부팅 시 자동 시작
- 크래시 시 자동 재시작
- 덮개를 닫아도 백그라운드 동작 (Power Nap / 전원 연결 시)
- 외출 중에도 텔레그램으로 지시 가능

### 내 데이터가 외부로 전송되나요?

**절대 아닙니다.** 모든 데이터는 맥북 로컬 파일(SQLite, JSONL)에만 저장됩니다. 외부 서버, 클라우드 스토리지, 텔레메트리 일체 없습니다. Claude API 호출만 Anthropic 서버를 경유하며, 이는 Claude Code 자체의 동작과 동일합니다.

### 설치하면 기존 claude-code-telegram 설정이 날아가나요?

아닙니다. `install.sh`는 기존 파일에 Jarvis 관련 코드만 **추가**합니다. 기존 설정, 대화 기록, 스케줄 작업은 전부 유지됩니다. 이미 Jarvis가 설치되어 있으면 덮어쓸지 먼저 물어봅니다.

### install.sh 실행 중 에러가 나요

가장 흔한 원인:
1. **claude-code-telegram이 설치되지 않음** → 먼저 `uv tool install claude-code-telegram`
2. **Python 3.11 미만** → `python3 --version` 확인
3. **site-packages 경로를 못 찾음** → 스크립트가 수동 입력을 요청합니다

이슈가 해결되지 않으면 [GitHub Issues](https://github.com/whynowlab/mrstack/issues)에 남겨주세요.

### 봇 응답이 느려요

Claude Code SDK를 통해 Claude를 호출하므로, 복잡한 요청은 30초~2분 걸릴 수 있습니다. 이건 Claude 자체의 처리 시간이며, Mr.Stack의 오버헤드는 무시할 수준입니다.

### Jarvis 알림이 너무 자주 와요

`/jarvis`로 일시정지하거나, `context_engine.py`의 `_TRIGGER_COOLDOWNS` 값을 늘려서 쿨다운을 조절할 수 있습니다. 딥워크 상태에서는 배터리 경고 외 전부 자동 차단됩니다.

### 용량을 많이 차지하나요? 오래 쓰면 데이터가 쌓이지 않나요?

Mr.Stack은 단기 기억과 장기 기억을 분리해서 관리합니다.

**단기 기억 (자동 순환, 디스크 사용 없음):**
- 컨텍스트 스냅샷: 메모리에서만 12개 순환 → 디스크 0
- 세션 대화: Claude 컨텍스트 윈도우 안에서만 유지

**장기 기억 (디스크 저장, 하지만 거의 안 늘어남):**
- `people/`, `projects/`, `preferences/` → **덮어쓰기 방식**. 파일이 커지지 않고 항상 최신 상태만 유지
- `daily/` → 하루 1파일, ~1KB. 1년 = ~365KB
- `interactions.jsonl` → 대화당 ~300B. 하루 50회 사용 시 1년 = ~5MB
- `routines.json` → 주기적으로 갱신, 수 KB 고정

**1년 사용 시 예상 용량: 10~15MB** (사진 1장보다 작습니다)

SQLite 데이터베이스(대화 기록)가 별도로 있지만, 이것도 수십 MB 수준입니다.
용량 걱정은 하지 않아도 됩니다.

### 여러 맥북에서 사용 가능한가요?

각 맥북에 별도로 설치하면 됩니다. 메모리 데이터를 동기화하려면 `~/claude-telegram/memory/` 폴더를 iCloud나 git으로 공유할 수 있습니다.

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
