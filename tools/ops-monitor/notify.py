"""
Telegram 알림 — 유치원생 설명 스타일
"""
import json
import urllib.parse
import urllib.request
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT


def _send(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=data, method="POST"), timeout=10
        ) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:
        print(f"Telegram 전송 실패: {e}")
        return False


# ── 트렌드 이모지 ──────────────────────────────────────────
def trend_emoji(pct: float) -> str:
    if pct is None:
        return "➡️"
    if pct >= 10:   return "🚀"
    if pct >= 3:    return "📈"
    if pct >= 0:    return "➡️"
    if pct >= -5:   return "📉"
    return "⚠️"


def trend_text(pct: float, unit: str = "") -> str:
    if pct is None:
        return "첫 측정이에요"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%{unit}"


# ── 인시던트 알림 ──────────────────────────────────────────
def notify_incident_detected(service_name: str, error: str, timestamp: str) -> None:
    _send(
        f"🚨 <b>앗! 가게 문이 잠겼어요!</b>\n\n"
        f"<b>{service_name}</b> 가게가 갑자기 문을 닫았어요.\n"
        f"로봇 선생님이 지금 달려가고 있어요! 🏃\n\n"
        f"🕐 감지 시각: {timestamp}\n"
        f"💬 이유: {error[:150]}"
    )


def notify_incident_fixed(service_name: str, detected: str, fixed: str,
                          minutes: int, method: str) -> None:
    _send(
        f"✅ <b>가게 문이 다시 열렸어요!</b>\n\n"
        f"<b>{service_name}</b> 이제 다시 잘 돌아가고 있어요.\n"
        f"로봇 선생님 덕분에 {minutes}분 만에 고쳤답니다 🔧\n\n"
        f"🕐 닫혔던 시각: {detected}\n"
        f"🕐 다시 열린 시각: {fixed}\n"
        f"🛠 어떻게 고쳤나요: {method}\n"
        f"👤 사람이 직접 해야 할 일: 없어요!"
    )


def notify_incident_failed(service_name: str, attempts: int, error: str) -> None:
    _send(
        f"😰 <b>선생님도 못 고쳤어요. 도움이 필요해요!</b>\n\n"
        f"<b>{service_name}</b> 가게를 {attempts}번이나 고치려 했는데\n"
        f"아직도 문이 열리지 않아요. 직접 봐주세요! 🙏\n\n"
        f"💬 에러: {error[:200]}"
    )


def notify_build_failure(service_name: str, error_lines: list) -> None:
    err_text = "\n".join(f"  {l}" for l in error_lines[:5])
    _send(
        f"🔴 <b>레고 블록을 잘못 쌓았어요!</b>\n\n"
        f"<b>{service_name}</b> 빌드가 실패했어요.\n"
        f"코드에 문제가 있는 것 같아요 🧩\n\n"
        f"<b>에러 내용:</b>\n<code>{err_text}</code>"
    )


# ── 아침 브리핑 ────────────────────────────────────────────
def send_morning_briefing(sections: list) -> None:
    from datetime import datetime
    date = datetime.now().strftime("%Y-%m-%d")
    msg = f"☀️ <b>좋은 아침이에요! {date} 브리핑</b>\n\n"
    msg += "\n".join(sections)
    msg += "\n\n<i>💡 로봇 선생님이 밤새 지켜봤어요. 오늘도 화이팅! 🌟</i>"
    _send(msg)


def send_evening_summary(sections: list, incidents_today: int) -> None:
    from datetime import datetime
    date = datetime.now().strftime("%Y-%m-%d")
    incident_msg = (
        f"오늘 사고 없이 하루 잘 마쳤어요 🎉" if incidents_today == 0
        else f"오늘 가게 문 닫힌 일이 {incidents_today}번 있었어요 (모두 자동으로 고쳤어요)"
    )
    msg = f"🌙 <b>저녁 정리 {date}</b>\n\n"
    msg += f"{incident_msg}\n\n"
    msg += "\n".join(sections)
    _send(msg)


# ── 섹션 빌더 ────────────────────────────────────────────
def build_clarvia_section(kpi: dict, prev_kpi: dict | None) -> str:
    """완성 프로젝트 — 마케팅 KPI 섹션"""
    tool_count    = kpi.get("tool_count", 0)
    npm_dl        = kpi.get("npm_downloads_7d", 0)
    response_ms   = kpi.get("response_ms", 0)
    data_age_h    = kpi.get("data_age_hours", 0)
    is_healthy    = kpi.get("healthy", False)

    # 트렌드 계산
    npm_pct       = _calc_pct(npm_dl,      prev_kpi, "npm_downloads_7d")  if prev_kpi else None
    tool_pct      = _calc_pct(tool_count,  prev_kpi, "tool_count")        if prev_kpi else None
    speed_pct     = _calc_pct(response_ms, prev_kpi, "response_ms", invert=True) if prev_kpi else None

    health_icon = "✅" if is_healthy else "🔴"

    lines = [
        f"━━ 📚 <b>CLARVIA</b> (완성 75%) ━━",
        f"{health_icon} 가게 상태: {'활짝 열려있어요' if is_healthy else '문제가 있어요!'}",
        f"",
        f"<b>📊 마케팅 성적표</b>",
        f"📦 npm 친구들 (주간): <b>{npm_dl:,}명</b> {trend_emoji(npm_pct)} {trend_text(npm_pct)}",
        f"🗂 도서관 책 수: <b>{tool_count:,}권</b> {trend_emoji(tool_pct)} {trend_text(tool_pct)}",
        f"⚡ 대답 속도: <b>{response_ms}ms</b> {trend_emoji(speed_pct)} {'빠를수록 좋아요' if speed_pct is not None and speed_pct > 0 else ''}",
        f"🌿 데이터 신선도: <b>{data_age_h:.1f}시간 전</b> {'✅ 신선해요' if data_age_h < 12 else '⚠️ 좀 오래됐어요'}",
        f"",
        f"<b>🎯 오늘 해야 할 일</b>",
        f"→ 툴 메이커 5곳에 AEO 점수 개선 제안 보내기",
    ]
    return "\n".join(lines)


def build_auton_section(kpi: dict, prev_kpi: dict | None) -> str:
    """미완성 프로젝트 — 빌딩 현황"""
    agents     = kpi.get("total_agents", 0)
    active     = kpi.get("active_agents", 0)
    posts      = kpi.get("total_posts", 0)
    interact   = kpi.get("total_interactions", 0)
    follows    = kpi.get("total_follows", 0)
    is_healthy = kpi.get("healthy", False)

    posts_pct  = _calc_pct(posts,    prev_kpi, "total_posts")       if prev_kpi else None
    agent_pct  = _calc_pct(agents,   prev_kpi, "total_agents")      if prev_kpi else None

    health_icon = "✅" if is_healthy else "🔴"

    lines = [
        f"━━ 🤖 <b>AUTON</b> (완성 55%) ━━",
        f"{health_icon} 마을 상태: {'활발해요' if is_healthy else '마을에 문제가 있어요!'}",
        f"",
        f"<b>🏗 오늘의 마을 현황</b>",
        f"🤖 마을 로봇 수: <b>{agents}명</b> (활성: {active}명) {trend_emoji(agent_pct)} {trend_text(agent_pct)}",
        f"📝 오늘까지 쓴 글: <b>{posts}개</b> {trend_emoji(posts_pct)} {trend_text(posts_pct)}",
        f"👋 서로 반응한 횟수: <b>{interact}번</b>",
        f"👥 팔로우: <b>{follows}명</b>",
        f"",
        f"<b>🧱 집 완성까지 남은 레고</b>",
        f"① NFT 신분증 민팅 구현",
        f"② 브랜딩 완성 (컬러, 아바타)",
        f"③ 평판 엔진 실데이터 테스트",
    ]
    return "\n".join(lines)


def build_ortus_section(kpi: dict) -> str:
    """미완성 프로젝트 — 빌딩 현황"""
    is_healthy = kpi.get("healthy", False)
    health_icon = "✅" if is_healthy else "🔴"

    lines = [
        f"━━ 🪙 <b>ORTUS</b> (완성 50%) ━━",
        f"{health_icon} 발사대 상태: {'준비 중' if is_healthy else '문제 발생!'}",
        f"",
        f"<b>🧱 발사까지 남은 레고</b>",
        f"① Helius API 키 교체 (지금 바로 가능 — 수동 필요)",
        f"② Solana devnet 배포 (키 교체 후 바로 가능)",
        f"③ E2E 테스트 통과 확인",
        f"",
        f"💬 오톤이 마을을 만들면 발사 준비 완료!",
    ]
    return "\n".join(lines)


def build_merx_section() -> str:
    """대기 중 프로젝트"""
    lines = [
        f"━━ 💹 <b>MERX</b> (완성 25%) ━━",
        f"⏸️ 지금은 자는 중이에요",
        f"",
        f"오톤 마을이 활발해지고 오르투스 발사대가 날아오르면",
        f"그때 MERX가 깨어나요 🌙",
        f"예상 수익 시작: 12-18개월 후",
    ]
    return "\n".join(lines)


def build_health_summary(service_statuses: dict) -> str:
    """전체 점검 요약"""
    total = len(service_statuses)
    ok    = sum(1 for v in service_statuses.values() if v)
    lines = [
        f"━━ 🏥 <b>전체 건강 점검</b> ━━",
        f"가게 상태: {ok}/{total}개 정상",
    ]
    for svc, healthy in service_statuses.items():
        icon = "✅" if healthy else "🔴"
        name = f"{icon} {svc}"
        lines.append(name)
    return "\n".join(lines)


# ── 내부 유틸 ────────────────────────────────────────────
def _calc_pct(current: float, prev: dict, key: str, invert: bool = False) -> float | None:
    if prev is None:
        return None
    old = prev.get(key)
    if old is None or old == 0:
        return None
    pct = (current - old) / old * 100
    return -pct if invert else pct
