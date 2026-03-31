#!/usr/bin/env python3
"""
4개 사업 운영 모니터 — 메인 실행 파일

사용법:
  python3 run.py health     # 헬스체크 + 자동복구 (15분마다)
  python3 run.py morning    # 아침 브리핑 (08:00 KST)
  python3 run.py evening    # 저녁 요약 (22:00 KST)
  python3 run.py test       # Telegram 연결 테스트
"""
import sys
import json
from datetime import datetime, timezone

# ── 공통 임포트 ───────────────────────────────────────────
from config import SERVICES
from health import run_all_checks, check_http
from kpi    import (
    fetch_clarvia_kpi, fetch_auton_kpi, fetch_ortus_kpi, fetch_merx_kpi,
    save_snapshot, load_snapshots, get_yesterday_snapshot, get_week_ago_snapshot,
)
from notify import (
    _send,
    build_clarvia_section, build_auton_section,
    build_ortus_section, build_merx_section,
    build_health_summary,
    send_morning_briefing, send_evening_summary,
)
from remediate import handle_incident, count_incidents_today


# ── health 모드 ───────────────────────────────────────────
def run_health():
    """서비스 헬스체크 + 장애 자동복구"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 헬스체크 시작...")
    results = run_all_checks()

    for key, res in results.items():
        svc = SERVICES[key]
        if not res["healthy"] and svc["url"]:  # Background Worker 제외
            print(f"  ❌ {key} 다운 감지! 자동복구 시도...")

            # check_fn 클로저
            url, path = svc["url"], svc["health_path"] or "/health"
            def make_check(u, p):
                return lambda: check_http(u, p)
            check_fn = make_check(url, path)

            error_msg = res["body"].get("error", "응답 없음")
            handle_incident(
                service_key=key,
                render_id=svc["render_id"],
                service_name=svc["name"],
                check_fn=check_fn,
                error_msg=error_msg,
            )
        else:
            status = "✅" if res["healthy"] else "⏭ (HTTP 없음)"
            print(f"  {status} {key}: {res['ms']}ms")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 헬스체크 완료")


# ── morning 모드 ──────────────────────────────────────────
def run_morning():
    """아침 브리핑 생성 + Telegram 전송"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 아침 브리핑 생성...")
    checks = run_all_checks()

    # KPI 수집
    clarvia_health = checks.get("clarvia-api", {})
    auton_health   = checks.get("auton-backend", {})
    ortus_health   = checks.get("ortus-api", {})

    clarvia_kpi = fetch_clarvia_kpi(
        clarvia_health.get("body", {}),
        clarvia_health.get("ms", 0)
    )
    auton_kpi = fetch_auton_kpi(auton_health.get("body", {}))
    ortus_kpi = fetch_ortus_kpi(ortus_health.get("healthy", False))

    # 오늘 스냅샷 저장
    today = datetime.now().strftime("%Y-%m-%d")
    save_snapshot(today, {
        "clarvia": clarvia_kpi,
        "auton":   auton_kpi,
        "ortus":   ortus_kpi,
    })

    # 이전 스냅샷 (트렌드용)
    prev_7d = get_week_ago_snapshot()
    prev_clarvia = prev_7d.get("clarvia") if prev_7d else None
    prev_auton   = prev_7d.get("auton")   if prev_7d else None

    # 섹션 조립
    sections = [
        build_health_summary({
            svc: r["healthy"] or not SERVICES[svc]["url"]
            for svc, r in checks.items()
        }),
        "",
        build_clarvia_section(clarvia_kpi, prev_clarvia),
        "",
        build_auton_section(auton_kpi, prev_auton),
        "",
        build_ortus_section(ortus_kpi),
        "",
        build_merx_section(),
    ]

    send_morning_briefing(sections)
    print("✅ 아침 브리핑 전송 완료")


# ── evening 모드 ─────────────────────────────────────────
def run_evening():
    """저녁 요약 전송"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 저녁 요약 생성...")
    checks  = run_all_checks()
    incidents = count_incidents_today()

    clarvia_health = checks.get("clarvia-api", {})
    auton_health   = checks.get("auton-backend", {})
    ortus_health   = checks.get("ortus-api", {})

    clarvia_kpi = fetch_clarvia_kpi(
        clarvia_health.get("body", {}),
        clarvia_health.get("ms", 0)
    )
    auton_kpi = fetch_auton_kpi(auton_health.get("body", {}))

    # 오늘 vs 아침 비교 (스냅샷에서)
    today = datetime.now().strftime("%Y-%m-%d")
    snaps = load_snapshots()
    morning_snap = snaps.get(today, {})
    prev_clarvia = morning_snap.get("clarvia")
    prev_auton   = morning_snap.get("auton")

    sections = [
        build_clarvia_section(clarvia_kpi, prev_clarvia),
        "",
        build_auton_section(auton_kpi, prev_auton),
        "",
        build_ortus_section({"healthy": ortus_health.get("healthy", False)}),
    ]

    send_evening_summary(sections, incidents)
    print("✅ 저녁 요약 전송 완료")


# ── test 모드 ────────────────────────────────────────────
def run_test():
    """Telegram 연결 테스트"""
    from datetime import datetime
    ok = _send(
        f"🧪 <b>운영 모니터 연결 테스트</b>\n\n"
        f"4개 사업 모니터가 잘 연결됐어요!\n"
        f"시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Telegram 전송: {'✅ 성공' if ok else '❌ 실패'}")


# ── 진입점 ───────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "health"

    if mode == "health":
        run_health()
    elif mode == "morning":
        run_morning()
    elif mode == "evening":
        run_evening()
    elif mode == "test":
        run_test()
    else:
        print(f"알 수 없는 모드: {mode}")
        print("사용법: python3 run.py [health|morning|evening|test]")
        sys.exit(1)
