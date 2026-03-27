"""Daily sync: fetch new MCP servers from registries and scan them.

Sources:
1. Official MCP Registry (registry.modelcontextprotocol.io)
2. Glama.ai sitemap (glama.ai/sitemaps/mcp-servers.xml)

Detects new servers since last sync, scans them, saves results.
Designed to run as a daily cron/scheduled task.
"""

import asyncio
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

API = "https://clarvia-api.onrender.com/api/scan"
ADMIN_KEY = os.environ.get("SCANNER_ADMIN_API_KEY", "")
CONCURRENCY = 10
SCAN_TIMEOUT = 120

STATE_FILE = DATA / "sync-state.json"
RESULTS_FILE = DATA / "mcp-scan-results-all.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync": None, "known_urls": [], "total_scanned": 0}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_results() -> list[dict]:
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return []


def save_results(results: list[dict]):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f)


# ─── Source 1: Official MCP Registry ───

def fetch_official_registry() -> list[str]:
    """Fetch all URLs from the official MCP registry."""
    all_servers = []
    cursor = None

    while True:
        url = "https://registry.modelcontextprotocol.io/v0.1/servers?limit=100&version=latest"
        if cursor:
            url += f"&cursor={urllib.parse.quote(cursor)}"

        req = urllib.request.Request(url, headers={"User-Agent": "clarvia-sync/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())

        for s in data.get("servers", []):
            srv = s.get("server", {})
            u = srv.get("websiteUrl") or srv.get("repository", {}).get("url")
            if not u:
                name = srv.get("name", "")
                if name:
                    u = f"https://www.npmjs.com/package/{name}"
            if u:
                all_servers.append(u.rstrip("/"))

        next_cursor = data.get("metadata", {}).get("nextCursor")
        if not next_cursor or not data.get("servers"):
            break
        cursor = next_cursor
        time.sleep(0.3)

    return list(dict.fromkeys(all_servers))


# ─── Source 2: Glama.ai Sitemap ───

def fetch_glama_sitemap() -> list[str]:
    """Fetch MCP server URLs from Glama sitemap."""
    try:
        req = urllib.request.Request(
            "https://glama.ai/sitemaps/mcp-servers.xml",
            headers={"User-Agent": "clarvia-sync/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode()
        glama_urls = re.findall(r"<loc>(https://glama\.ai/mcp/servers/[^<]+)</loc>", data)

        github_urls = []
        for u in glama_urls:
            parts = u.replace("https://glama.ai/mcp/servers/", "").split("/")
            if len(parts) >= 2:
                github_urls.append(f"https://github.com/{parts[0]}/{parts[1]}")
        return list(dict.fromkeys(github_urls))
    except Exception as e:
        print(f"⚠️ Glama fetch failed: {e}")
        return []


# ─── Scanner ───

async def scan_urls(urls: list[str]) -> list[dict]:
    """Scan URLs in parallel."""
    results = []
    sem = asyncio.Semaphore(CONCURRENCY)
    total = len(urls)

    async def scan_one(client: httpx.AsyncClient, url: str, idx: int) -> dict:
        async with sem:
            try:
                resp = await client.post(
                    API,
                    json={"url": url},
                    headers={"X-API-Key": ADMIN_KEY},
                    timeout=SCAN_TIMEOUT,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"url": url, "score": data.get("clarvia_score"),
                            "rating": data.get("rating"), "service_name": data.get("service_name"),
                            "scan_id": data.get("scan_id"), "ok": True,
                            "scanned_at": datetime.now(timezone.utc).isoformat()}
                return {"url": url, "error": f"HTTP {resp.status_code}", "ok": False}
            except Exception as e:
                return {"url": url, "error": str(e)[:100], "ok": False}
            finally:
                await asyncio.sleep(2)

    async with httpx.AsyncClient() as client:
        for batch_start in range(0, total, 50):
            batch = urls[batch_start:batch_start + 50]
            tasks = [scan_one(client, url, batch_start + i) for i, url in enumerate(batch)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            ok = len([r for r in results if r.get("ok")])
            print(f"  Batch {batch_start//50 + 1}: {ok}/{len(results)} OK")

    return results


# ─── Main ───

def main():
    state = load_state()
    known = set(state.get("known_urls", []))
    existing_results = load_results()
    scanned_urls = {r["url"] for r in existing_results if r.get("ok")}

    print(f"🦉 Clarvia MCP Registry Sync")
    print(f"   Last sync: {state.get('last_sync', 'never')}")
    print(f"   Known URLs: {len(known)}")
    print(f"   Already scanned: {len(scanned_urls)}")
    print("=" * 60)

    # Fetch all sources
    print("\n📡 Fetching Official Registry...")
    registry_urls = fetch_official_registry()
    print(f"   → {len(registry_urls)} URLs")

    print("\n📡 Fetching Glama.ai...")
    glama_urls = fetch_glama_sitemap()
    print(f"   → {len(glama_urls)} URLs")

    # Combine and deduplicate
    all_urls = set(registry_urls + glama_urls)
    new_urls = all_urls - scanned_urls
    print(f"\n📊 Total unique: {len(all_urls)}")
    print(f"   New to scan: {len(new_urls)}")

    if not new_urls:
        print("\n✅ No new servers to scan. Done.")
        state["last_sync"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return

    # Scan new URLs
    print(f"\n🔍 Scanning {len(new_urls)} new servers...")
    new_results = asyncio.run(scan_urls(sorted(new_urls)))

    # Merge results
    all_results = existing_results + new_results
    save_results(all_results)

    # Update state
    state["known_urls"] = sorted(all_urls)
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    state["total_scanned"] = len([r for r in all_results if r.get("ok")])
    save_state(state)

    ok = len([r for r in new_results if r.get("ok")])
    scores = [r["score"] for r in new_results if r.get("ok") and isinstance(r.get("score"), (int, float))]

    print("\n" + "=" * 60)
    print(f"📊 New: {ok}/{len(new_urls)} scanned")
    print(f"📊 Total: {state['total_scanned']} in database")
    if scores:
        print(f"📈 New avg: {sum(scores)/len(scores):.1f}")


if __name__ == "__main__":
    main()
