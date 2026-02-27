"""Daily coach — generates productivity coaching reports from interaction data.

Uses interactions.jsonl to analyze the day's work patterns
and produce a direct, actionable coaching report.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .pattern_learner import PatternLearner

logger = structlog.get_logger()


class DailyCoach:
    """Generates daily coaching reports from interaction logs."""

    def __init__(self, memory_base: str | Path) -> None:
        self.memory_base = Path(memory_base)
        self.pattern_learner = PatternLearner(memory_base)

    def calculate_metrics(
        self, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate productivity metrics from interaction records.

        Returns:
            Dict with total, success_rate, context_switches, debug_ratio, peak_hour.
        """
        if not records:
            return {
                "total": 0,
                "avg_duration_ms": 0,
                "context_switches": 0,
                "debug_ratio": 0.0,
                "peak_hour": None,
                "request_types": {},
                "hourly_distribution": {},
                "states": {},
            }

        types: Counter[str] = Counter()
        hours: Counter[int] = Counter()
        states: Counter[str] = Counter()
        durations: list[int] = []
        context_switches = 0
        prev_state = None

        for rec in records:
            rtype = rec.get("request_type", "admin")
            types[rtype] += 1
            hours[rec.get("hour", 0)] += 1
            state = rec.get("state", "UNKNOWN")
            states[state] += 1
            if "duration_ms" in rec:
                durations.append(rec["duration_ms"])
            if prev_state and state != prev_state:
                context_switches += 1
            prev_state = state

        total = len(records)
        debug_count = types.get("debug", 0)
        peak_hour = hours.most_common(1)[0][0] if hours else None

        return {
            "total": total,
            "avg_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
            "context_switches": context_switches,
            "debug_ratio": round(debug_count / total, 2) if total else 0.0,
            "peak_hour": peak_hour,
            "request_types": dict(types),
            "hourly_distribution": dict(hours),
            "states": dict(states),
        }

    def generate_report(self, date: datetime | None = None) -> str:
        """Generate a coaching report prompt for Claude to process.

        Args:
            date: Target date (defaults to today).

        Returns:
            A prompt string that Claude should process to produce the coaching report.
        """
        if date is None:
            date = datetime.now()

        records = self.pattern_learner.get_today_records()
        metrics = self.calculate_metrics(records)

        # Also get weekly patterns for trend analysis
        weekly = self.pattern_learner.extract_patterns(days=7)

        date_str = date.strftime("%Y-%m-%d")

        prompt = (
            f"[Daily Coach] {date_str} 코칭 리포트를 작성해주세요.\n\n"
            f"오늘의 데이터:\n"
            f"- 총 요청: {metrics['total']}회\n"
            f"- 평균 응답 시간: {metrics['avg_duration_ms']}ms\n"
            f"- 컨텍스트 전환: {metrics['context_switches']}회\n"
            f"- 디버깅 비율: {metrics['debug_ratio']:.0%}\n"
            f"- 피크 시간: {metrics['peak_hour']}시\n"
            f"- 요청 유형: {metrics['request_types']}\n"
            f"- 시간대별 분포: {metrics['hourly_distribution']}\n"
            f"- 상태 분포: {metrics['states']}\n\n"
            f"주간 패턴 (7일):\n"
            f"- 총 요청: {weekly['total']}회\n"
            f"- 피크 시간대: {weekly['peak_hours']}\n"
            f"- 요청 유형 분포: {weekly['request_types']}\n\n"
            f"다음 형식으로 직설적인 코칭 리포트를 작성하세요:\n"
            f"1. 생산성 점수 (1-10)\n"
            f"2. 잘한 점 (bullet 2-3개)\n"
            f"3. 개선 포인트 (구체적 제안 포함, bullet 2-3개)\n"
            f"4. 이번 주 트렌드 (패턴 분석)\n\n"
            f"직설적이되 건설적으로. 아첨 금지. 한국어로 작성."
        )
        return prompt
