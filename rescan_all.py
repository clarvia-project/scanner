#!/usr/bin/env python3
"""Rescan all services from prebuilt-scans.json using the local backend.

Usage:
    python3 rescan_all.py [--port 8003] [--delay 2]
"""

import argparse
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent

# All 3 output locations
OUTPUT_PATHS = [
    BASE_DIR / "data" / "prebuilt-scans.json",
    BASE_DIR / "frontend" / "public" / "data" / "prebuilt-scans.json",
    BASE_DIR / "backend" / "data" / "prebuilt-scans.json",
]

# Full list of 48+ services to scan
ALL_SERVICES = [
    ("OpenAI", "https://openai.com"),
    ("Anthropic", "https://anthropic.com"),
    ("Google AI", "https://ai.google.dev"),
    ("Mistral", "https://mistral.ai"),
    ("Cohere", "https://cohere.com"),
    ("Replicate", "https://replicate.com"),
    ("Hugging Face", "https://huggingface.co"),
    ("Together AI", "https://together.ai"),
    ("Groq", "https://groq.com"),
    ("Perplexity", "https://perplexity.ai"),
    ("GitHub", "https://github.com"),
    ("GitLab", "https://gitlab.com"),
    ("Vercel", "https://vercel.com"),
    ("Netlify", "https://netlify.com"),
    ("Supabase", "https://supabase.com"),
    ("Firebase", "https://firebase.google.com"),
    ("AWS", "https://aws.amazon.com"),
    ("Cloudflare", "https://cloudflare.com"),
    ("Railway", "https://railway.app"),
    ("Stripe", "https://stripe.com"),
    ("PayPal", "https://paypal.com"),
    ("Square", "https://squareup.com"),
    ("Plaid", "https://plaid.com"),
    ("Coinbase", "https://coinbase.com"),
    ("Circle", "https://circle.com"),
    ("Slack", "https://slack.com"),
    ("Discord", "https://discord.com"),
    ("Twilio", "https://twilio.com"),
    ("SendGrid", "https://sendgrid.com"),
    ("Resend", "https://resend.com"),
    ("Snowflake", "https://snowflake.com"),
    ("Databricks", "https://databricks.com"),
    ("Amplitude", "https://amplitude.com"),
    ("Segment", "https://segment.com"),
    ("Linear", "https://linear.app"),
    ("Jira", "https://atlassian.com/software/jira"),
    ("Asana", "https://asana.com"),
    ("Figma", "https://figma.com"),
    ("Solana", "https://solana.com"),
    ("Ethereum", "https://ethereum.org"),
    ("Helius", "https://helius.dev"),
    ("Alchemy", "https://alchemy.com"),
    ("Moralis", "https://moralis.io"),
    ("Dune", "https://dune.com"),
    ("Notion", "https://notion.so"),
    ("Canva", "https://canva.com"),
    ("Render", "https://render.com"),
    ("Mixpanel", "https://mixpanel.com"),
]


def save_results(results: list[dict]) -> None:
    """Save results to all 3 output paths."""
    sorted_results = sorted(
        results, key=lambda x: (x.get("clarvia_score") or 0), reverse=True
    )
    content = json.dumps(sorted_results, indent=2, ensure_ascii=False)
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Rescan all services")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    api_url = f"http://localhost:{args.port}/api/scan"

    # Health check
    try:
        resp = requests.get(f"http://localhost:{args.port}/health", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Backend not reachable on port {args.port}: {e}")
        return

    results: list[dict] = []
    total = len(ALL_SERVICES)
    failed = 0
    start_time = time.monotonic()

    for i, (name, url) in enumerate(ALL_SERVICES, 1):
        print(f"[{i}/{total}] Scanning {name} ({url})...", end=" ", flush=True)
        try:
            resp = requests.post(api_url, json={"url": url}, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "url": url,
                    "service_name": name,
                    "clarvia_score": data.get("clarvia_score"),
                    "rating": data.get("rating"),
                    "dimensions": data.get("dimensions"),
                    "onchain_bonus": data.get("onchain_bonus"),
                    "scan_id": data.get("scan_id"),
                    "top_recommendations": data.get("top_recommendations"),
                    "scan_duration_ms": data.get("scan_duration_ms"),
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                }
                results.append(result)
                print(
                    f"Score: {data.get('clarvia_score')} ({data.get('rating')}) "
                    f"[{data.get('scan_duration_ms', 0)}ms]"
                )
            else:
                failed += 1
                print(f"FAILED (HTTP {resp.status_code})")
        except Exception as e:
            failed += 1
            print(f"ERROR: {type(e).__name__}: {e}")

        # Save progress after each scan
        save_results(results)

        if i < total:
            time.sleep(args.delay)

    elapsed = time.monotonic() - start_time
    print(f"\nDone! {len(results)}/{total} scanned, {failed} failed, {elapsed:.0f}s total")
    print(f"Results saved to {len(OUTPUT_PATHS)} locations")


if __name__ == "__main__":
    main()
