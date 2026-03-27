#!/usr/bin/env python3
"""Test scorer distribution against real data.

Loads actual tool data and scores 20 tools of each type,
printing distribution stats and sample breakdowns.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scoring import score_tool
from app.scoring.mcp_scorer import score_mcp_server
from app.scoring.api_scorer import score_api
from app.scoring.cli_scorer import score_cli_tool
from app.scoring.connector_scorer import score_connector
from app.scoring.skill_scorer import score_skill

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

SAMPLE_SIZE = 20


def load_json(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def distribution_stats(scores: list[int]) -> dict[str, Any]:
    if not scores:
        return {"count": 0}
    scores_sorted = sorted(scores)
    n = len(scores_sorted)
    return {
        "count": n,
        "min": scores_sorted[0],
        "max": scores_sorted[-1],
        "mean": round(sum(scores_sorted) / n, 1),
        "median": scores_sorted[n // 2],
        "p25": scores_sorted[n // 4],
        "p75": scores_sorted[3 * n // 4],
        "low": sum(1 for s in scores_sorted if s < 25),
        "basic": sum(1 for s in scores_sorted if 25 <= s < 45),
        "moderate": sum(1 for s in scores_sorted if 45 <= s < 70),
        "strong": sum(1 for s in scores_sorted if s >= 70),
    }


def print_stats(label: str, scores: list[int]) -> None:
    stats = distribution_stats(scores)
    if stats["count"] == 0:
        print(f"\n{'=' * 60}")
        print(f"  {label}: NO DATA")
        return

    print(f"\n{'=' * 60}")
    print(f"  {label} ({stats['count']} tools)")
    print(f"{'=' * 60}")
    print(f"  Range:   {stats['min']} - {stats['max']}")
    print(f"  Mean:    {stats['mean']}")
    print(f"  Median:  {stats['median']}")
    print(f"  P25/P75: {stats['p25']} / {stats['p75']}")
    print("  Rating distribution:")
    print(f"    Low (<25):      {stats['low']:3d} ({100 * stats['low'] // stats['count']:2d}%)")
    print(f"    Basic (25-44):  {stats['basic']:3d} ({100 * stats['basic'] // stats['count']:2d}%)")
    print(f"    Moderate (45-69): {stats['moderate']:3d} ({100 * stats['moderate'] // stats['count']:2d}%)")
    print(f"    Strong (70+):   {stats['strong']:3d} ({100 * stats['strong'] // stats['count']:2d}%)")


def print_sample_breakdown(name: str, result: dict) -> None:
    dims = result.get("dimensions", {})
    dim_parts = []
    for dim_name, dim_data in dims.items():
        s = dim_data.get("score", 0)
        m = dim_data.get("max", 25)
        dim_parts.append(f"{dim_name[:12]:12s}={s:2d}/{m}")
    dim_str = "  ".join(dim_parts)
    print(f"  {name[:35]:35s} | {result['clarvia_score']:3d} {result['rating']:8s} | {dim_str}")


def test_mcp_servers(full: bool = False) -> list[int]:
    path = DATA_DIR / "mcp-registry-all.json"
    if not path.exists():
        print(f"  [SKIP] {path} not found")
        return []

    data = load_json(path)
    sample = random.sample(data, min(SAMPLE_SIZE, len(data)))
    if full:
        sample = data

    scores = []
    print("\n  Sample breakdowns (MCP):")
    for entry in sample[:SAMPLE_SIZE]:
        result = score_mcp_server(entry)
        scores.append(result["clarvia_score"])
        name = entry.get("server", {}).get("name", "?")
        if len(scores) <= 5:  # Show first 5 detailed
            print_sample_breakdown(name, result)

    if full:
        for entry in data[SAMPLE_SIZE:]:
            result = score_mcp_server(entry)
            scores.append(result["clarvia_score"])

    return scores


def test_apis(full: bool = False) -> list[int]:
    path = DATA_DIR / "all-agent-tools.json"
    if not path.exists():
        print(f"  [SKIP] {path} not found")
        return []

    data = load_json(path)
    api_tools = [t for t in data if t.get("type") == "api"]
    sample = random.sample(api_tools, min(SAMPLE_SIZE, len(api_tools)))
    if full:
        sample = api_tools

    scores = []
    print("\n  Sample breakdowns (API):")
    for tool in sample[:SAMPLE_SIZE]:
        result = score_api(tool)
        scores.append(result["clarvia_score"])
        name = tool.get("name", "?")
        if len(scores) <= 5:
            print_sample_breakdown(name, result)

    if full:
        for tool in api_tools[SAMPLE_SIZE:]:
            result = score_api(tool)
            scores.append(result["clarvia_score"])

    return scores


def test_connectors(full: bool = False) -> list[int]:
    path = DATA_DIR / "all-agent-tools.json"
    if not path.exists():
        return []

    data = load_json(path)
    conn_tools = [t for t in data if t.get("type") == "connector"]
    sample = random.sample(conn_tools, min(SAMPLE_SIZE, len(conn_tools)))
    if full:
        sample = conn_tools

    scores = []
    print("\n  Sample breakdowns (Connector):")
    for tool in sample[:SAMPLE_SIZE]:
        result = score_connector(tool)
        scores.append(result["clarvia_score"])
        name = tool.get("name", "?")
        if len(scores) <= 5:
            print_sample_breakdown(name, result)

    if full:
        for tool in conn_tools[SAMPLE_SIZE:]:
            result = score_connector(tool)
            scores.append(result["clarvia_score"])

    return scores


def test_cli_tools(full: bool = False) -> list[int]:
    path = DATA_DIR / "skills-cli-collected.json"
    if not path.exists():
        print(f"  [SKIP] {path} not found")
        return []

    data = load_json(path)
    cli_tools = [t for t in data if t.get("type") == "cli_tool"]
    sample = random.sample(cli_tools, min(SAMPLE_SIZE, len(cli_tools)))
    if full:
        sample = cli_tools

    scores = []
    print("\n  Sample breakdowns (CLI):")
    for tool in sample[:SAMPLE_SIZE]:
        result = score_cli_tool(tool)
        scores.append(result["clarvia_score"])
        name = tool.get("name", "?")
        if len(scores) <= 5:
            print_sample_breakdown(name, result)

    if full:
        for tool in cli_tools[SAMPLE_SIZE:]:
            result = score_cli_tool(tool)
            scores.append(result["clarvia_score"])

    return scores


def test_skills(full: bool = False) -> list[int]:
    path = DATA_DIR / "skills-cli-collected.json"
    if not path.exists():
        return []

    data = load_json(path)
    skills = [t for t in data if t.get("type") == "skill"]
    sample = random.sample(skills, min(SAMPLE_SIZE, len(skills)))
    if full:
        sample = skills

    scores = []
    print("\n  Sample breakdowns (Skill):")
    for tool in sample[:SAMPLE_SIZE]:
        result = score_skill(tool)
        scores.append(result["clarvia_score"])
        name = tool.get("name", "?")
        if len(scores) <= 5:
            print_sample_breakdown(name, result)

    if full:
        for tool in skills[SAMPLE_SIZE:]:
            result = score_skill(tool)
            scores.append(result["clarvia_score"])

    return scores


def test_unified_router() -> None:
    """Test that the unified score_tool() routes correctly."""
    print(f"\n{'=' * 60}")
    print("  Unified Router Test")
    print(f"{'=' * 60}")

    # Load one of each type
    test_cases = []

    mcp_path = DATA_DIR / "mcp-registry-all.json"
    if mcp_path.exists():
        mcp_data = load_json(mcp_path)
        if mcp_data:
            test_cases.append(("MCP", mcp_data[0]))

    tools_path = DATA_DIR / "all-agent-tools.json"
    if tools_path.exists():
        all_tools = load_json(tools_path)
        apis = [t for t in all_tools if t.get("type") == "api"]
        conns = [t for t in all_tools if t.get("type") == "connector"]
        if apis:
            test_cases.append(("API", apis[0]))
        if conns:
            test_cases.append(("Connector", conns[0]))

    skills_path = DATA_DIR / "skills-cli-collected.json"
    if skills_path.exists():
        skill_data = load_json(skills_path)
        clis = [t for t in skill_data if t.get("type") == "cli_tool"]
        skills = [t for t in skill_data if t.get("type") == "skill"]
        if clis:
            test_cases.append(("CLI", clis[0]))
        if skills:
            test_cases.append(("Skill", skills[0]))

    for label, tool in test_cases:
        result = score_tool(tool)
        detected = result.get("tool_type", "?")
        name = tool.get("name") or tool.get("server", {}).get("name", "?")
        expected_map = {"MCP": "mcp_server", "API": "api", "Connector": "connector", "CLI": "cli_tool", "Skill": "skill"}
        expected = expected_map.get(label, label.lower())
        status = "OK" if detected == expected or (label == "Connector" and detected in ("api", "connector")) else "MISMATCH"
        print(f"  [{status}] {label:12s} -> detected={detected:12s} | {name[:30]:30s} | score={result['clarvia_score']}")


def main() -> None:
    full = "--full" in sys.argv
    random.seed(42)  # Reproducible samples

    print("=" * 60)
    print("  Clarvia Scorer Distribution Test")
    print("  Mode:", "FULL (all data)" if full else f"SAMPLE ({SAMPLE_SIZE} per type)")
    print("=" * 60)

    mcp_scores = test_mcp_servers(full)
    print_stats("MCP Servers", mcp_scores)

    api_scores = test_apis(full)
    print_stats("APIs (apis_guru)", api_scores)

    conn_scores = test_connectors(full)
    print_stats("Connectors (n8n)", conn_scores)

    cli_scores = test_cli_tools(full)
    print_stats("CLI Tools", cli_scores)

    skill_scores = test_skills(full)
    print_stats("Skills", skill_scores)

    test_unified_router()

    # Cross-type comparison
    all_types = {
        "MCP": mcp_scores,
        "API": api_scores,
        "Connector": conn_scores,
        "CLI": cli_scores,
        "Skill": skill_scores,
    }

    print(f"\n{'=' * 60}")
    print("  Cross-Type Mean Comparison")
    print(f"{'=' * 60}")
    for name, scores in all_types.items():
        if scores:
            mean = sum(scores) / len(scores)
            print(f"  {name:12s}: mean={mean:5.1f} | n={len(scores)}")

    print("\n  Target: means within 35-55 range for fair cross-type ranking.")
    print("  Strong should be rare (<15%), Low should be uncommon (<10%).")
    print()


if __name__ == "__main__":
    main()
