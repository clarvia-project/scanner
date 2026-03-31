"""
서비스 헬스체크 + Render API 상태 조회
"""
import json
import time
import urllib.request
import urllib.error
from config import SERVICES, RENDER_API_KEY, RENDER_API_BASE


def check_http(url: str, path: str = "/health", timeout: int = 10) -> tuple[bool, int, dict]:
    """
    Returns: (healthy, response_ms, json_body)
    """
    if not url:
        return True, 0, {}   # Background Worker는 HTTP 없음 → 항상 ok로 간주
    full_url = url.rstrip("/") + path
    start = time.time()
    try:
        with urllib.request.urlopen(full_url, timeout=timeout) as r:
            ms = int((time.time() - start) * 1000)
            body = {}
            try:
                body = json.loads(r.read())
            except Exception:
                pass
            return True, ms, body
    except urllib.error.HTTPError as e:
        ms = int((time.time() - start) * 1000)
        # 401/403 = 인증 필요지만 서비스는 살아있음
        if e.code in (401, 403):
            return True, ms, {"status": "ok", "note": "auth_required"}
        return False, ms, {"error": str(e)}
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        return False, ms, {"error": str(e)}


def check_render_service(render_id: str) -> dict | None:
    """Render API로 서비스 상태 조회"""
    if not RENDER_API_KEY:
        return None
    try:
        req = urllib.request.Request(
            f"{RENDER_API_BASE}/services/{render_id}",
            headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None


def get_recent_deploy_status(render_id: str) -> str | None:
    """최근 배포 상태 반환"""
    if not RENDER_API_KEY:
        return None
    try:
        req = urllib.request.Request(
            f"{RENDER_API_BASE}/services/{render_id}/deploys?limit=1",
            headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            if data:
                return data[0].get("status")
    except Exception:
        pass
    return None


def run_all_checks() -> dict:
    """
    모든 서비스 헬스체크 실행
    Returns: {service_key: {healthy, ms, body, render_status}}
    """
    results = {}
    for key, svc in SERVICES.items():
        healthy, ms, body = check_http(svc["url"], svc["health_path"] or "/health")
        render_status = get_recent_deploy_status(svc["render_id"])
        results[key] = {
            "healthy":        healthy,
            "ms":             ms,
            "body":           body,
            "render_status":  render_status,
            "service_name":   svc["name"],
            "project":        svc["project"],
        }
    return results
