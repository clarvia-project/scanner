#!/usr/bin/env python3
"""Batch rescan script — scan all 48 services via localhost API and save results.

Usage:
    python scripts/batch_rescan.py [--api-url http://localhost:8002] [--concurrent 3]

Requires the backend server to be running. Results are saved to:
  - data/prebuilt-scans.json
  - backend/data/prebuilt-scans.json
  - frontend/public/data/prebuilt-scans.json
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import aiohttp

# All services to scan
SERVICES = [
    "https://helius.dev",
    "https://replicate.com",
    "https://cohere.com",
    "https://groq.com",
    "https://stripe.com",
    "https://github.com",
    "https://resend.com",
    "https://vercel.com",
    "https://netlify.com",
    "https://atlassian.com/software/jira",
    "https://dune.com",
    "https://supabase.com",
    "https://figma.com",
    "https://openai.com",
    "https://together.ai",
    "https://circle.com",
    "https://linear.app",
    "https://huggingface.co",
    "https://alchemy.com",
    "https://twilio.com",
    "https://segment.com",
    "https://gitlab.com",
    "https://slack.com",
    "https://databricks.com",
    "https://asana.com",
    "https://anthropic.com",
    "https://ai.google.dev",
    "https://aws.amazon.com",
    "https://cloudflare.com",
    "https://squareup.com",
    "https://plaid.com",
    "https://mistral.ai",
    "https://firebase.google.com",
    "https://solana.com",
    "https://discord.com",
    "https://sendgrid.com",
    "https://snowflake.com",
    "https://railway.app",
    "https://moralis.io",
    "https://amplitude.com",
    "https://paypal.com",
    "https://ethereum.org",
    "https://perplexity.ai",
    "https://canva.com",
    "https://notion.so",
    "https://mixpanel.com",
    "https://render.com",
    "https://coinbase.com",
]


async def scan_one(
    session: aiohttp.ClientSession,
    api_url: str,
    url: str,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Scan a single URL via the API."""
    async with semaphore:
        try:
            async with session.post(
                f"{api_url}/api/scan",
                json={"url": url},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    score = data.get("clarvia_score", "?")
                    print(f"  OK  {url} -> score={score}")
                    return data
                else:
                    text = await resp.text()
                    print(f"  ERR {url} -> {resp.status}: {text[:100]}")
                    return None
        except Exception as e:
            print(f"  ERR {url} -> {type(e).__name__}: {e}")
            return None


async def main(api_url: str, concurrent: int) -> None:
    start = time.monotonic()
    print(f"Batch rescan: {len(SERVICES)} services via {api_url}")
    print(f"Concurrency: {concurrent}")
    print()

    # Health check
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{api_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"ERROR: Server health check failed (status {resp.status})")
                    sys.exit(1)
        except Exception as e:
            print(f"ERROR: Cannot reach server at {api_url}: {e}")
            sys.exit(1)

    print("Server is healthy. Starting scans...\n")

    semaphore = asyncio.Semaphore(concurrent)
    results: list[dict] = []

    async with aiohttp.ClientSession() as session:
        tasks = [scan_one(session, api_url, url, semaphore) for url in SERVICES]
        scan_results = await asyncio.gather(*tasks)

        for result in scan_results:
            if result is not None:
                results.append(result)

    elapsed = time.monotonic() - start
    print(f"\nCompleted: {len(results)}/{len(SERVICES)} succeeded in {elapsed:.1f}s")

    if not results:
        print("No results to save.")
        sys.exit(1)

    # Sort by score descending
    results.sort(key=lambda r: r.get("clarvia_score", 0), reverse=True)

    # Save to all output paths
    project_root = Path(__file__).resolve().parent.parent
    output_paths = [
        project_root / "data" / "prebuilt-scans.json",
        project_root / "backend" / "data" / "prebuilt-scans.json",
        project_root / "frontend" / "public" / "data" / "prebuilt-scans.json",
    ]

    for path in output_paths:
        if path.parent.exists():
            with open(path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Saved to {path}")

    # Print summary
    scores = [r["clarvia_score"] for r in results]
    avg = sum(scores) / len(scores)
    print(f"\nSummary:")
    print(f"  Average score: {avg:.1f}")
    print(f"  Highest: {max(scores)} ({results[0]['service_name']})")
    print(f"  Lowest:  {min(scores)} ({results[-1]['service_name']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch rescan all services")
    parser.add_argument("--api-url", default="http://localhost:8002", help="Scanner API URL")
    parser.add_argument("--concurrent", type=int, default=3, help="Max concurrent scans")
    args = parser.parse_args()

    asyncio.run(main(args.api_url, args.concurrent))
