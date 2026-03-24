"""Convert Clarvia scan results to SARIF 2.1.0 format."""

from typing import Any

from .models import ScanResponse


def _severity_level(score: int, max_score: int) -> str:
    """Map dimension score to SARIF severity.

    score < 10  -> error   (critical gap)
    score < 18  -> warning (needs work)
    score >= 18 -> note    (minor or acceptable)
    """
    if score < 10:
        return "error"
    elif score < 18:
        return "warning"
    return "note"


def _make_rule(rule_id: str, name: str, description: str, score: int, max_score: int) -> dict[str, Any]:
    """Build a SARIF rule entry for a dimension."""
    return {
        "id": rule_id,
        "name": name,
        "shortDescription": {"text": description},
        "properties": {
            "score": score,
            "maxScore": max_score,
            "percentage": round(score / max_score * 100, 1) if max_score > 0 else 0,
        },
    }


def _make_result(
    rule_id: str,
    message: str,
    level: str,
    score: int,
    max_score: int,
) -> dict[str, Any]:
    """Build a SARIF result entry."""
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "properties": {
            "score": score,
            "maxScore": max_score,
        },
    }


_DIMENSION_META: dict[str, tuple[str, str]] = {
    "api_accessibility": (
        "API Accessibility",
        "Measures how easily AI agents can reach and use the API "
        "(endpoint existence, speed, rate limits, auth docs, versioning, SDKs, free tier).",
    ),
    "data_structuring": (
        "Data Structuring",
        "Evaluates structured data quality "
        "(schema definition, JSON responses, error structure, webhooks, batch API, content negotiation).",
    ),
    "agent_compatibility": (
        "Agent Compatibility",
        "Checks agent-specific integration readiness "
        "(MCP server, robot policy, discovery, idempotency, pagination, streaming).",
    ),
    "trust_signals": (
        "Trust Signals",
        "Assesses reliability and trustworthiness signals "
        "(uptime, consistency, TLS, error quality, deprecation policy, changelog, contact info).",
    ),
}


def scan_to_sarif(scan: ScanResponse) -> dict[str, Any]:
    """Convert a ScanResponse to a SARIF 2.1.0 document."""
    rules: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    # Dimension-level rules and results
    for dim_key, dim in scan.dimensions.items():
        meta = _DIMENSION_META.get(dim_key, (dim_key, ""))
        rule_id = f"clarvia/{dim_key}"

        rules.append(_make_rule(
            rule_id=rule_id,
            name=meta[0],
            description=meta[1],
            score=dim.score,
            max_score=dim.max,
        ))

        level = _severity_level(dim.score, dim.max)
        results.append(_make_result(
            rule_id=rule_id,
            message=f"{meta[0]}: {dim.score}/{dim.max}",
            level=level,
            score=dim.score,
            max_score=dim.max,
        ))

        # Sub-factor results
        for sf_key, sf in dim.sub_factors.items():
            sf_rule_id = f"clarvia/{dim_key}/{sf_key}"
            rules.append(_make_rule(
                rule_id=sf_rule_id,
                name=sf.label,
                description=f"Sub-factor of {meta[0]}",
                score=sf.score,
                max_score=sf.max,
            ))
            sf_level = _severity_level(
                # Scale sub-factor score to 25-point equivalent for severity
                int(sf.score / sf.max * 25) if sf.max > 0 else 0,
                25,
            )
            results.append(_make_result(
                rule_id=sf_rule_id,
                message=f"{sf.label}: {sf.score}/{sf.max}",
                level=sf_level,
                score=sf.score,
                max_score=sf.max,
            ))

    # Recommendations as results
    for i, rec in enumerate(scan.top_recommendations, start=1):
        rec_rule_id = f"clarvia/recommendation/{i}"
        rules.append({
            "id": rec_rule_id,
            "name": f"Recommendation {i}",
            "shortDescription": {"text": "Improvement recommendation from Clarvia AEO scan"},
        })
        results.append({
            "ruleId": rec_rule_id,
            "level": "warning",
            "message": {"text": rec},
        })

    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Clarvia AEO Scanner",
                        "version": "1.0.0",
                        "informationUri": "https://clarvia.art",
                        "rules": rules,
                    },
                },
                "results": results,
                "properties": {
                    "scanId": scan.scan_id,
                    "url": scan.url,
                    "serviceName": scan.service_name,
                    "clarviaScore": scan.clarvia_score,
                    "rating": scan.rating,
                    "scannedAt": scan.scanned_at.isoformat(),
                    "scanDurationMs": scan.scan_duration_ms,
                    "authenticatedScan": scan.authenticated_scan,
                },
            },
        ],
    }

    return sarif
