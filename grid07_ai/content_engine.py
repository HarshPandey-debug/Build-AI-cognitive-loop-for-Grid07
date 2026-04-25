from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Callable, Dict, List, MutableMapping, Protocol

from grid07_ai.models import BotPersona

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover

    def tool(func: Callable[..., Any]) -> Callable[..., Any]:
        """Fallback decorator when langchain is unavailable."""

        return func


@dataclass
class GeneratedPost:
    bot_id: str
    topic: str
    post_content: str

    def to_json_dict(self) -> Dict[str, str]:
        payload = asdict(self)
        required = {"bot_id", "topic", "post_content"}
        if set(payload.keys()) != required:
            raise ValueError(f"JSON schema mismatch. Expected {required}, got {set(payload.keys())}")
        if len(payload["post_content"]) > 280:
            payload["post_content"] = payload["post_content"][:280]
        return payload


@tool
def mock_searxng_search(query: str) -> List[str]:
    """Return hardcoded news-like headlines based on query keywords."""

    q = query.lower()
    dated_prefix = f"[{date.today().isoformat()}]"

    if "crypto" in q or "bitcoin" in q:
        return [
            f"{dated_prefix} Bitcoin extends breakout as ETF flows remain elevated.",
            f"{dated_prefix} Policymakers debate stablecoin reserve requirements after market expansion.",
        ]
    if "ai" in q or "openai" in q or "model" in q or "agent" in q:
        return [
            f"{dated_prefix} AI labs compete on autonomous coding agents for enterprise rollout.",
            f"{dated_prefix} New AI governance proposals target provenance and eval transparency.",
        ]
    if "rates" in q or "inflation" in q or "market" in q:
        return [
            f"{dated_prefix} Central bank officials emphasize data dependence as inflation moderates.",
            f"{dated_prefix} Equity volatility rises as rate-cut expectations reprice.",
        ]
    return [
        f"{dated_prefix} Energy transition and industrial policy remain central macro themes.",
        f"{dated_prefix} Platform regulation debates intensify across major technology markets.",
    ]


class LLMAdapterProtocol(Protocol):
    def choose_topic_and_query(self, bot: BotPersona) -> Dict[str, str]: ...

    def draft_post(self, bot: BotPersona, topic: str, search_results: List[str]) -> GeneratedPost: ...


class LLMAdapter:
    """Mock-first adapter with deterministic behavior for offline execution."""

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower()

    def choose_topic_and_query(self, bot: BotPersona) -> Dict[str, str]:
        persona = bot.persona.lower()
        if "crypto" in persona or "space" in persona or "optimistic" in persona:
            return {
                "topic": "AI acceleration and frontier innovation",
                "query": "latest ai model launch autonomous coding agent regulation",
            }
        if "market" in persona or "roi" in persona or "rates" in persona:
            return {
                "topic": "Rates, risk assets, and monetizable edge",
                "query": "latest fed rates inflation equities volatility",
            }
        return {
            "topic": "Tech concentration and social externalities",
            "query": "ai monopoly social media billionaires privacy policy",
        }

    def draft_post(self, bot: BotPersona, topic: str, search_results: List[str]) -> GeneratedPost:
        context = " | ".join(search_results)
        post = (
            f"{topic}: {context} My take: {bot.name} says the trend is obvious—"
            "adapt faster than incumbents or pay the opportunity cost."
        )
        return GeneratedPost(bot_id=bot.bot_id, topic=topic, post_content=_truncate_to_limit(post, 280))


class MiniGraph:
    """Sequential graph runner mirroring LangGraph node semantics."""

    def __init__(self, nodes: List[Callable[[MutableMapping[str, Any]], MutableMapping[str, Any]]]) -> None:
        self.nodes = nodes

    def invoke(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        for node in self.nodes:
            state = node(state)
        return state


def build_content_graph(llm: LLMAdapterProtocol) -> MiniGraph:
    """Build three-node orchestration flow: decide -> search -> draft."""

    def decide_search(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        picked = llm.choose_topic_and_query(state["bot"])
        state["topic"] = picked["topic"]
        state["query"] = picked["query"]
        return state

    def do_search(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        state["search_results"] = mock_searxng_search(state["query"])
        return state

    def draft(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        result = llm.draft_post(state["bot"], state["topic"], state["search_results"])
        state["output"] = result.to_json_dict()
        return state

    return MiniGraph([decide_search, do_search, draft])


def generate_post(bot: BotPersona) -> Dict[str, Any]:
    """Generate a strict JSON post object from persona + mocked real-world context."""

    llm = LLMAdapter()
    graph = build_content_graph(llm)
    initial_state: Dict[str, Any] = {
        "bot": bot,
        "query": "",
        "topic": "",
        "search_results": [],
        "output": {},
    }
    final_state = graph.invoke(initial_state)

    # Guard: ensure strict JSON serializability and schema.
    payload = final_state["output"]
    canonical = json.loads(json.dumps(payload))
    if set(canonical.keys()) != {"bot_id", "topic", "post_content"}:
        raise ValueError("Final output must be exactly: bot_id, topic, post_content")

    return canonical


def _truncate_to_limit(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped + "…"
