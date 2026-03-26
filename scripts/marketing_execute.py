#!/usr/bin/env python3
"""Comprehensive Agent Marketing Automation — runs 24/7 via GitHub Actions.

Executes ALL possible agent-facing marketing activities.
Target: AI agents only. No human social media.

Channels:
  1. MCP Registries (Smithery, Glama, mcp.so, PulseMCP, Official Registry)
  2. npm/PyPI SEO (keywords, description, README)
  3. GitHub optimization (topics, description, README)
  4. .well-known/agents.json
  5. OpenAPI spec discoverability
  6. Framework integrations (LangChain, CrewAI, AutoGen)
  7. Awesome-list PRs
  8. Package registry trending
  9. Cross-platform config examples (Claude, Cursor, Windsurf, Cline)
  10. API documentation SEO
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOG_FILE = PROJECT_DIR / "data" / "marketing-log.jsonl"
API_URL = os.environ.get("CLARVIA_API_URL", "https://clarvia-api.onrender.com")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6558975935")


# ─── Helpers ────────────────────────────────────────────────────

def log_activity(activity: str, channel: str, detail: str = "", success: bool = True):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "activity": activity,
        "channel": channel,
        "detail": detail[:200],
        "success": success,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info("[%s] %s: %s", channel, activity, detail[:100] or "OK")
    return entry


def fetch_json(url: str, timeout: int = 15) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clarvia-marketing/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.debug("Fetch failed %s: %s", url, e)
        return None


def send_telegram(text: str):
    if not TELEGRAM_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN set, skipping Telegram")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Telegram sent: %d", resp.status)
    except Exception as e:
        logger.warning("Telegram failed: %s", e)


def run_cmd(cmd: str, timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


# ─── Metrics Collection ────────────────────────────────────────

def collect_metrics() -> dict:
    metrics = {"ts": datetime.now(timezone.utc).isoformat()}

    # Platform stats
    stats = fetch_json(f"{API_URL}/v1/stats")
    if stats:
        metrics["total_tools"] = stats.get("total_services", 0)
        metrics["avg_score"] = stats.get("avg_score", 0)
        metrics["by_type"] = stats.get("by_type", {})

    # Search demand
    demand = fetch_json(f"{API_URL}/v1/demand?days=1")
    if demand:
        metrics["searches_today"] = demand.get("total_searches", 0)
        metrics["top_queries"] = demand.get("top_queries", [])[:5]
        metrics["zero_results"] = demand.get("zero_result_queries", [])[:5]

    # npm downloads
    npm = fetch_json("https://api.npmjs.org/downloads/point/last-week/clarvia-mcp-server")
    if npm:
        metrics["npm_weekly"] = npm.get("downloads", 0)

    npm_daily = fetch_json("https://api.npmjs.org/downloads/point/last-day/clarvia-mcp-server")
    if npm_daily:
        metrics["npm_daily"] = npm_daily.get("downloads", 0)

    # API health
    try:
        req = urllib.request.Request(f"{API_URL}/v1/stats")
        with urllib.request.urlopen(req, timeout=10) as resp:
            metrics["api_status"] = resp.status
    except Exception:
        metrics["api_status"] = 0

    return metrics


# ─── Marketing Activities ──────────────────────────────────────

def check_npm_search_visibility():
    """Check if clarvia appears in key npm searches."""
    searches = [
        "mcp server tool discovery",
        "ai agent tools",
        "mcp scoring",
        "agent compatibility",
        "aeo scanner",
    ]
    found = 0
    for query in searches:
        data = fetch_json(f"https://registry.npmjs.org/-/v1/search?text={query.replace(' ', '+')}&size=20")
        if data:
            names = [p["package"]["name"] for p in data.get("objects", [])]
            if "clarvia-mcp-server" in names:
                found += 1
    log_activity("npm_search_check", "npm", f"Found in {found}/{len(searches)} searches")
    return found


def check_directory_status():
    """Check status of all directory listings."""
    results = {}

    # mcp.so
    data = fetch_json("https://mcp.so/api/search?q=clarvia")
    results["mcp_so"] = "listed" if data and data.get("results") else "unknown"

    # Check awesome-list PR
    code, out = run_cmd("gh pr view 771 --repo appcypher/awesome-mcp-servers --json state -q '.state' 2>/dev/null")
    results["appcypher_pr"] = out.strip() if code == 0 else "unknown"

    log_activity("directory_status_check", "directories", json.dumps(results))
    return results


def optimize_github_repo():
    """Ensure GitHub repo is optimized for agent discovery."""
    code, out = run_cmd(
        'gh repo edit clarvia-project/scanner '
        '--description "AI agent tool discovery & AEO scoring — 15,400+ indexed MCP servers, APIs, CLIs. '
        'Free API + 24 MCP tools + npm package. clarvia.art" '
        '--add-topic mcp --add-topic ai-agents --add-topic tool-discovery '
        '--add-topic aeo --add-topic agent-tools --add-topic llm-tools '
        '--add-topic mcp-server --add-topic ai-tools --add-topic agent-compatibility '
        '--add-topic clarvia'
    )
    log_activity("github_optimize", "github", "Topics updated" if code == 0 else out[:100], code == 0)


def ensure_agents_json():
    """Ensure .well-known/agents.json is up to date."""
    agents_path = PROJECT_DIR / "frontend" / "public" / ".well-known" / "agents.json"
    agents_path.parent.mkdir(parents=True, exist_ok=True)

    agents_data = {
        "name": "Clarvia",
        "description": "AI agent tool discovery and AEO scoring platform. 15,400+ indexed tools.",
        "url": "https://clarvia.art",
        "api": {
            "base_url": API_URL,
            "openapi": f"{API_URL}/openapi.json",
            "docs": f"{API_URL}/docs",
        },
        "mcp": {
            "npm_package": "clarvia-mcp-server",
            "install": "npx -y clarvia-mcp-server",
            "tools_count": 24,
            "transport": "stdio",
        },
        "capabilities": [
            "tool_discovery", "tool_scoring", "vulnerability_check",
            "dependency_audit", "compliance_checklist", "tool_comparison",
            "trend_analysis", "demand_intelligence", "tool_enrichment",
        ],
        "pricing": "free",
        "version": "2.0",
    }

    with open(agents_path, "w") as f:
        json.dump(agents_data, f, indent=2)
    log_activity("agents_json_update", "web", str(agents_path))


def check_api_endpoints():
    """Verify all critical API endpoints are responding."""
    endpoints = [
        "/v1/stats", "/v1/categories", "/v1/featured",
        "/v1/methodology", "/v1/demand", "/openapi.json",
    ]
    ok = 0
    for ep in endpoints:
        try:
            req = urllib.request.Request(f"{API_URL}{ep}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    ok += 1
        except Exception:
            pass
    log_activity("api_health_check", "api", f"{ok}/{len(endpoints)} endpoints OK")
    return ok == len(endpoints)


def ping_keep_alive():
    """Ping API to prevent Render cold start."""
    try:
        fetch_json(f"{API_URL}/v1/stats")
        log_activity("keep_alive_ping", "infra", "OK")
    except Exception as e:
        log_activity("keep_alive_ping", "infra", str(e), False)


def check_pypi_status():
    """Check PyPI package status."""
    data = fetch_json("https://pypi.org/pypi/clarvia-langchain/json")
    if data:
        version = data.get("info", {}).get("version", "?")
        log_activity("pypi_check", "pypi", f"clarvia-langchain@{version}")
    else:
        log_activity("pypi_check", "pypi", "Not found or error", False)


def check_npm_package_health():
    """Check npm package metadata is correct."""
    data = fetch_json("https://registry.npmjs.org/clarvia-mcp-server")
    if data:
        latest = data.get("dist-tags", {}).get("latest", "?")
        desc = data.get("description", "")[:80]
        keywords = data.get("keywords", [])
        log_activity("npm_health", "npm", f"v{latest}, {len(keywords)} keywords, desc: {desc}")


def submit_to_registries():
    """Check and submit to registries that support programmatic submission."""
    # Smithery - check if listed
    data = fetch_json("https://registry.smithery.ai/servers?q=clarvia")
    if data and not data.get("servers"):
        log_activity("smithery_not_listed", "smithery", "Not yet listed - needs HTTP endpoint")

    # Check Official MCP Registry
    code, out = run_cmd("gh pr list --repo modelcontextprotocol/registry --author digitamaz --state all 2>/dev/null")
    if "clarvia" not in out.lower():
        log_activity("official_registry_needed", "mcp_official", "PR not yet submitted")
    else:
        log_activity("official_registry_check", "mcp_official", "PR exists")


# ─── Main Execution ────────────────────────────────────────────

def run_morning():
    """Morning routine: collect metrics, plan, send to Telegram, execute."""
    logger.info("=== Morning Marketing Routine ===")

    metrics = collect_metrics()
    activities = []

    # Execute all marketing activities
    check_npm_search_visibility()
    activities.append("npm 검색 노출 확인")

    dirs = check_directory_status()
    activities.append(f"디렉토리 상태 확인: {json.dumps(dirs)}")

    optimize_github_repo()
    activities.append("GitHub 레포 최적화")

    ensure_agents_json()
    activities.append("agents.json 갱신")

    check_api_endpoints()
    activities.append("API 헬스체크")

    check_npm_package_health()
    activities.append("npm 패키지 상태 확인")

    check_pypi_status()
    activities.append("PyPI 패키지 확인")

    submit_to_registries()
    activities.append("레지스트리 등록 상태 확인")

    ping_keep_alive()
    activities.append("Keep-alive 핑")

    # Send morning plan
    msg = f"""🌅 Clarvia 모닝 플랜 — {datetime.now().strftime('%m/%d')}

📊 현재 지표:
• 인덱싱 도구: {metrics.get('total_tools', '?')}개
• API 검색(오늘): {metrics.get('searches_today', 0)}건
• npm 다운로드(주간): {metrics.get('npm_weekly', '?')}
• API 상태: {'정상' if metrics.get('api_status') == 200 else '이상'}

📋 오늘 실행한 활동:
{chr(10).join(f'• {a}' for a in activities)}

🎯 목표 대비:
• 1주차 목표: 일일 50건 → 현재 {metrics.get('searches_today', 0)}건
• 최종 목표: 일일 1,000,000
• npm 주간: {metrics.get('npm_weekly', 0)}/1,000 목표"""

    send_telegram(msg)
    logger.info("=== Morning routine complete ===")


def run_evening():
    """Evening routine: collect final metrics, report results."""
    logger.info("=== Evening Report Routine ===")

    metrics = collect_metrics()

    # Count today's activities
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_activities = []
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("ts", "").startswith(today):
                        today_activities.append(entry)
                except Exception:
                    pass

    success_count = sum(1 for a in today_activities if a.get("success"))

    msg = f"""🌙 Clarvia 저녁 리포트 — {datetime.now().strftime('%m/%d')}

📊 오늘 성과:
• 인덱싱 도구: {metrics.get('total_tools', '?')}개
• API 검색: {metrics.get('searches_today', 0)}건
• npm 다운로드(오늘/주간): {metrics.get('npm_daily', 0)}/{metrics.get('npm_weekly', 0)}
• API 상태: {'정상' if metrics.get('api_status') == 200 else '이상'}

📣 마케팅 활동: {len(today_activities)}건 ({success_count}건 성공)

📈 성장 추적:
• 일일 에이전트 방문: {metrics.get('searches_today', 0)} (목표: 1,000,000)
• 진행률: {metrics.get('searches_today', 0)/10000:.4f}%
• npm 주간 목표: {metrics.get('npm_weekly', 0)}/1,000

📋 내일 우선순위:
• 새 디렉토리 등록 시도
• 프레임워크 통합 확대
• npm 키워드 A/B 테스트"""

    send_telegram(msg)
    logger.info("=== Evening routine complete ===")


def run_keepalive():
    """Just ping the API to prevent cold starts."""
    ping_keep_alive()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    if mode == "morning":
        run_morning()
    elif mode == "evening":
        run_evening()
    elif mode == "keepalive":
        run_keepalive()
    else:
        print(f"Usage: {sys.argv[0]} [morning|evening|keepalive]")
