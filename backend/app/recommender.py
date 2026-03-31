"""Intent-based tool recommendation engine for Clarvia.

Uses TF-IDF with synonym expansion, exact-name boosting, and
category-aware scoring to match user intents to tools.
"""

from __future__ import annotations

import logging
import re
from typing import Any

# sklearn imports are deferred to build_index() / recommend() to avoid loading
# ~80-150 MB of numpy+sklearn into RAM at startup.  On a 512 MB Render Starter
# instance this is the difference between OOM and stable operation.

from .synonym_dict import expand_intent

logger = logging.getLogger(__name__)

# Name-match boost: when the query exactly matches or contains the tool name
_NAME_EXACT_BOOST = 0.35
_NAME_PARTIAL_BOOST = 0.15

# Penalize tools whose description is empty or very short (< 20 chars)
_NO_DESC_PENALTY = 0.5


class RecommendationEngine:
    """TF-IDF based recommendation engine with synonym expansion."""

    def __init__(self) -> None:
        self._vectorizer = None  # TfidfVectorizer, lazily imported
        self._tfidf_matrix = None
        self._tools: list[dict[str, Any]] = []
        self._name_lower: list[str] = []  # pre-computed lowercase names
        self._built = False

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def build_index(self, tools: list[dict[str, Any]]) -> None:
        """Build TF-IDF index from tool list.

        Each tool should have: service_name, description, tags, category, service_type,
        capabilities, popularity.
        """
        if not tools:
            logger.warning("No tools to index")
            return

        self._tools = tools
        self._name_lower = [t.get("service_name", "").lower().strip() for t in tools]

        # Build document corpus — name repeated for emphasis, plus desc/tags/category/capabilities
        documents = []
        for tool in tools:
            name = tool.get("service_name", "")
            parts = [
                name,
                name,  # repeat name to boost its weight
                tool.get("description", ""),
                " ".join(tool.get("tags", [])),
                tool.get("category", ""),
                tool.get("service_type", ""),
                # Include capabilities for better matching
                " ".join(c.replace("_", " ").replace(":", " ") for c in tool.get("capabilities", [])),
            ]
            tc = tool.get("type_config") or {}
            if tc.get("npm_package"):
                parts.append(tc["npm_package"])
            if tc.get("tools") and isinstance(tc["tools"], list):
                parts.extend(str(t) for t in tc["tools"][:5])

            documents.append(" ".join(filter(None, parts)).lower())

        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=5000,   # Reduced from 15k — saves ~20 MB sparse matrix RAM
            ngram_range=(1, 2),
            stop_words="english",
            min_df=2,            # Raised from 1 — skip unique terms, saves memory
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

        intent_lower = intent.lower().strip()

        # Expand intent with synonyms
        expanded_terms = expand_intent(intent)
        expanded_query = " ".join(expanded_terms)

        # Vectorize and compute similarity
        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self._vectorizer.transform([expanded_query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        max_clarvia = max((t["clarvia_score"] for t in self._tools), default=1) or 1

        # Pre-compute: detect if intent looks like a product name (single word, no spaces/verbs)
        intent_words = intent_lower.split()
        is_name_query = len(intent_words) <= 2 and not any(
            w in intent_words for w in ("want", "need", "how", "to", "can", "should", "help")
        )

        # Tokenize query for keyword hit counting
        query_tokens = set(re.findall(r"[a-z0-9]{2,}", intent_lower))
        query_tokens.update(t for t in expanded_terms if len(t) >= 2)

        candidates = []
        for idx, sim_score in enumerate(similarities):
            if sim_score < 0.005:
                continue

            tool = self._tools[idx]

            # Apply filters
            if tool["clarvia_score"] < min_score:
                continue
            if service_type and tool.get("service_type", "").lower().replace(" ", "_") != service_type.lower().replace(" ", "_"):
                continue
            if category and tool.get("category", "").lower() != category.lower():
                continue

            # --- Scoring ---
            name_lower = self._name_lower[idx]
            boost = 0.0

            # Exact name match boost
            if is_name_query:
                if name_lower == intent_lower or intent_lower == name_lower.replace(" ", ""):
                    boost = _NAME_EXACT_BOOST
                elif intent_lower in name_lower or name_lower in intent_lower:
                    boost = _NAME_PARTIAL_BOOST

            # Penalize tools with missing/empty description (low quality signal)
            desc = tool.get("description", "")
            quality_mult = _NO_DESC_PENALTY if len(desc) < 20 else 1.0

            # Count keyword hits across name + description + tags + capabilities
            tool_text = f"{name_lower} {desc.lower()} {' '.join(tool.get('tags', []))} {' '.join(tool.get('capabilities', []))}".lower()
            keyword_hits = sum(1 for token in query_tokens if token in tool_text)

            popularity = tool.get("popularity", 0)

            # TF-IDF relevance combined with keyword hits, clarvia score, and popularity
            # relevance_score = keyword_hits * 10 + clarvia_score * 0.5 + popularity * 0.3
            relevance_score = keyword_hits * 10 + tool["clarvia_score"] * 0.5 + popularity * 0.3

            # Blend TF-IDF similarity with the new relevance score
            normalized_quality = (tool["clarvia_score"] / max_clarvia) * quality_mult
            combined = (
                relevance_weight * sim_score
                + quality_weight * normalized_quality
                + boost
                + (relevance_score / 200)  # normalize to ~0-1 range for blending
            )

            match_reason = _build_match_reason(intent, tool, expanded_terms)
            install_hint = _build_install_hint(tool)

            candidates.append({
                "name": tool["service_name"],
                "scan_id": tool["scan_id"],
                "url": tool.get("url", ""),
                "description": desc,
                "category": tool.get("category", "other"),
                "service_type": tool.get("service_type", "general"),
                "clarvia_score": tool["clarvia_score"],
                "rating": tool["rating"],
                "relevance_score": round(float(sim_score), 4),
                "combined_score": round(float(combined), 4),
                "match_score": {
                    "keyword_hits": keyword_hits,
                    "tfidf_similarity": round(float(sim_score), 4),
                    "clarvia_component": round(tool["clarvia_score"] * 0.5, 1),
                    "popularity_component": round(popularity * 0.3, 1),
                    "raw_relevance": round(relevance_score, 1),
                },
                "match_reason": match_reason,
                "install_hint": install_hint,
                "tags": tool.get("tags", []),
                "popularity": popularity,
                "capabilities": tool.get("capabilities", [])[:5],
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
            "method": "tfidf+synonyms+boost",
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
