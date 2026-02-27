"""Context engine — polls system state, detects context, evaluates triggers.

Mirrors ClipboardMonitor's asyncio.Task pattern:
- 5-minute polling via subprocess calls (osascript, pmset, sysctl, git, etc.)
- State classification (CODING, BROWSING, MEETING, ...)
- Rule-based trigger evaluation with cooldowns
- Publishes ScheduledEvent to EventBus on trigger fire
"""

import asyncio
import re
import subprocess
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import structlog

from ..events.bus import EventBus
from ..events.types import ScheduledEvent
from .persona import ContextState, PersonaLayer

logger = structlog.get_logger()

POLL_INTERVAL = 300  # 5 minutes
MAX_API_CALLS_PER_HOUR = 10

# App name -> state mapping
_APP_STATE_MAP: Dict[str, ContextState] = {
    "code": ContextState.CODING,
    "terminal": ContextState.CODING,
    "iterm": ContextState.CODING,
    "warp": ContextState.CODING,
    "xcode": ContextState.CODING,
    "cursor": ContextState.CODING,
    "chrome": ContextState.BROWSING,
    "safari": ContextState.BROWSING,
    "firefox": ContextState.BROWSING,
    "arc": ContextState.BROWSING,
    "zoom": ContextState.MEETING,
    "meet": ContextState.MEETING,
    "teams": ContextState.MEETING,
    "facetime": ContextState.MEETING,
    "slack": ContextState.COMMUNICATION,
    "discord": ContextState.COMMUNICATION,
    "messages": ContextState.COMMUNICATION,
    "telegram": ContextState.COMMUNICATION,
    "kakaotalk": ContextState.COMMUNICATION,
    "mail": ContextState.COMMUNICATION,
}

# Trigger cooldowns (seconds)
_TRIGGER_COOLDOWNS: Dict[str, int] = {
    "battery_warning": 1800,        # 30 min
    "meeting_prep": 3600,           # 1 hour
    "return_from_away": 1800,       # 30 min
    "long_coding_session": 3600,    # 1 hour
    "context_switch_overload": 1800, # 30 min
    "terminal_error": 600,          # 10 min
    "stuck_detection": 3600,        # 1 hour
    "preemptive_routine": 7200,     # 2 hours
}


class ContextSnapshot:
    """A single point-in-time system state snapshot."""

    def __init__(
        self,
        active_app: str = "",
        battery_pct: int = 100,
        battery_charging: bool = True,
        cpu_load: float = 0.0,
        git_branch: str = "",
        git_dirty: bool = False,
        recent_commands: List[str] | None = None,
        chrome_tabs: List[str] | None = None,
        timestamp: float = 0.0,
    ) -> None:
        self.active_app = active_app
        self.battery_pct = battery_pct
        self.battery_charging = battery_charging
        self.cpu_load = cpu_load
        self.git_branch = git_branch
        self.git_dirty = git_dirty
        self.recent_commands = recent_commands or []
        self.chrome_tabs = chrome_tabs or []
        self.timestamp = timestamp or time.time()


class ContextEngine:
    """Polls system state, classifies context, evaluates triggers."""

    def __init__(
        self,
        event_bus: EventBus,
        target_chat_ids: List[int],
        working_directory: str = "",
        pattern_learner: Any = None,
    ) -> None:
        self.event_bus = event_bus
        self.target_chat_ids = target_chat_ids
        self.working_directory = working_directory
        self._pattern_learner = pattern_learner

        self._running = False
        self._enabled = True  # Always-on when engine is started
        self._task: Optional[asyncio.Task[None]] = None

        # State tracking
        self._current_state = ContextState.AWAY
        self._state_start_time: float = time.time()
        self._history: Deque[ContextSnapshot] = deque(maxlen=12)  # 1 hour
        self._api_calls_this_hour: int = 0
        self._hour_reset_time: float = time.time()

        # Trigger cooldowns
        self._last_trigger_times: Dict[str, float] = {}

        # State transition tracking for triggers
        self._app_switch_times: List[float] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def current_state(self) -> ContextState:
        return self._current_state

    @property
    def state_duration_min(self) -> int:
        return int((time.time() - self._state_start_time) / 60)

    def toggle(self) -> bool:
        """Toggle context engine. Returns new state."""
        self._enabled = not self._enabled
        if self._enabled:
            logger.info("Jarvis context engine enabled")
        else:
            logger.info("Jarvis context engine disabled")
        return self._enabled

    def set_enabled(self, state: bool) -> None:
        self._enabled = state

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Context engine started (active)")

    async def stop(self) -> None:
        """Stop the polling loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Context engine stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                if self._enabled:
                    await self._tick()
                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Context engine poll error")
                await asyncio.sleep(POLL_INTERVAL * 2)

    async def _tick(self) -> None:
        """Single poll cycle: collect -> detect state -> evaluate triggers."""
        # Reset hourly API counter
        now = time.time()
        if now - self._hour_reset_time >= 3600:
            self._api_calls_this_hour = 0
            self._hour_reset_time = now

        snap = await self._collect_snapshot()
        self._history.append(snap)

        new_state = self._detect_state(snap)

        # Track state transitions
        if new_state != self._current_state:
            self._app_switch_times.append(now)
            # Clean old switch times (keep last 10 min)
            self._app_switch_times = [
                t for t in self._app_switch_times if now - t < 600
            ]
            prev_state = self._current_state
            self._current_state = new_state
            self._state_start_time = now
            logger.info(
                "State transition",
                from_state=prev_state.value,
                to_state=new_state.value,
                app=snap.active_app,
            )

        # Evaluate triggers
        triggers = self._evaluate_triggers(snap)
        for trigger_id, prompt in triggers:
            if self._api_calls_this_hour >= MAX_API_CALLS_PER_HOUR:
                logger.warning("Jarvis hourly API limit reached, skipping trigger")
                break

            # Add persona prefix
            from datetime import datetime

            hour = datetime.now().hour
            prefix = PersonaLayer.build_prompt_prefix(
                self._current_state, hour, self.state_duration_min
            )
            full_prompt = f"{prefix}\n\n{prompt}"

            event = ScheduledEvent(
                job_id=f"jarvis-{trigger_id}",
                job_name=f"jarvis-{trigger_id}",
                prompt=full_prompt,
                working_directory=self.working_directory,
                target_chat_ids=self.target_chat_ids,
                source="jarvis",
            )
            await self.event_bus.publish(event)
            self._api_calls_this_hour += 1
            self._last_trigger_times[trigger_id] = now
            logger.info("Jarvis trigger fired", trigger=trigger_id)

    async def _collect_snapshot(self) -> ContextSnapshot:
        """Collect system state via parallel subprocess calls."""
        loop = asyncio.get_event_loop()

        async def _run(cmd: List[str], timeout: int = 5) -> str:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        cmd, capture_output=True, text=True, timeout=timeout
                    ),
                )
                return result.stdout.strip() if result.returncode == 0 else ""
            except Exception:
                return ""

        # Run all collectors in parallel
        results = await asyncio.gather(
            _run([
                "osascript", "-e",
                'tell app "System Events" to get name of first process '
                "whose frontmost is true",
            ]),
            _run(["pmset", "-g", "batt"]),
            _run(["sysctl", "-n", "vm.loadavg"]),
            _run([
                "git", "-C", self.working_directory,
                "branch", "--show-current",
            ]),
            _run([
                "git", "-C", self.working_directory,
                "status", "--short",
            ]),
            _run([
                "osascript", "-e",
                'tell application "Google Chrome" to get title of active tab '
                "of front window",
            ]),
            return_exceptions=True,
        )

        # Parse results
        active_app = results[0] if isinstance(results[0], str) else ""

        battery_pct = 100
        battery_charging = True
        batt_str = results[1] if isinstance(results[1], str) else ""
        batt_match = re.search(r"(\d+)%", batt_str)
        if batt_match:
            battery_pct = int(batt_match.group(1))
        battery_charging = "charging" in batt_str.lower() or "charged" in batt_str.lower()

        cpu_load = 0.0
        load_str = results[2] if isinstance(results[2], str) else ""
        load_match = re.search(r"[\d.]+", load_str)
        if load_match:
            try:
                cpu_load = float(load_match.group())
            except ValueError:
                pass

        git_branch = results[3] if isinstance(results[3], str) else ""
        git_dirty = bool(results[4]) if isinstance(results[4], str) else False

        chrome_tab = results[5] if isinstance(results[5], str) else ""
        chrome_tabs = [chrome_tab] if chrome_tab else []

        return ContextSnapshot(
            active_app=active_app,
            battery_pct=battery_pct,
            battery_charging=battery_charging,
            cpu_load=cpu_load,
            git_branch=git_branch,
            git_dirty=git_dirty,
            chrome_tabs=chrome_tabs,
        )

    def _detect_state(self, snap: ContextSnapshot) -> ContextState:
        """Classify current state from snapshot."""
        app_lower = snap.active_app.lower()

        # Check app-based state
        for app_key, state in _APP_STATE_MAP.items():
            if app_key in app_lower:
                # Promote to DEEP_WORK if same coding app for 2+ hours
                if (
                    state == ContextState.CODING
                    and self._current_state == ContextState.CODING
                    and self.state_duration_min >= 120
                ):
                    return ContextState.DEEP_WORK
                return state

        # No active app or unknown -> check if AWAY
        if not app_lower or app_lower in ("loginwindow", "screensaver"):
            return ContextState.AWAY

        # Default: keep current state
        return self._current_state

    def _evaluate_triggers(
        self, snap: ContextSnapshot
    ) -> List[Tuple[str, str]]:
        """Evaluate trigger rules against current snapshot.

        Returns list of (trigger_id, prompt) for triggers that should fire.
        DEEP_WORK state only allows battery + meeting triggers.
        """
        now = time.time()
        triggers: List[Tuple[str, str]] = []

        def _cooled(trigger_id: str) -> bool:
            last = self._last_trigger_times.get(trigger_id, 0)
            cooldown = _TRIGGER_COOLDOWNS.get(trigger_id, 600)
            return (now - last) >= cooldown

        is_deep = self._current_state == ContextState.DEEP_WORK

        # 1. Battery warning (< 20%, not charging)
        if (
            snap.battery_pct < 20
            and not snap.battery_charging
            and _cooled("battery_warning")
        ):
            triggers.append((
                "battery_warning",
                f"배터리가 {snap.battery_pct}%입니다. "
                f"충전기를 연결하거나 작업을 저장하세요.",
            ))

        # 2. Meeting prep (check via calendar — simplified: just notify)
        # This would ideally check Google Calendar MCP, but for now
        # we skip this trigger (calendar-check job already handles it)

        # Deep work gate: remaining triggers are suppressed
        if is_deep:
            return triggers

        # 3. Return from AWAY
        if (
            len(self._history) >= 2
            and self._history[-2].active_app.lower() in ("loginwindow", "screensaver", "")
            and snap.active_app
            and snap.active_app.lower() not in ("loginwindow", "screensaver", "")
            and _cooled("return_from_away")
        ):
            triggers.append((
                "return_from_away",
                f"돌아오셨네요. "
                f"마지막 작업: {snap.git_branch or '알 수 없음'} 브랜치"
                f"{' (변경사항 있음)' if snap.git_dirty else ''}",
            ))

        # 4. Long coding session (3+ hours)
        if (
            self._current_state in (ContextState.CODING, ContextState.DEEP_WORK)
            and self.state_duration_min >= 180
            and _cooled("long_coding_session")
        ):
            triggers.append((
                "long_coding_session",
                f"{self.state_duration_min}분째 코딩 중입니다. "
                f"잠깐 쉬어가시죠. 스트레칭이나 물 한잔 어떠세요?",
            ))

        # 5. Context switch overload (5+ switches in 10 min)
        recent_switches = [
            t for t in self._app_switch_times if now - t < 600
        ]
        if len(recent_switches) >= 5 and _cooled("context_switch_overload"):
            triggers.append((
                "context_switch_overload",
                f"최근 10분간 앱 전환이 {len(recent_switches)}회입니다. "
                f"컨텍스트 전환이 잦으면 집중이 어렵습니다. "
                f"하나의 작업에 집중해보시겠어요?",
            ))

        # 6. Terminal error detection (check recent commands for error patterns)
        for cmd in snap.recent_commands[-3:]:
            if re.search(r"(error|fail|panic|traceback)", cmd, re.I):
                if _cooled("terminal_error"):
                    triggers.append((
                        "terminal_error",
                        f"터미널에서 에러가 감지되었습니다: {cmd[:200]}. "
                        f"도움이 필요하신가요?",
                    ))
                break

        # 7. Stuck detection (same branch, dirty, 30+ min in CODING)
        if (
            self._current_state == ContextState.CODING
            and self.state_duration_min >= 30
            and snap.git_dirty
            and _cooled("stuck_detection")
        ):
            # Check if git status hasn't changed (still dirty, same branch)
            if len(self._history) >= 6:
                old_snap = self._history[-6]
                if (
                    old_snap.git_branch == snap.git_branch
                    and old_snap.git_dirty
                ):
                    triggers.append((
                        "stuck_detection",
                        f"30분 이상 같은 브랜치({snap.git_branch})에서 "
                        f"커밋 없이 작업 중입니다. 막히신 부분이 있나요?",
                    ))

        # 8. Preemptive routine (learned pattern)
        if self._pattern_learner and _cooled("preemptive_routine"):
            from datetime import datetime as _dt

            routine = self._pattern_learner.check_preemptive(
                self._current_state, _dt.now().hour
            )
            if routine:
                rtype = routine.get("request_type", "")
                triggers.append((
                    "preemptive_routine",
                    f"이 시간대에 보통 '{rtype}' 유형의 작업을 하시더라고요. "
                    f"미리 준비할 게 있을까요?",
                ))

        return triggers
