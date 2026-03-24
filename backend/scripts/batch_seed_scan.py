"""Batch seed scan — populate benchmark data by scanning popular services.

Usage:
    cd scanner/backend
    source .venv/bin/activate
    python scripts/batch_seed_scan.py
"""

import asyncio
import httpx
import time
import sys

API_BASE = "http://localhost:8000"

# 50 popular services across categories
SEED_SERVICES = [
    # Developer Tools / APIs
    "https://stripe.com",
    "https://github.com",
    "https://openai.com",
    "https://anthropic.com",
    "https://twilio.com",
    "https://sendgrid.com",
    "https://cloudflare.com",
    "https://vercel.com",
    "https://supabase.com",
    "https://firebase.google.com",
    # Cloud / Infrastructure
    "https://aws.amazon.com",
    "https://cloud.google.com",
    "https://azure.microsoft.com",
    "https://digitalocean.com",
    "https://heroku.com",
    # Crypto / Web3
    "https://etherscan.io",
    "https://coingecko.com",
    "https://coinmarketcap.com",
    "https://alchemy.com",
    "https://infura.io",
    "https://opensea.io",
    "https://uniswap.org",
    "https://aave.com",
    "https://chainlink.com",
    "https://thegraph.com",
    # SaaS / Productivity
    "https://notion.so",
    "https://slack.com",
    "https://linear.app",
    "https://figma.com",
    "https://airtable.com",
    "https://zapier.com",
    "https://hubspot.com",
    "https://intercom.com",
    "https://segment.com",
    "https://datadog.com",
    # E-commerce / Payments
    "https://shopify.com",
    "https://paypal.com",
    "https://square.com",
    "https://plaid.com",
    # AI / ML
    "https://huggingface.co",
    "https://replicate.com",
    "https://stability.ai",
    "https://cohere.com",
    "https://mistral.ai",
    # Communication
    "https://discord.com",
    "https://telegram.org",
    "https://zoom.us",
    # Data / Analytics
    "https://mixpanel.com",
    "https://amplitude.com",
    "https://snowflake.com",
    "https://elastic.co",
]


async def scan_one(client: httpx.AsyncClient, url: str, idx: int, total: int) -> dict:
    """Scan a single URL via the API."""
    try:
        resp = await client.post(
            f"{API_BASE}/api/scan",
            json={"url": url},
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            score = data.get("clarvia_score", "?")
            rating = data.get("rating", "?")
            print(f"  [{idx}/{total}] ✅ {url} → {score} ({rating})")
            return {"url": url, "score": score, "rating": rating, "ok": True}
        else:
            err = resp.text[:100]
            print(f"  [{idx}/{total}] ❌ {url} → HTTP {resp.status_code}: {err}")
            return {"url": url, "error": err, "ok": False}
    except Exception as e:
        print(f"  [{idx}/{total}] ❌ {url} → {str(e)[:100]}")
        return {"url": url, "error": str(e)[:100], "ok": False}


async def main():
    total = len(SEED_SERVICES)
    print(f"\n🦉 Clarvia Batch Seed Scan — {total} services")
    print("=" * 60)

    results = []
    t0 = time.time()

    # Scan in batches of 5 to avoid overwhelming the server
    batch_size = 5
    async with httpx.AsyncClient() as client:
        for i in range(0, total, batch_size):
            batch = SEED_SERVICES[i:i + batch_size]
            tasks = [
                scan_one(client, url, i + j + 1, total)
                for j, url in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            # Small delay between batches
            if i + batch_size < total:
                await asyncio.sleep(1)

    elapsed = time.time() - t0
    success = sum(1 for r in results if r.get("ok"))
    failed = total - success

    print("\n" + "=" * 60)
    print(f"📊 Results: {success} success, {failed} failed, {elapsed:.1f}s total")

    if success > 0:
        scores = [r["score"] for r in results if r.get("ok") and isinstance(r.get("score"), int)]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"📈 Average score: {avg:.1f}")
            print(f"📈 Range: {min(scores)} — {max(scores)}")

    # Now test benchmark
    print("\n🔍 Testing benchmark endpoint...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/api/v1/benchmark")
        if resp.status_code == 200:
            bm = resp.json()
            print(f"   Total services in benchmark: {bm.get('total_services', 0)}")
            stats = bm.get("score_stats", {})
            if stats:
                print(f"   Average: {stats.get('average')}")
                print(f"   Median: {stats.get('median')}")
                print(f"   P25-P75: {stats.get('p25')} — {stats.get('p75')}")


if __name__ == "__main__":
    asyncio.run(main())
