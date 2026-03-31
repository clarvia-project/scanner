"""
자동 복구 — Render API로 재배포 트리거
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from config import RENDER_API_KEY, RENDER_API_BASE, INCIDENT_LOG


def _render_redeploy(render_id: str) -> tuple[bool, str]:
    """Render Manual Deploy 트리거"""
    if not RENDER_API_KEY:
        return False, "RENDER_API_KEY 미설정 — 수동 재시작 필요"
    try:
        req = urllib.request.Request(
            f"{RENDER_API_BASE}/services/{render_id}/deploys",
            data=json.dumps({"clearCache": "do_not_clear"}).encode(),
            headers={
                "Authorization": f"Bearer {RENDER_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
            deploy_id = result.get("id", "")
            return True, f"재배포 시작 (deploy: {deploy_id})"
    except urllib.error.HTTPError as e:
        return False, f"Render API 오류: {e.code} {e.reason}"
    except Exception as e:
        return False, f"Render API 연결 실패: {e}"


def _wait_for_recovery(check_fn, max_wait_sec: int = 300, interval: int = 20) -> bool:
    """서비스가 살아날 때까지 대기 (최대 N초)"""
    waited = 0
    while waited < max_wait_sec:
        time.sleep(interval)
        waited += interval
        healthy, _, _ = check_fn()
        if healthy:
            return True
    return False


def handle_incident(service_key: str, render_id: str, service_name: str,
                    check_fn, error_msg: str) -> dict:
    """
    장애 감지 → 자동 복구 시도 → 결과 반환
    Returns: {resolved, minutes, method, attempts}
    """
    from notify import notify_incident_detected, notify_incident_fixed, notify_incident_failed

    detected_at = datetime.now(timezone.utc)
    detected_str = detected_at.strftime("%H:%M KST")

    # 1. 즉시 알림
    notify_incident_detected(service_name, error_msg, detected_str)

    max_attempts = 3
    resolved = False
    last_error = error_msg

    for attempt in range(1, max_attempts + 1):
        # 2. Render 재배포 시도
        success, msg = _render_redeploy(render_id)
        method_desc = msg

        if not success:
            # API 키 없거나 실패 → 바로 에스컬레이션
            _log_incident(service_key, detected_at, None, False, method_desc, attempt)
            notify_incident_failed(service_name, attempt, msg)
            return {"resolved": False, "minutes": 0, "method": method_desc, "attempts": attempt}

        # 3. 복구 대기 (최대 5분)
        recovered = _wait_for_recovery(check_fn, max_wait_sec=300, interval=20)

        if recovered:
            fixed_at = datetime.now(timezone.utc)
            minutes = int((fixed_at - detected_at).total_seconds() / 60)
            fixed_str = fixed_at.strftime("%H:%M KST")
            method = f"Render 자동 재배포 (시도 {attempt}회)"
            _log_incident(service_key, detected_at, fixed_at, True, method, attempt)
            notify_incident_fixed(service_name, detected_str, fixed_str, minutes, method)
            resolved = True
            break
        else:
            last_error = f"재배포 {attempt}회 시도했지만 복구 안 됨"

    if not resolved:
        _log_incident(service_key, detected_at, None, False, last_error, max_attempts)
        notify_incident_failed(service_name, max_attempts, last_error)

    return {"resolved": resolved, "method": method_desc, "attempts": max_attempts}


def _log_incident(service_key: str, detected_at, fixed_at, resolved: bool,
                  method: str, attempts: int) -> None:
    """인시던트 로그 저장"""
    incidents = []
    if INCIDENT_LOG.exists():
        try:
            incidents = json.loads(INCIDENT_LOG.read_text())
        except Exception:
            incidents = []
    incidents.append({
        "service":     service_key,
        "detected_at": detected_at.isoformat() if detected_at else None,
        "fixed_at":    fixed_at.isoformat()    if fixed_at    else None,
        "resolved":    resolved,
        "method":      method,
        "attempts":    attempts,
    })
    # 최근 100개만 보관
    INCIDENT_LOG.write_text(json.dumps(incidents[-100:], indent=2, ensure_ascii=False))


def count_incidents_today() -> int:
    """오늘 발생한 인시던트 수"""
    if not INCIDENT_LOG.exists():
        return 0
    try:
        incidents = json.loads(INCIDENT_LOG.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(
            1 for i in incidents
            if i.get("detected_at", "").startswith(today)
        )
    except Exception:
        return 0
