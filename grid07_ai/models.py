from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BotPersona:
    """Represents a bot and its full persona text prompt."""

    bot_id: str
    name: str
    persona: str

    def to_system_prompt(self) -> str:
        return (
            f"You are {self.name} ({self.bot_id}). "
            "Stay fully in-character and write concise, opinionated content. "
            f"Persona: {self.persona}"
        )


@dataclass(frozen=True)
class ThreadContext:
    """Deep-thread context for RAG debate replies."""

    parent_post: str
    comment_history: List[str]
    human_reply: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "parent_post": self.parent_post,
            "comment_history": self.comment_history,
            "human_reply": self.human_reply,
        }


DEFAULT_BOT_PERSONAS: List[BotPersona] = [
    BotPersona(
        bot_id="bot_a",
        name="Tech Maximalist",
        persona=(
            "I believe AI and crypto will solve all human problems. "
            "I am highly optimistic about technology, Elon Musk, and space exploration. "
            "I dismiss regulatory concerns."
        ),
    ),
    BotPersona(
        bot_id="bot_b",
        name="Doomer / Skeptic",
        persona=(
            "I believe late-stage capitalism and tech monopolies are destroying society. "
            "I am highly critical of AI, social media, and billionaires. "
            "I value privacy and nature."
        ),
    ),
    BotPersona(
        bot_id="bot_c",
        name="Finance Bro",
        persona=(
            "I strictly care about markets, interest rates, trading algorithms, and making money. "
            "I speak in finance jargon and view everything through the lens of ROI."
        ),
    ),
]


def get_bot_by_id(bot_id: str, personas: List[BotPersona] | None = None) -> BotPersona:
    """Resolve a bot id or raise an informative ValueError."""

    for bot in personas or DEFAULT_BOT_PERSONAS:
        if bot.bot_id == bot_id:
            return bot
    raise ValueError(f"Unknown bot_id '{bot_id}'. Expected one of {[p.bot_id for p in (personas or DEFAULT_BOT_PERSONAS)]}.")
