"""CLI entry point for the Clarvia AEO Scanner."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from . import __version__
from .scanner import ClarviaClient, ScanError, ScanResult


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _bar(score: int, max_score: int, width: int = 24) -> str:
    """Render a Unicode progress bar."""
    filled = round(score / max_score * width) if max_score > 0 else 0
    return "\u2588" * filled + "\u2591" * (width - filled)


def _rating_label(rating: str) -> str:
    labels = {
        "excellent": "Excellent",
        "strong": "Strong",
        "moderate": "Moderate",
        "weak": "Weak",
    }
    return labels.get(rating.lower(), rating.capitalize())


_DIMENSION_LABELS = {
    "api_accessibility": "API Accessibility",
    "data_structuring": "Data Structuring",
    "agent_compatibility": "Agent Compatibility",
    "trust_signals": "Trust Signals",
    "metadata_quality": "Metadata Quality",
}


def format_text(result: ScanResult, verbose: bool = False) -> str:
    """Format scan result as human-readable text."""
    lines = []
    lines.append(f"\U0001F989 Clarvia AEO Scanner v{__version__}")
    lines.append("")
    lines.append(f"Scanning: {result.url}")
    lines.append("\u2501" * 36)
    lines.append("")
    lines.append(
        f"Clarvia Score: {result.clarvia_score}/100 "
        f"({_rating_label(result.rating)})"
    )
    lines.append("")

    for key, dim in result.dimensions.items():
        label = _DIMENSION_LABELS.get(key, key.replace("_", " ").title())
        score = dim.get("score", 0)
        max_score = dim.get("max", 25)
        bar = _bar(score, max_score)
        lines.append(f"  {label + ':':<24}{score:>2}/{max_score} {bar}")

        if verbose and "sub_factors" in dim:
            for sf_key, sf in dim["sub_factors"].items():
                sf_label = sf.get("label", sf_key)
                sf_score = sf.get("score", 0)
                sf_max = sf.get("max", 0)
                lines.append(f"    - {sf_label}: {sf_score}/{sf_max}")

    # Onchain bonus (if applicable)
    ob = result.onchain_bonus
    if ob.get("applicable"):
        label = "Onchain Bonus:"
        score = ob.get("score", 0)
        max_score = ob.get("max", 25)
        bar = _bar(score, max_score)
        lines.append(f"  {label:<24}{score:>2}/{max_score} {bar}")

    lines.append("")

    if result.top_recommendations:
        lines.append("Top Recommendations:")
        for i, rec in enumerate(result.top_recommendations, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    lines.append(f"Badge: {result.raw.get('_badge_url', '')}")
    return "\n".join(lines)


def format_sarif(result: ScanResult) -> dict:
    """Format scan result as SARIF 2.1.0 JSON."""
    severity_map = {
        "excellent": "note",
        "strong": "note",
        "moderate": "warning",
        "weak": "error",
    }
    default_severity = severity_map.get(result.rating.lower(), "warning")

    rules = []
    results_list = []

    for i, rec in enumerate(result.top_recommendations):
        rule_id = f"clarvia/recommendation-{i + 1}"
        rules.append(
            {
                "id": rule_id,
                "shortDescription": {"text": rec},
                "helpUri": "https://clarvia.art",
                "properties": {"tags": ["aeo", "api-readiness"]},
            }
        )
        results_list.append(
            {
                "ruleId": rule_id,
                "level": default_severity,
                "message": {"text": rec},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": result.url},
                        }
                    }
                ],
                "properties": {
                    "clarvia_score": result.clarvia_score,
                    "rating": result.rating,
                },
            }
        )

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Clarvia AEO Scanner",
                        "version": __version__,
                        "informationUri": "https://clarvia.art",
                        "rules": rules,
                    }
                },
                "results": results_list,
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "properties": {
                            "url": result.url,
                            "clarvia_score": result.clarvia_score,
                            "rating": result.rating,
                            "scan_id": result.scan_id,
                            "dimensions": {
                                k: v.get("score", 0)
                                for k, v in result.dimensions.items()
                            },
                        },
                    }
                ],
            }
        ],
    }
    return sarif


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    """Execute a scan and print results."""
    auth = None
    if args.auth_header:
        parts = args.auth_header.split(":", 1)
        if len(parts) != 2:
            print("Error: --auth-header must be KEY:VALUE", file=sys.stderr)
            return 2
        auth = (parts[0].strip(), parts[1].strip())

    client = ClarviaClient(
        api_url=args.api_url,
        timeout=args.timeout,
        auth_header=auth,
    )

    try:
        result = client.scan(args.url)
    except ScanError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Attach badge URL to raw for text formatter
    result.raw["_badge_url"] = client.badge_url(result.service_name or args.url)

    if args.format == "json":
        output = json.dumps(result.raw, indent=2, default=str)
        print(output)
    elif args.format == "sarif":
        sarif = format_sarif(result)
        print(json.dumps(sarif, indent=2))
    else:
        print(format_text(result, verbose=args.verbose))

    # Check fail-under threshold
    if args.fail_under and result.clarvia_score < args.fail_under:
        print(
            f"\nFail: score {result.clarvia_score} is below threshold {args.fail_under}",
            file=sys.stderr,
        )
        return 1

    return 0


def cmd_badge(args: argparse.Namespace) -> int:
    """Print badge URL for a service."""
    client = ClarviaClient(api_url=args.api_url)
    url = client.badge_url(args.url)
    print(url)
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clarvia",
        description="Clarvia AEO Scanner CLI - Check API readiness for AI agents",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"clarvia-cli {__version__}",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # -- scan --
    scan_p = sub.add_parser("scan", help="Scan a URL for AEO readiness")
    scan_p.add_argument("url", help="URL to scan")
    scan_p.add_argument(
        "--api-url",
        default="https://clarvia.art",
        help="API base URL (default: https://clarvia.art)",
    )
    scan_p.add_argument(
        "--format",
        choices=["json", "text", "sarif"],
        default="text",
        help="Output format (default: text)",
    )
    scan_p.add_argument(
        "--fail-under",
        type=int,
        default=0,
        metavar="N",
        help="Exit with code 1 if score < N (for CI/CD)",
    )
    scan_p.add_argument(
        "--auth-header",
        metavar="KEY:VALUE",
        help="Add auth header to scan request",
    )
    scan_p.add_argument(
        "--timeout",
        type=int,
        default=60,
        metavar="N",
        help="Timeout in seconds (default: 60)",
    )
    scan_p.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed dimension sub-factor scores",
    )

    # -- badge --
    badge_p = sub.add_parser("badge", help="Get badge URL for a service")
    badge_p.add_argument("url", help="Service name, URL, or scan_id")
    badge_p.add_argument(
        "--api-url",
        default="https://clarvia.art",
        help="API base URL (default: https://clarvia.art)",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        sys.exit(cmd_scan(args))
    elif args.command == "badge":
        sys.exit(cmd_badge(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
