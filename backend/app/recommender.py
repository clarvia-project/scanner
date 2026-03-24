"""Intent-based tool recommendation engine for Clarvia.

Uses TF-IDF with synonym expansion to match user intents to tools.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .synonym_dict import expand_intent

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """TF-IDF based recommendation engine with synonym expansion."""

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix = None
        self._tools: list[dict[str, Any]] = []
        self._built = False

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def build_index(self, tools: list[dict[str, Any]]) -> None:
        """Build TF-IDF index from tool list.

        Each tool should have: service_name, description, tags, category, service_type.
        """
        if not tools:
            logger.warning("No tools to index")
            return

        self._tools = tools

        # Build document corpus: name + description + tags + category + type
        documents = []
        for tool in tools:
            parts = [
                tool.get("service_name", ""),
                tool.get("description", ""),
                " ".join(tool.get("tags", [])),
                tool.get("category", ""),
                tool.get("service_type", ""),
            ]
            # Add type_config hints for richer matching
            tc = tool.get("type_config") or {}
            if tc.get("npm_package"):
                parts.append(tc["npm_package"])
            if tc.get("tools") and isinstance(tc["tools"], list):
                parts.extend(str(t) for t in tc["tools"][:5])

            documents.append(" ".join(filter(None, parts)).lower())

        self._vectorizer = TfidfVectorizer(
            max_features=15000,
            ngram_range=(1, 2),  # unigrams + bigrams
            stop_words="english",
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(documents)
        self._built = True
        logger.info(
            "Built TF-IDF index: %d tools, %d features",
            len(tools),
            self._tfidf_matrix.shape[1],
        )

    def recommend(
        self,
        intent: str,
        *,
        limit: int = 10,
        min_score: int = 0,
        service_type: str | None = None,
        category: str | None = None,
        relevance_weight: float = 0.6,
        quality_weight: float = 0.4,
    ) -> dict[str, Any]:
        """Recommend tools based on user intent.

        Returns dict with intent_parsed, recommendations, total_candidates, method.
        """
        if not self._built or self._vectorizer is None:
            return {
                "intent_parsed": {"original": intent, "expanded_terms": []},
                "recommendations": [],
                "total_candidates": 0,
                "method": "not_ready",
            }

        # Expand intent with synonyms
        expanded_terms = expand_intent(intent)
        expanded_query = " ".join(expanded_terms)

        # Vectorize and compute similarity
        query_vec = self._vectorizer.transform([expanded_query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Build candidates with scores
        max_clarvia = max((t["clarvia_score"] for t in self._tools), default=1) or 1

        candidates = []
        for idx, sim_score in enumerate(similarities):
            if sim_score < 0.01:  # skip irrelevant
                continue

            tool = self._tools[idx]

            # Apply filters
            if tool["clarvia_score"] < min_score:
                continue
            if service_type and tool.get("service_type") != service_type:
                continue
            if category and tool.get("category") != category:
                continue

            normalized_quality = tool["clarvia_score"] / max_clarvia
            combined = (relevance_weight * sim_score) + (quality_weight * normalized_quality)

            # Build match reason
            match_reason = _build_match_reason(intent, tool, expanded_terms)

            # Build install hint
            install_hint = _build_install_hint(tool)

            candidates.append({
                "name": tool["service_name"],
                "scan_id": tool["scan_id"],
                "url": tool.get("url", ""),
                "description": tool.get("description", ""),
                "category": tool.get("category", "other"),
                "service_type": tool.get("service_type", "general"),
                "clarvia_score": tool["clarvia_score"],
                "rating": tool["rating"],
                "relevance_score": round(float(sim_score), 4),
                "combined_score": round(float(combined), 4),
                "match_reason": match_reason,
                "install_hint": install_hint,
                "tags": tool.get("tags", []),
            })

        # Sort by combined score
        candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        top = candidates[:limit]

        return {
            "intent_parsed": {
                "original": intent,
                "expanded_terms": expanded_terms[:20],
            },
            "recommendations": top,
            "total_candidates": len(candidates),
            "method": "tfidf+synonyms",
        }


def _build_match_reason(intent: str, tool: dict, expanded_terms: list[str]) -> str:
    """Build a human-readable match reason."""
    intent_lower = intent.lower()
    name_lower = tool.get("service_name", "").lower()
    desc_lower = tool.get("description", "").lower()
    combined = f"{name_lower} {desc_lower}"

    matched = []
    # Check which expanded terms actually match the tool
    for term in expanded_terms:
        if len(term) >= 3 and term in combined:
            matched.append(term)
            if len(matched) >= 3:
                break

    if matched:
        return f"Matched: {', '.join(matched)}"
    return f"Related to: {intent[:50]}"


def _build_install_hint(tool: dict) -> str | None:
    """Generate install hint based on tool type."""
    stype = tool.get("service_type", "general")
    tc = tool.get("type_config") or {}
    name = tool.get("service_name", "")

    if stype == "mcp_server":
        if tc.get("npm_package"):
            pkg = tc["npm_package"]
            return f"npx -y {pkg}"
        # Try name-based hint
        safe = re.sub(r"[^a-z0-9@/_-]", "", name.lower())
        if safe:
            return f"claude mcp add {safe}"
        return None

    if stype == "cli_tool":
        if tc.get("install_command"):
            return tc["install_command"]
        return None

    if stype == "api":
        url = tc.get("base_url") or tc.get("openapi_url") or tool.get("url", "")
        if url:
            return f"API: {url}"
        return None

    return None


# Singleton engine
_engine = RecommendationEngine()


def get_engine() -> RecommendationEngine:
    """Get the singleton recommendation engine."""
    return _engine
