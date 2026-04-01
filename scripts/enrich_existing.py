#!/usr/bin/env python3
"""Enrich existing prebuilt-scans.json with pricing, capabilities, difficulty, popularity.

Reads the current data, applies enrichment functions from tool_scorer,
and writes back the enriched data.

Usage:
    python3 scripts/enrich_existing.py
    python3 scripts/enrich_existing.py --dry-run  # Preview without writing
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.tool_scorer import detect_pricing, extract_capabilities, detect_difficulty, estimate_popularity
from app.scoring import score_tool, detect_source, compute_confidence


def _to_raw_tool(service: dict) -> dict:
    """Convert normalized service record back to raw tool format for scorer functions.

    The scorer functions (detect_pricing, extract_capabilities, etc.) expect
    raw tool dicts with keys like 'name', 'description', 'repository', 'server'.
    Prebuilt-scans.json uses 'service_name', 'service_type', 'type_config', etc.
    """
    raw = {
        "name": service.get("service_name", ""),
        "description": service.get("description", ""),
        "source": service.get("source", "unknown"),
        "type": service.get("service_type", "general"),
        "keywords": service.get("tags", []),
        "homepage": service.get("url", ""),
    }

    # Reconstruct repository from url or cross_refs
    cross_refs = service.get("cross_refs") or {}
    if cross_refs.get("github"):
        raw["repository"] = {"url": cross_refs["github"]}
    elif service.get("url", "").startswith("https://github.com"):
        raw["repository"] = {"url": service["url"]}

    # Reconstruct npm_url from cross_refs
    if cross_refs.get("npm"):
        raw["npm_url"] = cross_refs["npm"]

    # Reconstruct server dict for MCP servers
    if service.get("service_type") == "mcp_server":
        type_config = service.get("type_config") or {}
        raw["server"] = {
            "name": service.get("service_name", ""),
            "description": service.get("description", ""),
            "tools": type_config.get("tools", []),
            "websiteUrl": type_config.get("endpoint_url", ""),
        }
        if type_config.get("npm_package"):
            raw["server"]["packages"] = [{"name": type_config["npm_package"]}]
            raw["install_command"] = f"npm install {type_config['npm_package']}"

    # Reconstruct install_command for CLI tools
    if service.get("service_type") == "cli_tool":
        type_config = service.get("type_config") or {}
        if type_config.get("install_command"):
            raw["install_command"] = type_config["install_command"]

    # Reconstruct openapi_url for APIs
    if service.get("service_type") == "api":
        type_config = service.get("type_config") or {}
        if type_config.get("openapi_url"):
            raw["openapi_url"] = type_config["openapi_url"]

    return raw


def enrich_service(service: dict) -> dict:
    """Add enrichment fields to a service record."""
    raw = _to_raw_tool(service)

    # Pricing (if missing or unknown)
    if not service.get("pricing") or service.get("pricing") == "unknown":
        service["pricing"] = detect_pricing(raw)

    # Capabilities (if missing or empty)
    if not service.get("capabilities"):
        service["capabilities"] = extract_capabilities(raw)

    # Difficulty (if missing)
    if not service.get("difficulty") or service.get("difficulty") == "unknown":
        service["difficulty"] = detect_difficulty(raw)

    # Popularity (if missing or 0)
    if not service.get("popularity"):
        service["popularity"] = estimate_popularity(raw)

    # Source (if missing or unknown)
    if not service.get("source") or service.get("source") == "unknown":
        service["source"] = detect_source(raw)

    # Scoring confidence (if missing)
    if not service.get("scoring_confidence"):
        service["scoring_confidence"] = compute_confidence(raw)

    return service


def main():
    dry_run = "--dry-run" in sys.argv

    data_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    input_file = data_dir / "prebuilt-scans.json"

    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        sys.exit(1)

    print(f"Loading {input_file}...")
    with open(input_file) as f:
        services = json.load(f)

    print(f"Loaded {len(services)} services")

    # Stats tracking
    stats = {
        "pricing_enriched": 0,
        "capabilities_enriched": 0,
        "difficulty_enriched": 0,
        "popularity_enriched": 0,
        "source_enriched": 0,
        "confidence_enriched": 0,
    }

    for i, svc in enumerate(services):
        old_pricing = svc.get("pricing")
        old_caps = svc.get("capabilities")
        old_diff = svc.get("difficulty")
        old_pop = svc.get("popularity")
        old_src = svc.get("source")
        old_conf = svc.get("scoring_confidence")

        enrich_service(svc)

        if svc.get("pricing") != old_pricing:
            stats["pricing_enriched"] += 1
        if svc.get("capabilities") != old_caps:
            stats["capabilities_enriched"] += 1
        if svc.get("difficulty") != old_diff:
            stats["difficulty_enriched"] += 1
        if svc.get("popularity") != old_pop:
            stats["popularity_enriched"] += 1
        if svc.get("source") != old_src:
            stats["source_enriched"] += 1
        if svc.get("scoring_confidence") != old_conf:
            stats["confidence_enriched"] += 1

        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{len(services)}...")

    print(f"\nEnrichment stats:")
    for key, count in stats.items():
        print(f"  {key}: {count}/{len(services)} ({count/len(services)*100:.1f}%)")

    if dry_run:
        print("\n[DRY RUN] No files written.")
        # Show samples across different service types
        shown_types = set()
        for svc in services:
            st = svc.get("service_type", "unknown")
            if st not in shown_types:
                shown_types.add(st)
                print(f"\nSample ({st}): {svc.get('service_name', '?')}")
                for field in ["pricing", "capabilities", "difficulty", "popularity", "source", "scoring_confidence"]:
                    print(f"  {field}: {svc.get(field)}")
            if len(shown_types) >= 5:
                break
        return

    # Write back
    output_file = input_file  # Overwrite in place
    print(f"\nWriting to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(services, f, separators=(",", ":"), ensure_ascii=False)

    print(f"Done! Enriched {len(services)} services.")


if __name__ == "__main__":
    main()
