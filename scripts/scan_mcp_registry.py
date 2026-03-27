"""Scan all MCP servers from the official registry.

Reads URLs from data/mcp-scan-urls.json and scans them via the Clarvia API.
Uses admin API key to bypass rate limits.

Usage:
    python3 scripts/scan_mcp_registry.py [--resume] [--delay 8]
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API = "https://clarvia-api.onrender.com/api/scan"
ADMIN_KEY = os.environ.get("SCANNER_ADMIN_API_KEY", "")
BASE = Path(__file__).resolve().parent.parent

URLS_FILE = BASE / "data" / "mcp-scan-urls.json"
RESULTS_FILE = BASE / "data" / "mcp-scan-results.json"
PROGRESS_FILE = BASE / "data" / "mcp-scan-progress.json"


def load_urls() -> list[str]:
    with open(URLS_FILE) as f:
        return json.load(f)


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"scanned": [], "failed": [], "last_index": 0}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def load_results() -> list[dict]:
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return []


def save_results(results: list[dict]):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)


def scan_one(url: str) -> dict | None:
    try:
        body = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            API,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": ADMIN_KEY,
            },
        )
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        return {
            "url": url,
            "score": data.get("clarvia_score"),
            "rating": data.get("rating"),
            "service_name": data.get("service_name"),
            "scan_id": data.get("scan_id"),
            "ok": True,
        }
    except urllib.error.HTTPError as e:
        return {"url": url, "error": f"HTTP {e.code}", "ok": False}
    except Exception as e:
        return {"url": url, "error": str(e)[:100], "ok": False}


def main():
    resume = "--resume" in sys.argv
    delay = 8
    for i, arg in enumerate(sys.argv):
        if arg == "--delay" and i + 1 < len(sys.argv):
            delay = int(sys.argv[i + 1])

    urls = load_urls()
    progress = load_progress() if resume else {"scanned": [], "failed": [], "last_index": 0}
    results = load_results() if resume else []

    start_idx = progress["last_index"] if resume else 0
    total = len(urls)
    scanned_urls = set(progress["scanned"])

    print(f"\n🦉 Clarvia MCP Registry Scan")
    print(f"   Total URLs: {total}")
    print(f"   Starting from: {start_idx}")
    print(f"   Delay: {delay}s")
    print(f"   Already scanned: {len(scanned_urls)}")
    print("=" * 60)

    for idx in range(start_idx, total):
        url = urls[idx]
        if url in scanned_urls:
            continue

        result = scan_one(url)
        if result["ok"]:
            results.append(result)
            progress["scanned"].append(url)
            print(f"[{idx+1}/{total}] ✅ {url} → {result['score']}")
        else:
            progress["failed"].append(url)
            print(f"[{idx+1}/{total}] ❌ {url} → {result['error']}")

        progress["last_index"] = idx + 1

        # Save every 10 scans
        if (idx + 1) % 10 == 0:
            save_results(results)
            save_progress(progress)

        time.sleep(delay)

    # Final save
    save_results(results)
    save_progress(progress)

    ok_count = len([r for r in results if r.get("ok")])
    scores = [r["score"] for r in results if r.get("ok") and isinstance(r.get("score"), (int, float))]

    print("\n" + "=" * 60)
    print(f"📊 완료: {ok_count} 성공, {len(progress['failed'])} 실패")
    if scores:
        print(f"📈 평균: {sum(scores)/len(scores):.1f}, 범위: {min(scores)}-{max(scores)}")
    print(f"📁 결과: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
