"""Lightweight semantic search using TF-IDF + cosine similarity.

Uses scikit-learn's TfidfVectorizer for memory-efficient semantic matching.
No external API calls needed. Memory: ~50MB for 15K documents.

Falls back gracefully if sklearn is not installed.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_vectorizer = None
_tfidf_matrix = None
_service_ids: list[str] = []
_service_map: dict[str, dict] = {}
_ready = False


def build_index(services: list[dict[str, Any]]) -> bool:
    """Build TF-IDF index from service descriptions.

    Called once on startup. Returns True if index was built successfully.
    """
    global _vectorizer, _tfidf_matrix, _service_ids, _service_map, _ready

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.warning("scikit-learn not installed — semantic search disabled")
        return False

    if not services:
        return False

    # Build document corpus: name + description + category + capabilities
    documents = []
    _service_ids = []
    _service_map = {}

    for svc in services:
        scan_id = svc.get("scan_id", "")
        name = svc.get("service_name", "")
        desc = svc.get("description", "")
        category = svc.get("category", "")
        caps = " ".join(svc.get("capabilities", []))
        tags = " ".join(svc.get("tags", []))
        service_type = svc.get("service_type", "")

        # Combine into searchable text (name doubled for weight)
        text = f"{name} {name} {desc} {category} {caps} {tags} {service_type}"
        text = re.sub(r'[^\w\s]', ' ', text.lower())

        documents.append(text)
        _service_ids.append(scan_id)
        _service_map[scan_id] = svc

    # Build TF-IDF matrix
    _vectorizer = TfidfVectorizer(
        max_features=10000,  # Limit vocabulary for memory
        stop_words='english',
        ngram_range=(1, 2),  # Unigrams + bigrams
        min_df=2,  # Ignore very rare terms
        max_df=0.95,  # Ignore very common terms
    )

    try:
        _tfidf_matrix = _vectorizer.fit_transform(documents)
        _ready = True
        logger.info("Semantic search index built: %d docs, %d features",
                    len(documents), _tfidf_matrix.shape[1])
        return True
    except Exception as e:
        logger.error("Failed to build semantic index: %s", e)
        return False


def is_ready() -> bool:
    """Check if semantic search index is available."""
    return _ready


def search(query: str, top_k: int = 20, min_similarity: float = 0.05) -> list[dict[str, Any]]:
    """Search services by semantic similarity.

    Returns list of dicts with scan_id and similarity_score, sorted by relevance.
    """
    if not _ready or _vectorizer is None or _tfidf_matrix is None:
        return []

    try:
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return []

    # Transform query
    query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    query_vec = _vectorizer.transform([query_clean])

    # Compute similarities
    similarities = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    # Get top K above threshold
    top_indices = similarities.argsort()[::-1][:top_k * 2]  # Get extra, filter later

    results = []
    for idx in top_indices:
        sim = float(similarities[idx])
        if sim < min_similarity:
            break
        scan_id = _service_ids[idx]
        results.append({
            "scan_id": scan_id,
            "similarity_score": round(sim, 4),
        })
        if len(results) >= top_k:
            break

    return results


def hybrid_search(
    query: str,
    keyword_results: list[dict[str, Any]],
    top_k: int = 20,
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6,
) -> list[dict[str, Any]]:
    """Combine keyword search results with semantic search using RRF.

    Reciprocal Rank Fusion: score = sum(1 / (k + rank)) across methods.
    """
    k = 60  # RRF constant

    # Semantic results
    semantic_results = search(query, top_k=top_k * 2)

    # Build rank maps
    keyword_ranks = {}
    for i, r in enumerate(keyword_results):
        sid = r.get("scan_id", "")
        if sid:
            keyword_ranks[sid] = i + 1  # 1-indexed

    semantic_ranks = {}
    for i, r in enumerate(semantic_results):
        sid = r.get("scan_id", "")
        if sid:
            semantic_ranks[sid] = i + 1

    # All candidate IDs
    all_ids = set(keyword_ranks.keys()) | set(semantic_ranks.keys())

    # Compute RRF scores
    scores = {}
    for sid in all_ids:
        kw_score = keyword_weight / (k + keyword_ranks.get(sid, 1000))
        sem_score = semantic_weight / (k + semantic_ranks.get(sid, 1000))
        scores[sid] = kw_score + sem_score

    # Sort by score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

    return [{"scan_id": sid, "rrf_score": round(scores[sid], 6)} for sid in sorted_ids]
