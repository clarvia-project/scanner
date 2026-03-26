"""Setup API — Register, compare, and get recommendations for user tool setups."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/setup", tags=["setup"])

# ---------------------------------------------------------------------------
# Categories for classification
# ---------------------------------------------------------------------------
VALID_CATEGORIES = [
    "data-analytics", "database", "iot", "developer-tools", "ai-agents",
    "search", "design", "file-management", "communication", "blockchain",
    "security", "general",
]

# ---------------------------------------------------------------------------
# Data file path
# ---------------------------------------------------------------------------
_SETUPS_FILE: Path | None = None


def _get_setups_file() -> Path:
    global _SETUPS_FILE
    if _SETUPS_FILE is not None:
        return _SETUPS_FILE

    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break
    for d in candidates:
        if d.is_dir():
            _SETUPS_FILE = d / "user_setups.json"
            return _SETUPS_FILE

    # Fallback: create next to backend
    fallback = base.parents[3] / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    _SETUPS_FILE = fallback / "user_setups.json"
    return _SETUPS_FILE


def _load_setups() -> dict[str, Any]:
    fp = _get_setups_file()
    if not fp.exists():
        return {}
    try:
        with open(fp, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_setups(data: dict[str, Any]) -> None:
    fp = _get_setups_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers: resolve tools against Clarvia index
# ---------------------------------------------------------------------------
def _get_all_tools() -> list[dict[str, Any]]:
    """Load all tools from the index (scanned + collected)."""
    from . import index_routes

    index_routes._ensure_loaded()
    index_routes._load_collected()

    scanned_ids = {s["scan_id"] for s in index_routes._services}
    return list(index_routes._services) + [
        t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
    ]


def _find_tool(name: str, all_tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fuzzy-match a tool name against the index."""
    name_lower = name.lower().strip()

    # Exact match on service_name
    for t in all_tools:
        if t.get("service_name", "").lower().strip() == name_lower:
            return t

    # Partial match
    for t in all_tools:
        sn = t.get("service_name", "").lower()
        if name_lower in sn or sn in name_lower:
            return t

    # Check tags
    for t in all_tools:
        tags = [tag.lower() for tag in t.get("tags", [])]
        if name_lower in tags:
            return t

    return None


def _tool_category(tool: dict[str, Any]) -> str:
    """Get normalized category for a tool."""
    cat = tool.get("category", "other")
    # Map internal categories to the user-facing list
    cat_map = {
        "ai": "ai-agents",
        "data": "data-analytics",
        "developer_tools": "developer-tools",
        "blockchain": "blockchain",
        "communication": "communication",
        "productivity": "developer-tools",
        "payments": "general",
        "mcp": "developer-tools",
        "other": "general",
    }
    return cat_map.get(cat, cat)


def _rank_in_category(tool: dict[str, Any], category: str, all_tools: list[dict[str, Any]]) -> int:
    """Get rank of tool within its category (1-based)."""
    same_cat = [
        t for t in all_tools
        if _tool_category(t) == category
    ]
    same_cat.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)
    for i, t in enumerate(same_cat):
        if t.get("scan_id") == tool.get("scan_id"):
            return i + 1
    return 0


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    tools: list[str] = Field(..., min_length=1, max_length=50, description="List of tool names")
    setup_id: str | None = Field(None, description="Custom setup ID (auto-generated if omitted)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_setup(req: RegisterRequest, response: Response):
    """Register a user's tool setup and get AEO scores for each tool.

    Accepts a list of tool names (MCP servers, CLIs, Skills, APIs) and
    returns each tool's Clarvia score, category, and rank within that category.
    """
    all_tools = _get_all_tools()

    # Generate setup_id
    if req.setup_id:
        setup_id = req.setup_id
    else:
        raw = ",".join(sorted(t.lower().strip() for t in req.tools))
        setup_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    resolved_tools: list[dict[str, Any]] = []
    for name in req.tools:
        matched = _find_tool(name, all_tools)
        if matched:
            cat = _tool_category(matched)
            rank = _rank_in_category(matched, cat, all_tools)
            resolved_tools.append({
                "name": matched.get("service_name", name),
                "input_name": name,
                "score": matched.get("clarvia_score", 0),
                "category": cat,
                "rank_in_category": rank,
                "scan_id": matched.get("scan_id"),
            })
        else:
            resolved_tools.append({
                "name": name,
                "input_name": name,
                "score": None,
                "category": "unknown",
                "rank_in_category": None,
                "scan_id": None,
            })

    # Persist setup
    setups = _load_setups()
    setups[setup_id] = {
        "tools": resolved_tools,
        "raw_tools": req.tools,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_setups(setups)

    avg_score = 0
    scored = [t for t in resolved_tools if t["score"] is not None]
    if scored:
        avg_score = round(sum(t["score"] for t in scored) / len(scored), 1)

    return {
        "setup_id": setup_id,
        "tools": resolved_tools,
        "summary": {
            "total": len(resolved_tools),
            "matched": len(scored),
            "unmatched": len(resolved_tools) - len(scored),
            "avg_score": avg_score,
        },
    }


@router.get("/{setup_id}/compare")
async def compare_setup(setup_id: str, response: Response):
    """Compare each tool in a registered setup against higher-scored alternatives.

    For each tool, shows better alternatives in the same category and the
    category average score.
    """
    setups = _load_setups()
    setup = setups.get(setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found. Register first via POST /v1/setup/register.")

    all_tools = _get_all_tools()

    comparisons: list[dict[str, Any]] = []
    for tool_entry in setup["tools"]:
        scan_id = tool_entry.get("scan_id")
        cat = tool_entry.get("category", "general")
        score = tool_entry.get("score")

        if score is None:
            comparisons.append({
                "current": {"name": tool_entry["name"], "score": None, "status": "not_found"},
                "better_alternatives": [],
                "category": cat,
                "category_avg": None,
            })
            continue

        # Find same-category tools with higher scores
        same_cat = [
            t for t in all_tools
            if _tool_category(t) == cat and t.get("scan_id") != scan_id
        ]
        same_cat.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)

        better = [
            {
                "name": t.get("service_name", ""),
                "score": t.get("clarvia_score", 0),
                "scan_id": t.get("scan_id"),
            }
            for t in same_cat
            if t.get("clarvia_score", 0) > score
        ][:5]  # Top 5 alternatives

        # Category average
        all_cat_scores = [t.get("clarvia_score", 0) for t in same_cat]
        all_cat_scores.append(score)
        cat_avg = round(sum(all_cat_scores) / len(all_cat_scores), 1) if all_cat_scores else 0

        comparisons.append({
            "current": {
                "name": tool_entry["name"],
                "score": score,
                "rank": tool_entry.get("rank_in_category"),
            },
            "better_alternatives": better,
            "category": cat,
            "category_avg": cat_avg,
            "upgrade_potential": len(better) > 0,
        })

    total_upgradable = sum(1 for c in comparisons if c.get("upgrade_potential"))
    return {
        "setup_id": setup_id,
        "comparisons": comparisons,
        "summary": {
            "total_tools": len(comparisons),
            "upgradable": total_upgradable,
        },
    }


@router.get("/{setup_id}/recommend")
async def recommend_for_setup(setup_id: str, response: Response, limit: int = 10):
    """Recommend new tools based on a registered setup.

    Suggests popular tools in the same categories that the user doesn't
    already have. Uses a "users with X also use Y" heuristic based on
    category co-occurrence.
    """
    setups = _load_setups()
    setup = setups.get(setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found. Register first via POST /v1/setup/register.")

    all_tools = _get_all_tools()

    # Gather user's current categories and tool scan_ids
    user_scan_ids = {t.get("scan_id") for t in setup["tools"] if t.get("scan_id")}
    user_categories = {t.get("category") for t in setup["tools"] if t.get("category") and t["category"] != "unknown"}

    # Strategy 1: High-scoring tools in user's categories that they don't have
    category_recs: list[dict[str, Any]] = []
    for cat in user_categories:
        same_cat = [
            t for t in all_tools
            if _tool_category(t) == cat and t.get("scan_id") not in user_scan_ids
        ]
        same_cat.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)

        # Find which user tool is in this category for the "complements" reason
        user_tools_in_cat = [
            t["name"] for t in setup["tools"]
            if t.get("category") == cat
        ]
        complement_ref = user_tools_in_cat[0] if user_tools_in_cat else "your tools"

        for t in same_cat[:3]:
            category_recs.append({
                "name": t.get("service_name", ""),
                "score": t.get("clarvia_score", 0),
                "category": cat,
                "scan_id": t.get("scan_id"),
                "reason": f"Popular in {cat}, complements {complement_ref}",
            })

    # Strategy 2: Adjacent categories — categories user doesn't have
    adjacent_cats = {
        "data-analytics": ["database", "ai-agents"],
        "developer-tools": ["ai-agents", "security"],
        "ai-agents": ["data-analytics", "developer-tools"],
        "blockchain": ["data-analytics", "security"],
        "communication": ["developer-tools"],
        "database": ["data-analytics"],
        "search": ["ai-agents", "data-analytics"],
        "design": ["developer-tools"],
        "security": ["developer-tools"],
    }
    adjacent_recs: list[dict[str, Any]] = []
    for cat in user_categories:
        for adj_cat in adjacent_cats.get(cat, []):
            if adj_cat in user_categories:
                continue
            adj_tools = [
                t for t in all_tools
                if _tool_category(t) == adj_cat and t.get("scan_id") not in user_scan_ids
            ]
            adj_tools.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)
            for t in adj_tools[:2]:
                adjacent_recs.append({
                    "name": t.get("service_name", ""),
                    "score": t.get("clarvia_score", 0),
                    "category": adj_cat,
                    "scan_id": t.get("scan_id"),
                    "reason": f"Commonly paired with {cat} tools",
                })

    # Merge and deduplicate
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for rec in category_recs + adjacent_recs:
        sid = rec.get("scan_id", rec["name"])
        if sid not in seen:
            seen.add(sid)
            merged.append(rec)

    # Sort by score descending
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)
    recommendations = merged[:limit]

    return {
        "setup_id": setup_id,
        "recommendations": recommendations,
        "based_on_categories": list(user_categories),
    }
