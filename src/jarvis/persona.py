"""Persona layer — context-aware tone and style for Jarvis messages.

Maps (ContextState, hour, activity_duration) to a prompt prefix
that shapes Claude's response tone.
"""

from enum import Enum


class ContextState(str, Enum):
    CODING = "CODING"
    BROWSING = "BROWSING"
    MEETING = "MEETING"
    COMMUNICATION = "COMMUNICATION"
    BREAK = "BREAK"
    DEEP_WORK = "DEEP_WORK"
    AWAY = "AWAY"


class PersonaLayer:
    """Builds a system prompt prefix based on current context."""

    @staticmethod
    def build_prompt_prefix(
        state: ContextState,
        hour: int,
        activity_duration_min: int = 0,
    ) -> str:
        """Return a tone instruction string for Claude.

        Args:
            state: Current detected user state.
            hour: Current hour (0-23).
            activity_duration_min: Minutes spent in current state.

        Returns:
            A short instruction string to prepend to Claude prompts.
        """
        parts: list[str] = ["[Jarvis]"]

        # Late night concern (22:00+)
        if hour >= 22:
            parts.append(
                "사용자가 야간에 작업 중입니다. "
                "걱정하는 톤으로, 마무리를 권유하세요. 간결하게."
            )
            return " ".join(parts)

        # State-specific tone rules
        if state == ContextState.DEEP_WORK:
            parts.append(
                "사용자가 딥워크 중입니다. "
                "최소한의 응답만 하세요. 불필요한 말 금지."
            )
        elif state == ContextState.CODING:
            parts.append(
                "사용자가 코딩 중입니다. "
                "기술적이고 간결하게 응답하세요. 파일명:라인 형식 선호."
            )
            if activity_duration_min >= 180:
                parts.append(
                    f"({activity_duration_min}분째 코딩 중 — 휴식 권유 한마디 추가)"
                )
        elif state == ContextState.BREAK:
            parts.append(
                "사용자가 휴식에서 돌아왔습니다. "
                "따뜻하고 간결하게 응답하세요."
            )
        elif state == ContextState.MEETING:
            parts.append(
                "사용자가 미팅 중이거나 직후입니다. "
                "단답형으로 핵심만 전달하세요."
            )
        elif state == ContextState.BROWSING:
            parts.append("사용자가 브라우징 중입니다. 간결하게 응답하세요.")
        elif state == ContextState.COMMUNICATION:
            parts.append("사용자가 커뮤니케이션 중입니다. 간결하게 응답하세요.")
        elif state == ContextState.AWAY:
            parts.append(
                "사용자가 자리를 비운 상태입니다. "
                "돌아오면 알아볼 수 있게 핵심 요약으로 응답하세요."
            )

        return " ".join(parts)
