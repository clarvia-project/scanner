"""Collection API — user-created curated tool lists."""

import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1", tags=["collections"])
logger = logging.getLogger(__name__)

_collections: dict[str, dict] = {}


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    tool_ids: list[str] = Field(default_factory=list, description="List of scan_ids")
    is_public: bool = True


@router.post("/collections")
async def create_collection(req: CollectionCreate):
    """Create a new curated tool collection."""
    cid = "col_" + "".join(
        secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12)
    )
    now = datetime.now(timezone.utc).isoformat()
    col = {
        "collection_id": cid,
        "name": req.name,
        "description": req.description,
        "tool_ids": req.tool_ids[:50],
        "is_public": req.is_public,
        "created_at": now,
        "updated_at": now,
        "views": 0,
    }
    _collections[cid] = col
    return col


@router.get("/collections")
async def list_collections(limit: int = Query(20, ge=1, le=100)):
    """List public curated tool collections."""
    public = [c for c in _collections.values() if c.get("is_public")]
    return {
        "collections": sorted(
            public, key=lambda c: c["created_at"], reverse=True
        )[:limit],
        "total": len(public),
    }


@router.get("/collections/{collection_id}")
async def get_collection(collection_id: str):
    """Get a collection with resolved tool details."""
    col = _collections.get(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    col["views"] += 1

    # Resolve tool details
    from .index_routes import (
        _by_scan_id,
        _collected_tools,
        _compact_service,
        _ensure_loaded,
        _load_collected,
    )

    _ensure_loaded()
    _load_collected()
    tools: list[dict[str, Any]] = []
    for tid in col["tool_ids"]:
        svc = _by_scan_id.get(tid)
        if not svc:
            for t in _collected_tools:
                if t["scan_id"] == tid:
                    svc = t
                    break
        if svc:
            tools.append(_compact_service(svc))
    return {**col, "tools": tools}


@router.put("/collections/{collection_id}")
async def update_collection(collection_id: str, req: CollectionCreate):
    """Update an existing collection."""
    col = _collections.get(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    col.update(
        {
            "name": req.name,
            "description": req.description,
            "tool_ids": req.tool_ids[:50],
            "is_public": req.is_public,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return col


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str):
    """Delete a collection."""
    if collection_id not in _collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    del _collections[collection_id]
    return {"deleted": True}
