from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence

from grid07_ai.embeddings import HashEmbeddings, cosine_similarity
from grid07_ai.models import BotPersona, DEFAULT_BOT_PERSONAS


@dataclass(frozen=True)
class RoutingMatch:
    bot_id: str
    bot_name: str
    similarity: float

    def to_dict(self) -> Dict[str, float | str]:
        data = asdict(self)
        data["similarity"] = round(float(data["similarity"]), 4)
        return data


class InMemoryVectorStore:
    """Simple in-memory vector store to simulate pgvector/FAISS behavior."""

    def __init__(self) -> None:
        self.items: List[Dict[str, object]] = []

    def add(self, vector: Sequence[float], metadata: Dict[str, str]) -> None:
        self.items.append({"vector": list(vector), "metadata": metadata})

    def similarity_search(self, query_vector: Sequence[float]) -> List[RoutingMatch]:
        scored: List[RoutingMatch] = []
        for item in self.items:
            vector = item["vector"]
            metadata = item["metadata"]
            score = cosine_similarity(query_vector, vector)  # type: ignore[arg-type]
            scored.append(
                RoutingMatch(
                    bot_id=str(metadata["bot_id"]),  # type: ignore[index]
                    bot_name=str(metadata["bot_name"]),  # type: ignore[index]
                    similarity=float(score),
                )
            )
        scored.sort(key=lambda x: x.similarity, reverse=True)
        return scored


class PersonaRouter:
    """Vector-based bot matcher using in-memory vector search and cosine similarity."""

    def __init__(self, personas: List[BotPersona] | None = None, dimension: int = 384) -> None:
        self.personas = personas or DEFAULT_BOT_PERSONAS
        self.embedding_model = HashEmbeddings(dimension=dimension)
        self.vector_store = InMemoryVectorStore()
        self._build_index()

    def _build_index(self) -> None:
        for persona in self.personas:
            vector = self.embedding_model.embed_text(persona.persona)
            self.vector_store.add(
                vector,
                metadata={"bot_id": persona.bot_id, "bot_name": persona.name},
            )

    def ranked_matches(self, post_content: str) -> List[RoutingMatch]:
        query_vector = self.embedding_model.embed_text(post_content)
        return self.vector_store.similarity_search(query_vector)

    def route_post_to_bots(self, post_content: str, threshold: float = 0.85) -> List[Dict[str, float | str]]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        matches = [m for m in self.ranked_matches(post_content) if m.similarity >= threshold]
        return [m.to_dict() for m in matches]

    def suggest_threshold(self, post_content: str) -> float:
        """Suggest a practical threshold based on score distribution for this post."""

        scores = [m.similarity for m in self.ranked_matches(post_content)]
        if not scores:
            return 0.85

        # midpoint between top two if possible, else scaled top score
        if len(scores) >= 2:
            return round(max(0.05, min(0.95, (scores[0] + scores[1]) / 2.0)), 2)
        return round(max(0.05, min(0.95, scores[0] * 0.8)), 2)


# Required assignment signature.
def route_post_to_bots(post_content: str, threshold: float = 0.85) -> List[Dict[str, float | str]]:
    router = PersonaRouter()
    return router.route_post_to_bots(post_content=post_content, threshold=threshold)
