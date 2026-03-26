"""Near-realtime agent tool sync system.

Monitors all sources for new tools and updates:
1. Official MCP Registry — updated_since parameter for incremental sync
2. Glama.ai — sitemap diff
3. GitHub — recently created/updated repos with agent topics
4. npm — recently published AI/agent packages
5. PyPI — RSS feed for new packages

Designed to run every 15 minutes via scheduled task.
Each run only fetches NEW items since last check.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
STATE_FILE = DATA / "realtime-sync-state.json"
NEW_TOOLS_FILE = DATA / "new-tools-queue.jsonl"  # append-only log of new discoveries

API = "https://clarvia-api.onrender.com/api/scan"
TRENDING_API = "https://clarvia-api.onrender.com/v1/trending"
ADMIN_KEY = "***REMOVED***"

# Category classification keywords (mirrors tool_scorer.py)
CAT_KEYWORDS = {
    "ai": ["ai", "llm", "gpt", "claude", "openai", "ml", "model", "agent"],
    "developer_tools": ["github", "git", "docker", "ci", "deploy", "dev", "code", "ide"],
    "communication": ["slack", "discord", "email", "chat", "message", "telegram"],
    "data": ["database", "sql", "analytics", "data", "postgres", "dune", "snowflake", "bigquery"],
    "productivity": ["notion", "calendar", "task", "project", "todoist"],
    "blockchain": ["solana", "ethereum", "web3", "crypto", "defi", "onchain"],
    "payments": ["payment", "stripe", "billing", "invoice"],
    "mcp": ["mcp", "model context protocol", "smithery", "glama"],
    "iot": ["iot", "home", "automation", "mqtt", "zigbee", "homeassistant", "hass"],
    "design": ["figma", "design", "ui", "ux", "sketch"],
    "search": ["search", "browse", "web", "scrape", "crawl"],
    "file_management": ["file", "storage", "drive", "dropbox", "s3"],
}


def classify_category(name: str, description: str) -> str:
    """Classify a tool into a category based on name and description."""
    combined = f"{name.lower()} {description.lower()}"
    for cat, kws in CAT_KEYWORDS.items():
        if any(kw in combined for kw in kws):
            return cat
    return "other"


def get_category_top3(category: str) -> list[dict]:
    """Fetch top 3 tools in a category from the trending API."""
    try:
        req = urllib.request.Request(TRENDING_API, headers={
            "User-Agent": "clarvia-realtime/1.0",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        cat_tools = data.get("by_category", {}).get(category, [])
        return cat_tools[:3]
    except Exception:
        return []


def get_category_avg(category: str) -> float | None:
    """Fetch avg score for a category from trending API category_stats."""
    try:
        req = urllib.request.Request(TRENDING_API, headers={
            "User-Agent": "clarvia-realtime/1.0",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        stats = data.get("category_stats", {}).get(category, {})
        return stats.get("avg_score")
    except Exception:
        return None


def score_emoji(score: int | None) -> str:
    """Return color emoji based on AEO score tier."""
    if score is None:
        return "⚪"
    if score >= 60:
        return "🟢"
    if score >= 40:
        return "🔵"
    if score >= 20:
        return "🟡"
    return "🔴"


def build_enhanced_report(new_tools: list[dict], total_discovered: int, total_scanned: int) -> str:
    """Build the enhanced Telegram report with category analysis."""
    if not new_tools:
        return ""

    lines = [f"🔄 Clarvia 실시간 도구 동기화 완료 ({len(new_tools)}개 신규)\n"]
    lines.append("📊 새 도구 분석:\n")

    # Cache trending data (single fetch)
    trending_data = None
    try:
        req = urllib.request.Request(TRENDING_API, headers={
            "User-Agent": "clarvia-realtime/1.0",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        trending_data = json.loads(resp.read())
    except Exception:
        pass

    for i, tool in enumerate(new_tools, 1):
        name = tool.get("name", "unknown")
        score = tool.get("aeo_score")
        category = tool.get("category", "other")
        emoji = score_emoji(score)

        score_str = f"AEO: {score}" if score is not None else "스캔 실패"
        lines.append(f"{i}. {emoji} {name} ({score_str})")
        lines.append(f"   카테고리: {category}")

        # Category Top 3 from cached trending data
        if trending_data:
            cat_tools = trending_data.get("by_category", {}).get(category, [])
            top3 = cat_tools[:3]
            if top3:
                top3_str = ", ".join(
                    f"{t.get('service_name', '?')}({t.get('clarvia_score', '?')})"
                    for t in top3
                )
                lines.append(f"   분야 Top 3: {top3_str}")

                # Determine rank position
                if score is not None:
                    rank = 1
                    for t in cat_tools:
                        if t.get("clarvia_score", 0) > score:
                            rank += 1
                    if rank <= 3:
                        lines.append(f"   → 분야 {rank}위 진입")
                    else:
                        cat_stats = trending_data.get("category_stats", {}).get(category, {})
                        avg = cat_stats.get("avg_score")
                        if avg is not None:
                            if score >= avg:
                                lines.append(f"   → 분야 평균({avg:.0f}) 이상")
                            else:
                                lines.append(f"   → 분야 평균({avg:.0f}) 이하")
                        else:
                            lines.append(f"   → 분야 {rank}위")
            else:
                lines.append(f"   → 분야 첫 진입 (비교 데이터 없음)")
        lines.append("")

    lines.append(f"📈 누적: {total_discovered:,} 발견 / {total_scanned:,} 스캔")

    return "\n".join(lines)


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_run": None,
        "mcp_registry_cursor": None,
        "last_npm_check": None,
        "known_urls": set(),
        "total_discovered": 0,
        "total_scanned": 0,
    }


def save_state(state: dict):
    # Convert sets to lists for JSON
    s = dict(state)
    if isinstance(s.get("known_urls"), set):
        s["known_urls"] = list(s["known_urls"])
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


def append_new_tool(tool: dict):
    """Append a newly discovered tool to the queue."""
    tool["discovered_at"] = datetime.now(timezone.utc).isoformat()
    with open(NEW_TOOLS_FILE, "a") as f:
        f.write(json.dumps(tool) + "\n")


def scan_url(url: str) -> dict | None:
    """Quick scan a single URL."""
    try:
        body = json.dumps({"url": url}).encode()
        req = urllib.request.Request(API, data=body, headers={
            "Content-Type": "application/json",
            "X-API-Key": ADMIN_KEY,
        })
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        return {"url": url, "score": data.get("clarvia_score"), "ok": True}
    except:
        return None


# ─── Source: MCP Registry (incremental) ───

def check_mcp_registry(state: dict) -> list[dict]:
    """Fetch only new/updated MCP servers since last check."""
    new_items = []
    last_run = state.get("last_run")

    params = "limit=100&version=latest"
    if last_run:
        params += f"&updated_since={urllib.parse.quote(last_run)}"

    cursor = None
    while True:
        url = f"https://registry.modelcontextprotocol.io/v0.1/servers?{params}"
        if cursor:
            url += f"&cursor={urllib.parse.quote(cursor)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "clarvia-realtime/1.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            print(f"  MCP Registry error: {e}")
            break

        servers = data.get("servers", [])
        for s in servers:
            srv = s.get("server", {})
            tool_url = srv.get("websiteUrl") or srv.get("repository", {}).get("url")
            if tool_url:
                new_items.append({
                    "name": srv.get("name", ""),
                    "description": srv.get("description", ""),
                    "url": tool_url,
                    "version": srv.get("version", ""),
                    "source": "mcp_registry",
                    "type": "mcp_server",
                })

        next_cursor = data.get("metadata", {}).get("nextCursor")
        if not next_cursor or not servers:
            break
        cursor = next_cursor
        time.sleep(0.3)

    return new_items


# ─── Source: npm (recent publishes) ───

def check_npm_recent() -> list[dict]:
    """Check npm for recently published AI/agent packages."""
    new_items = []
    keywords = ["mcp-server", "ai-agent", "agent-tool", "claude-skill", "llm-tool"]

    for kw in keywords:
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text={kw}&size=20&quality=0.5&maintenance=0.5&popularity=0.5"
            req = urllib.request.Request(url, headers={"User-Agent": "clarvia-realtime/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for obj in data.get("objects", []):
                pkg = obj.get("package", {})
                # Check if recently published (within last day)
                date_str = pkg.get("date", "")
                if date_str:
                    try:
                        pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if pub_date > datetime.now(timezone.utc) - timedelta(days=1):
                            new_items.append({
                                "name": pkg.get("name", ""),
                                "description": pkg.get("description", ""),
                                "url": pkg.get("links", {}).get("npm", ""),
                                "version": pkg.get("version", ""),
                                "source": "npm",
                                "type": "cli_tool" if "cli" in pkg.get("name", "").lower() else "mcp_server",
                                "install_command": f"npm install {pkg.get('name', '')}",
                            })
                    except:
                        pass
            time.sleep(0.5)
        except:
            pass

    return new_items


# ─── Source: GitHub (recently created) ───

def check_github_recent() -> list[dict]:
    """Check GitHub for recently created MCP/agent repos."""
    new_items = []
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    queries = [
        f"topic:mcp-server created:>={yesterday}",
        f"topic:claude-skills created:>={yesterday}",
        f"topic:ai-agent-tools created:>={yesterday}",
    ]

    for q in queries:
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=created&per_page=50"
            req = urllib.request.Request(url, headers={"User-Agent": "clarvia-realtime/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for repo in data.get("items", []):
                new_items.append({
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description", "") or "",
                    "url": repo["html_url"],
                    "stars": repo.get("stargazers_count", 0),
                    "source": "github",
                    "type": "skill" if "skill" in q else "mcp_server",
                })
            time.sleep(2)
        except:
            pass

    return new_items


# ─── Main ───

def main():
    state = load_state()
    known = set(state.get("known_urls", []))

    print(f"🦉 Clarvia Realtime Sync")
    print(f"   Last run: {state.get('last_run', 'never')}")
    print(f"   Known tools: {len(known):,}")
    print("─" * 50)

    all_new = []

    # 1. MCP Registry
    print("\n📡 MCP Registry (incremental)...")
    mcp_new = check_mcp_registry(state)
    mcp_truly_new = [t for t in mcp_new if t.get("url") and t["url"] not in known]
    print(f"   Found: {len(mcp_new)}, New: {len(mcp_truly_new)}")
    all_new.extend(mcp_truly_new)

    # 2. npm
    print("\n📦 npm (last 24h)...")
    npm_new = check_npm_recent()
    npm_truly_new = [t for t in npm_new if t.get("url") and t["url"] not in known]
    print(f"   Found: {len(npm_new)}, New: {len(npm_truly_new)}")
    all_new.extend(npm_truly_new)

    # 3. GitHub
    print("\n🐙 GitHub (last 24h)...")
    gh_new = check_github_recent()
    gh_truly_new = [t for t in gh_new if t.get("url") and t["url"] not in known]
    print(f"   Found: {len(gh_new)}, New: {len(gh_truly_new)}")
    all_new.extend(gh_truly_new)

    # Deduplicate
    seen = set()
    unique_new = []
    for t in all_new:
        url = t.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique_new.append(t)

    print(f"\n{'─' * 50}")
    print(f"📊 총 새 도구: {len(unique_new)}")

    # Scan new tools
    scanned = 0
    if unique_new:
        print(f"\n🔍 Scanning {len(unique_new)} new tools...")
        for i, tool in enumerate(unique_new):
            url = tool.get("url", "")
            if not url:
                continue

            # Classify category
            tool["category"] = classify_category(
                tool.get("name", ""),
                tool.get("description", ""),
            )

            result = scan_url(url)
            if result and result.get("ok"):
                tool["aeo_score"] = result.get("score")
                scanned += 1
                print(f"   [{i+1}/{len(unique_new)}] ✅ {tool['name']} → {result.get('score')} [{tool['category']}]")
            else:
                print(f"   [{i+1}/{len(unique_new)}] ⏭️ {tool['name']} (scan skipped) [{tool['category']}]")

            # Append to discovery log
            append_new_tool(tool)
            known.add(url)
            time.sleep(3)

    # Update state
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["known_urls"] = known
    state["total_discovered"] = state.get("total_discovered", 0) + len(unique_new)
    state["total_scanned"] = state.get("total_scanned", 0) + scanned
    save_state(state)

    # Build enhanced report for Telegram
    if unique_new:
        report = build_enhanced_report(
            unique_new,
            state["total_discovered"],
            state["total_scanned"],
        )
        # Write report to a file for the SKILL.md to pick up
        report_file = DATA / "last-sync-report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\n📝 Enhanced report saved to {report_file}")
        print("\n" + report)

    print(f"\n{'=' * 50}")
    print(f"✅ 완료: {len(unique_new)} 발견, {scanned} 스캔")
    print(f"📊 누적: {state['total_discovered']:,} 발견, {state['total_scanned']:,} 스캔")


if __name__ == "__main__":
    main()
