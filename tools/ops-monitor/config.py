"""
4개 사업 운영 모니터 — 설정
"""
import os

# ── Telegram ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN",
    "8290274754:AAHIbZoN8NTkeZHdc4m9BTwtnGo69uyTlC4"
)
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT", "6558975935")

# ── Render API ────────────────────────────────────────────
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
RENDER_API_BASE = "https://api.render.com/v1"

# ── 서비스 정의 ────────────────────────────────────────────
SERVICES = {
    "clarvia-api": {
        "name": "클라비아 도서관",
        "render_id": "srv-d70jf4ggjchc73fm4isg",
        "url": "https://clarvia-api.onrender.com",
        "health_path": "/health",
        "project": "clarvia",
        "status": "live",       # live = 완성, building = 미완성
    },
    "auton-backend": {
        "name": "오톤 마을 광장",
        "render_id": "srv-d74juh3uibrs73akffj0",
        "url": "https://auton-backend-api.onrender.com",
        "health_path": "/health",
        "project": "auton",
        "status": "building",
    },
    "auton-seed-agents": {
        "name": "오톤 시드 로봇들",
        "render_id": "srv-d75mhi6uk2gs73dc0ev0",
        "url": None,             # Background Worker — HTTP 없음
        "health_path": None,
        "project": "auton",
        "status": "building",
    },
    "ortus-api": {
        "name": "오르투스 발사대",
        "render_id": "srv-d74g305actks738ehirg",
        "url": "https://api.ortus.fun",
        "health_path": "/health",
        "project": "ortus",
        "status": "building",
    },
}

# ── 프로젝트 메타 ──────────────────────────────────────────
PROJECTS = {
    "clarvia": {
        "display": "CLARVIA 🔍",
        "emoji": "📚",
        "completion": 75,
        "phase": "live",        # live | building | waiting
        "next_revenue": "1-3개월",
        "build_blockers": [],   # 완성됐으므로 없음
    },
    "auton": {
        "display": "AUTON 🌐",
        "emoji": "🤖",
        "completion": 55,
        "phase": "building",
        "next_revenue": "6-12개월",
        "build_blockers": [
            "NFT 신분증 민팅 구현",
            "브랜딩 완성 (컬러, 아바타 시스템)",
            "평판 엔진 실데이터 캘리브레이션",
        ],
    },
    "ortus": {
        "display": "ORTUS 🚀",
        "emoji": "🪙",
        "completion": 50,
        "phase": "building",
        "next_revenue": "6-12개월",
        "build_blockers": [
            "Helius API 키 교체 (수동 필요)",
            "devnet 배포 (키 교체 후 바로 가능)",
            "E2E 테스트 스위트",
        ],
    },
    "merx": {
        "display": "MERX 📊",
        "emoji": "💹",
        "completion": 25,
        "phase": "waiting",
        "next_revenue": "12-18개월",
        "build_blockers": [
            "오톤 완성 대기 중",
            "오르투스 mainnet 대기 중",
        ],
    },
}

# ── KPI 스냅샷 저장 경로 ───────────────────────────────────
import pathlib
DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_FILE = DATA_DIR / "snapshots.json"
INCIDENT_LOG  = DATA_DIR / "incidents.json"
