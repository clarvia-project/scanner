"""
KPI 수집 + 스냅샷 저장 (성장 추이 추적)
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from config import SNAPSHOT_FILE


# ── KPI 수집 ────────────────────────────────────────────
def fetch_clarvia_kpi(health_body: dict, response_ms: int) -> dict:
    """Clarvia KPI 수집"""
    kpi = {
        "healthy":          health_body.get("status") == "healthy",
        "response_ms":      response_ms,
        "tool_count":       0,
        "data_age_hours":   0,
        "npm_downloads_7d": 0,
        "cache_entries":    0,
    }

    # health endpoint에서 추출
    checks = health_body.get("checks", {})
    data   = checks.get("data", {})
    cache  = checks.get("cache", {})

    kpi["tool_count"]     = data.get("tool_count", 0)
    kpi["data_age_hours"] = data.get("age_hours", 0)
    kpi["cache_entries"]  = cache.get("entries", 0)

    # npm 다운로드 (공개 API)
    try:
        url = "https://api.npmjs.org/downloads/point/last-week/clarvia-mcp-server"
        with urllib.request.urlopen(url, timeout=8) as r:
            npm_data = json.loads(r.read())
            kpi["npm_downloads_7d"] = npm_data.get("downloads", 0)
    except Exception:
        pass

    return kpi


def fetch_auton_kpi(health_body: dict) -> dict:
    """Auton KPI 수집"""
    stats = health_body.get("stats", {})
    economy = stats.get("economy", {})
    return {
        "healthy":               health_body.get("status") == "ok",
        "total_agents":          stats.get("total_agents", 0),
        "active_agents":         stats.get("active_agents", 0),
        "total_posts":           stats.get("total_posts", 0),
        "total_interactions":    stats.get("total_interactions", 0),
        "total_follows":         stats.get("total_follows", 0),
        "economy_volume":        economy.get("total_volume_lamports", 0),
        "economy_transactions":  economy.get("total_transactions", 0),
    }


def fetch_ortus_kpi(healthy: bool) -> dict:
    """Ortus KPI — API key 필요해서 헬스체크 결과만"""
    return {
        "healthy": healthy,
        "api_online": healthy,
        "build_blockers_remaining": 3,  # Helius 키 교체 / devnet / E2E
    }


def fetch_merx_kpi() -> dict:
    return {"status": "waiting", "phase": "waiting"}


# ── 스냅샷 저장/로드 ────────────────────────────────────
def load_snapshots() -> dict:
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_snapshot(date_str: str, kpis: dict) -> None:
    """하루 한 번 KPI 스냅샷 저장"""
    data = load_snapshots()
    data[date_str] = {
        **kpis,
        "_saved_at": datetime.now(timezone.utc).isoformat(),
    }
    # 최근 90일만 보관
    keys = sorted(data.keys())
    if len(keys) > 90:
        for old in keys[:-90]:
            del data[old]
    SNAPSHOT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_prev_snapshot(days_ago: int = 7) -> dict | None:
    """N일 전 스냅샷 반환"""
    from datetime import timedelta
    data = load_snapshots()
    target = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return data.get(target)


def get_yesterday_snapshot() -> dict | None:
    return get_prev_snapshot(1)


def get_week_ago_snapshot() -> dict | None:
    return get_prev_snapshot(7)


# ── 성장 분석 ─────────────────────────────────────────────
def analyze_growth(current: dict, history: dict) -> dict:
    """
    current와 history를 비교해서 프로젝트별 성장 분석 반환
    Returns: {project: {kpi: {value, delta_1d, delta_7d, trend}}}
    """
    result = {}
    today = datetime.now().strftime("%Y-%m-%d")
    prev_1d = get_yesterday_snapshot()
    prev_7d = get_week_ago_snapshot()

    for project, kpis in current.items():
        result[project] = {}
        for key, val in kpis.items():
            if not isinstance(val, (int, float)):
                continue
            d1  = _delta_pct(val, prev_1d, project, key) if prev_1d else None
            d7  = _delta_pct(val, prev_7d, project, key) if prev_7d else None
            result[project][key] = {
                "value":    val,
                "delta_1d": d1,
                "delta_7d": d7,
                "trend":    _classify_trend(d7 or d1),
            }
    return result


def _delta_pct(current: float, snapshot: dict | None, project: str, key: str) -> float | None:
    if not snapshot:
        return None
    old = snapshot.get(project, {}).get(key)
    if old is None or old == 0:
        return None
    return (current - old) / old * 100


def _classify_trend(pct: float | None) -> str:
    if pct is None:     return "unknown"
    if pct >= 10:       return "strong_up"
    if pct >= 2:        return "up"
    if pct >= -2:       return "flat"
    if pct >= -10:      return "down"
    return "strong_down"
