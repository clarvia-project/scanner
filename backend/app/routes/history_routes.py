"""History API — score snapshots and trend data."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/v1", tags=["history"])
logger = logging.getLogger(__name__)

_snapshots: list[dict] = []

def _snapshots_path() -> Path:
    candidates = [Path("/app/data/snapshots.json")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data" / "snapshots.json")
        except IndexError:
            break
    for p in candidates:
        if p.parent.exists():
            return p
    return candidates[0]

def load_snapshots():
    global _snapshots
    p = _snapshots_path()
    if p.exists():
        with open(p) as f:
            _snapshots = json.load(f)

def save_snapshot(stats: dict):
    """Save a daily snapshot of platform stats."""
    snapshot = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_tools": stats.get("total_services", 0),
        "avg_score": stats.get("avg_score", 0),
        "score_distribution": stats.get("score_distribution", {}),
        "by_category": {k: v.get("count", 0) for k, v in stats.get("by_category", {}).items()},
    }
    # Prevent duplicate date entries
    _snapshots[:] = [s for s in _snapshots if s["date"] != snapshot["date"]]
    _snapshots.append(snapshot)
    # Keep max 365 days
    if len(_snapshots) > 365:
        _snapshots[:] = _snapshots[-365:]
    p = _snapshots_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(_snapshots, f, indent=2)

@router.get("/history")
async def get_history(days: int = Query(30, ge=1, le=365)):
    """Get historical platform statistics (daily snapshots)."""
    load_snapshots()
    return {"snapshots": _snapshots[-days:], "total_days": len(_snapshots)}

@router.get("/history/{scan_id}")
async def get_tool_history(scan_id: str):
    """Get score history for a specific tool (placeholder for future implementation)."""
    return {
        "scan_id": scan_id,
        "history": [],
        "message": "Per-tool history tracking starts from today. Check back in a few days."
    }
