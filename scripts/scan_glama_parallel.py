"""Parallel scan of MCP registry servers using asyncio + httpx."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

API = "https://clarvia-api.onrender.com/api/scan"
ADMIN_KEY = os.environ.get("SCANNER_ADMIN_API_KEY", "")
BASE = Path(__file__).resolve().parent.parent

URLS_FILE = BASE / "data" / "glama-scan-urls.json"
RESULTS_FILE = BASE / "data" / "glama-scan-results.json"

CONCURRENCY = 10  # parallel requests
TIMEOUT = 120


async def scan_one(client: httpx.AsyncClient, url: str, idx: int, total: int) -> dict:
    try:
        resp = await client.post(
            API,
            json={"url": url},
            headers={"X-API-Key": ADMIN_KEY},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            score = data.get("clarvia_score", "?")
            print(f"[{idx}/{total}] OK {url} → {score}")
            return {"url": url, "score": score, "rating": data.get("rating"),
                    "service_name": data.get("service_name"), "scan_id": data.get("scan_id"), "ok": True}
        elif resp.status_code == 429:
            print(f"[{idx}/{total}] RATE {url}")
            return {"url": url, "error": "429", "ok": False, "retry": True}
        else:
            print(f"[{idx}/{total}] ERR {url} → {resp.status_code}")
            return {"url": url, "error": f"HTTP {resp.status_code}", "ok": False}
    except Exception as e:
        print(f"[{idx}/{total}] FAIL {url} → {str(e)[:60]}")
        return {"url": url, "error": str(e)[:100], "ok": False}


async def main():
    with open(URLS_FILE) as f:
        urls = json.load(f)

    # Resume support
    existing = []
    scanned_urls = set()
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            existing = json.load(f)
        scanned_urls = {r["url"] for r in existing if r.get("ok")}

    remaining = [u for u in urls if u not in scanned_urls]
    total = len(remaining)

    print(f"\n🦉 Clarvia Parallel MCP Scan")
    print(f"   Total URLs: {len(urls)}")
    print(f"   Already done: {len(scanned_urls)}")
    print(f"   Remaining: {total}")
    print(f"   Concurrency: {CONCURRENCY}")
    print("=" * 60)

    results = list(existing)
    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.time()

    async def bounded_scan(client, url, idx):
        async with sem:
            r = await scan_one(client, url, idx, total)
            await asyncio.sleep(2)  # small delay between requests
            return r

    async with httpx.AsyncClient() as client:
        # Process in batches of 50
        for batch_start in range(0, total, 50):
            batch = remaining[batch_start:batch_start + 50]
            tasks = [
                bounded_scan(client, url, batch_start + i + 1)
                for i, url in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            # Save after each batch
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f)

            ok = len([r for r in results if r.get("ok")])
            elapsed = time.time() - t0
            rate = ok / (elapsed / 60) if elapsed > 0 else 0
            print(f"  --- Batch done. Total OK: {ok}, Rate: {rate:.0f}/min, Elapsed: {elapsed:.0f}s ---")

    # Final stats
    ok_results = [r for r in results if r.get("ok")]
    scores = [r["score"] for r in ok_results if isinstance(r.get("score"), (int, float))]

    print("\n" + "=" * 60)
    print(f"📊 완료: {len(ok_results)} 성공, {total - len(ok_results)} 실패")
    if scores:
        print(f"📈 평균: {sum(scores)/len(scores):.1f}, 범위: {min(scores)}-{max(scores)}")
    print(f"⏱️ 총 소요: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
