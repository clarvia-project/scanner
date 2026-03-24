"""Intent expansion synonym dictionary for Clarvia recommendation engine.

Maps user intents (English + Korean) to expanded search terms.
"""

# Action/concept -> expanded search terms
INTENT_SYNONYMS: dict[str, list[str]] = {
    # --- Development workflow ---
    "code review": ["pull request", "pr", "lint", "static analysis", "code quality", "review"],
    "deploy": ["deployment", "ci/cd", "hosting", "publish", "release", "ship"],
    "ci cd": ["continuous integration", "continuous deployment", "pipeline", "build", "github actions"],
    "test": ["testing", "unit test", "e2e", "integration test", "qa", "coverage"],
    "debug": ["debugging", "troubleshoot", "error", "trace", "logging"],
    "refactor": ["refactoring", "code cleanup", "restructure", "modernize"],
    "scaffold": ["boilerplate", "template", "starter", "init", "bootstrap"],
    "version control": ["git", "github", "gitlab", "branch", "merge", "commit"],

    # --- Infrastructure ---
    "monitor": ["monitoring", "observability", "alerting", "logging", "metrics", "uptime"],
    "database": ["sql", "postgres", "mysql", "mongodb", "db", "data store", "sqlite", "redis"],
    "cache": ["caching", "redis", "memcached", "cdn", "edge"],
    "queue": ["message queue", "rabbitmq", "kafka", "pubsub", "event"],
    "container": ["docker", "kubernetes", "k8s", "orchestration", "container"],
    "serverless": ["lambda", "function", "edge function", "worker", "cloudflare workers"],
    "storage": ["s3", "blob", "upload", "file storage", "drive", "bucket"],

    # --- Communication ---
    "email": ["smtp", "mail", "sendgrid", "resend", "ses", "notification"],
    "chat": ["messaging", "slack", "discord", "communication", "teams"],
    "notification": ["push", "alert", "webhook", "notify", "sms", "twilio"],
    "video": ["video call", "meeting", "webrtc", "zoom", "conference"],

    # --- Data ---
    "analytics": ["analytics", "tracking", "metrics", "mixpanel", "amplitude", "segment"],
    "scraping": ["web scraping", "crawl", "spider", "extract", "parse"],
    "etl": ["data pipeline", "transform", "load", "sync", "migration"],
    "search": ["full-text search", "elasticsearch", "algolia", "index", "vector search"],
    "visualization": ["chart", "graph", "dashboard", "plot", "report"],

    # --- Security & Auth ---
    "auth": ["authentication", "oauth", "login", "sso", "identity", "jwt", "session"],
    "security": ["vulnerability", "scan", "audit", "pentest", "secret", "encryption"],
    "secret": ["secret management", "vault", "env", "credential", "key management"],

    # --- AI / ML ---
    "llm": ["large language model", "gpt", "claude", "openai", "anthropic", "ai"],
    "rag": ["retrieval augmented generation", "embedding", "vector", "knowledge base"],
    "image generation": ["dall-e", "stable diffusion", "midjourney", "image ai"],
    "transcription": ["speech to text", "whisper", "audio", "voice"],
    "embedding": ["vector", "similarity", "semantic search", "pinecone", "weaviate"],

    # --- Payments & Business ---
    "payment": ["billing", "stripe", "invoice", "checkout", "subscription"],
    "crm": ["customer", "hubspot", "salesforce", "contact", "lead"],
    "project management": ["task", "issue", "kanban", "sprint", "jira", "linear", "asana"],
    "documentation": ["docs", "wiki", "readme", "knowledge base", "confluence", "notion"],

    # --- Frontend ---
    "ui": ["user interface", "component", "design system", "figma", "storybook"],
    "form": ["form builder", "validation", "input", "survey", "typeform"],
    "cms": ["content management", "headless cms", "strapi", "sanity", "contentful"],

    # --- Blockchain ---
    "blockchain": ["web3", "crypto", "defi", "smart contract", "solidity"],
    "nft": ["token", "mint", "marketplace", "opensea"],
    "wallet": ["metamask", "phantom", "web3 wallet", "connect wallet"],

    # --- Korean -> English mappings ---
    "코드 리뷰": ["code review", "pull request", "pr review"],
    "배포": ["deploy", "deployment", "hosting", "ci/cd"],
    "모니터링": ["monitoring", "alerting", "observability"],
    "데이터베이스": ["database", "sql", "db", "postgres"],
    "결제": ["payment", "billing", "stripe", "checkout"],
    "인증": ["auth", "authentication", "login", "oauth"],
    "이메일": ["email", "mail", "sendgrid", "smtp"],
    "알림": ["notification", "push", "alert", "webhook"],
    "검색": ["search", "full-text search", "elasticsearch"],
    "분석": ["analytics", "tracking", "metrics", "data analysis"],
    "채팅": ["chat", "messaging", "slack", "discord"],
    "파일": ["file", "storage", "upload", "s3"],
    "보안": ["security", "vulnerability", "audit", "encryption"],
    "테스트": ["test", "testing", "qa", "e2e"],
    "디버깅": ["debug", "debugging", "troubleshoot", "error"],
    "자동화": ["automation", "workflow", "automate", "pipeline"],
    "문서화": ["documentation", "docs", "wiki", "readme"],
    "스크래핑": ["scraping", "crawl", "extract", "parse"],
    "시각화": ["visualization", "chart", "graph", "dashboard"],
    "번역": ["translation", "i18n", "internationalization", "localize"],
    "프로젝트 관리": ["project management", "task", "issue", "kanban"],
    "블록체인": ["blockchain", "web3", "crypto", "defi"],
}

# Flatten for quick lookup: term -> list of expanded terms
_FLAT_LOOKUP: dict[str, list[str]] = {}
for _key, _expansions in INTENT_SYNONYMS.items():
    _terms = _key.lower().split()
    for _term in _terms:
        if _term not in _FLAT_LOOKUP:
            _FLAT_LOOKUP[_term] = []
        _FLAT_LOOKUP[_term].extend(_expansions)
    # Also map each expansion back
    for _exp in _expansions:
        _exp_lower = _exp.lower()
        if _exp_lower not in _FLAT_LOOKUP:
            _FLAT_LOOKUP[_exp_lower] = []
        _FLAT_LOOKUP[_exp_lower].extend(_expansions)


def expand_intent(intent: str) -> list[str]:
    """Expand a user intent string into a broader set of search terms.

    Returns the original terms + all matched synonyms, deduplicated.
    """
    intent_lower = intent.lower().strip()
    terms = set(intent_lower.split())

    # Direct phrase match first (highest priority)
    for phrase, expansions in INTENT_SYNONYMS.items():
        if phrase.lower() in intent_lower:
            terms.update(e.lower() for e in expansions)

    # Individual word match
    for word in list(terms):
        if word in _FLAT_LOOKUP:
            terms.update(e.lower() for e in _FLAT_LOOKUP[word][:10])  # cap per word

    return sorted(terms)
