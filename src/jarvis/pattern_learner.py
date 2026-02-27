"""Pattern learner — logs interactions and extracts usage patterns.

Records every bot interaction to interactions.jsonl, then provides
pattern extraction for coaching and preemptive action triggers.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import structlog

from .persona import ContextState

logger = structlog.get_logger()

# Request type classification patterns
_TYPE_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "debug",
        [
            re.compile(r"(에러|error|bug|fix|왜.*안|traceback|오류|디버그)", re.I),
            re.compile(r"(안\s*[되됨]|문제|crash|fail)", re.I),
        ],
    ),
    (
        "feature",
        [
            re.compile(r"(만들어|추가|구현|implement|add|create|build)", re.I),
            re.compile(r"(기능|feature|새로)", re.I),
        ],
    ),
    (
        "question",
        [
            re.compile(r"(뭐야|무엇|어떻게|왜|what|how|why|explain|설명)", re.I),
            re.compile(r"\?$"),
        ],
    ),
    (
        "brainstorm",
        [
            re.compile(r"(아이디어|설계|design|plan|구조|architecture|방법)", re.I),
            re.compile(r"(어떤.*좋|제안|suggest|recommend)", re.I),
        ],
    ),
]

DEFAULT_TYPE = "admin"


class PatternLearner:
    """Logs interactions and extracts behavioral patterns."""

    def __init__(self, memory_base: str | Path) -> None:
        self.memory_base = Path(memory_base)
        self.patterns_dir = self.memory_base / "patterns"
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.interactions_path = self.patterns_dir / "interactions.jsonl"
        self.routines_path = self.patterns_dir / "routines.json"

    def log_interaction(
        self,
        user_id: int,
        prompt: str,
        response: str,
        duration_ms: int,
        tools_used: list[str] | None = None,
        state: ContextState | None = None,
    ) -> None:
        """Append an interaction record to interactions.jsonl."""
        now = datetime.now()
        record = {
            "ts": now.isoformat(),
            "dow": now.strftime("%a").lower(),
            "hour": now.hour,
            "user_id": user_id,
            "state": state.value if state else "UNKNOWN",
            "request_type": self._classify_request(prompt),
            "prompt_length": len(prompt),
            "response_length": len(response),
            "duration_ms": duration_ms,
            "tools_used": tools_used or [],
        }
        try:
            with open(self.interactions_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to log interaction")

    def _classify_request(self, prompt: str) -> str:
        """Classify a user prompt into a request type."""
        for rtype, patterns in _TYPE_PATTERNS:
            for pat in patterns:
                if pat.search(prompt):
                    return rtype
        return DEFAULT_TYPE

    def extract_patterns(self, days: int = 7) -> dict[str, Any]:
        """Extract usage patterns from recent interactions.

        Returns:
            Dict with hourly_counts, peak_hours, request_types, avg_duration.
        """
        cutoff = datetime.now() - timedelta(days=days)
        records = self._load_records(cutoff)

        if not records:
            return {
                "hourly_counts": {},
                "peak_hours": [],
                "request_types": {},
                "avg_duration": 0,
                "total": 0,
            }

        hourly: Counter[int] = Counter()
        types: Counter[str] = Counter()
        durations: list[int] = []

        for rec in records:
            hourly[rec.get("hour", 0)] += 1
            types[rec.get("request_type", DEFAULT_TYPE)] += 1
            if "duration_ms" in rec:
                durations.append(rec["duration_ms"])

        sorted_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [h for h, _ in sorted_hours[:4]]

        return {
            "hourly_counts": dict(hourly),
            "peak_hours": peak_hours,
            "request_types": dict(types),
            "avg_duration": int(sum(durations) / len(durations)) if durations else 0,
            "total": len(records),
        }

    def check_preemptive(
        self, state: ContextState, hour: int
    ) -> Optional[dict[str, Any]]:
        """Check if a preemptive action should trigger based on learned routines.

        Returns matching routine dict if confidence > 0.7, else None.
        """
        if not self.routines_path.exists():
            return None

        try:
            data = json.loads(self.routines_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        dow = datetime.now().strftime("%a").lower()

        for routine in data.get("routines", []):
            confidence = routine.get("confidence", 0)
            if confidence < 0.7:
                continue
            pattern = routine.get("pattern", "")
            # Simple matching: check if day-of-week or hour appears in pattern
            if dow in pattern.lower() or str(hour) in pattern:
                return routine

        return None

    def _load_records(
        self, cutoff: Optional[datetime] = None
    ) -> list[dict[str, Any]]:
        """Load interaction records, optionally filtering by cutoff date."""
        if not self.interactions_path.exists():
            return []

        records: list[dict[str, Any]] = []
        try:
            with open(self.interactions_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if cutoff:
                        ts = rec.get("ts", "")
                        try:
                            if datetime.fromisoformat(ts) < cutoff:
                                continue
                        except ValueError:
                            continue
                    records.append(rec)
        except Exception:
            logger.exception("Failed to load interaction records")

        return records

    def get_today_records(self) -> list[dict[str, Any]]:
        """Get all interaction records from today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._load_records(cutoff=today_start)
