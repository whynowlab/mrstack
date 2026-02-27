"""Jarvis mode — proactive context-aware AI partner.

JarvisEngine is the facade that composes:
- ContextEngine: system state polling + trigger evaluation
- PatternLearner: interaction logging + pattern extraction
- DailyCoach: productivity coaching reports
- PersonaLayer: context-aware tone injection
"""

from pathlib import Path
from typing import List, Optional

import structlog

from ..events.bus import EventBus
from .coach import DailyCoach
from .context_engine import ContextEngine
from .pattern_learner import PatternLearner
from .persona import ContextState, PersonaLayer

logger = structlog.get_logger()

__all__ = [
    "JarvisEngine",
    "ContextState",
    "PersonaLayer",
    "PatternLearner",
    "DailyCoach",
    "ContextEngine",
]


class JarvisEngine:
    """Facade combining all Jarvis sub-modules."""

    def __init__(
        self,
        event_bus: EventBus,
        target_chat_ids: List[int],
        working_directory: str = "",
        memory_base: str = "",
    ) -> None:
        if not working_directory:
            working_directory = str(Path.home())
        if not memory_base:
            memory_base = str(Path.home() / "claude-telegram" / "memory")
        self.pattern_learner = PatternLearner(memory_base)
        self.context_engine = ContextEngine(
            event_bus=event_bus,
            target_chat_ids=target_chat_ids,
            working_directory=working_directory,
            pattern_learner=self.pattern_learner,
        )
        self.coach = DailyCoach(memory_base)
        self.persona = PersonaLayer()

    @property
    def enabled(self) -> bool:
        return self.context_engine.enabled

    @property
    def current_state(self) -> ContextState:
        return self.context_engine.current_state

    def toggle(self) -> bool:
        """Toggle Jarvis on/off. Returns new state."""
        return self.context_engine.toggle()

    async def start(self) -> None:
        """Start the context engine polling loop."""
        await self.context_engine.start()
        logger.info("Jarvis engine started")

    async def stop(self) -> None:
        """Stop the context engine polling loop."""
        await self.context_engine.stop()
        logger.info("Jarvis engine stopped")
