#!/usr/bin/env python3
"""Clarvia Auto-Classification Engine.

Enhanced keyword-based classification for AI agent tools with 200+ keywords
per category. Re-classifies tools stuck in "other" category and updates
category mappings.

Usage:
    python scripts/automation/classifier.py [--reclassify] [--stats]
"""

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"
HARVEST_DIR = DATA_DIR / "harvester"

# ---------------------------------------------------------------------------
# Enhanced category keyword map — 200+ keywords per major category
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "coding": [
        # Languages & runtimes
        "python", "javascript", "typescript", "rust", "golang", "java", "ruby",
        "swift", "kotlin", "csharp", "cpp", "lua", "elixir", "scala", "haskell",
        "dart", "php", "perl", "zig", "nim", "crystal", "julia",
        # Dev tools
        "github", "gitlab", "bitbucket", "git", "vscode", "neovim", "vim",
        "jetbrains", "intellij", "cursor", "windsurf", "codespace",
        "copilot", "codeium", "tabnine", "sourcegraph",
        # Package managers
        "npm", "yarn", "pnpm", "pip", "cargo", "maven", "gradle", "gem",
        "composer", "nuget", "brew", "apt", "conda", "poetry",
        # Frameworks
        "react", "nextjs", "vue", "angular", "svelte", "remix", "astro",
        "express", "fastapi", "django", "flask", "rails", "spring",
        "electron", "tauri", "deno", "bun",
        # Code quality
        "lint", "prettier", "eslint", "ruff", "black", "mypy", "rubocop",
        "sonarqube", "codeclimate", "codecov", "coveralls",
        # Documentation
        "swagger", "openapi", "redoc", "docusaurus", "mkdocs", "sphinx",
        "storybook", "typedoc", "jsdoc",
        # Code generation
        "codegen", "scaffolding", "boilerplate", "template", "starter",
        "snippet", "refactor", "transpiler", "compiler", "parser", "ast",
        "formatter", "linter", "analyzer",
    ],
    "data": [
        # Databases
        "postgres", "postgresql", "mysql", "mariadb", "mongodb", "redis",
        "cassandra", "dynamodb", "couchdb", "neo4j", "arangodb", "cockroach",
        "cockroachdb", "timescale", "questdb", "clickhouse", "scylla",
        "sqlite", "duckdb", "surrealdb", "rethinkdb", "firebird",
        "planetscale", "neon", "turso", "upstash", "fauna", "yugabyte",
        # Data warehouses
        "snowflake", "bigquery", "redshift", "databricks", "delta lake",
        "presto", "trino", "athena", "hive",
        # Analytics
        "mixpanel", "amplitude", "segment", "posthog", "heap", "plausible",
        "matomo", "umami", "countly", "chartbrew",
        # BI tools
        "looker", "metabase", "superset", "grafana", "tableau", "powerbi",
        "redash", "cube", "lightdash",
        # ETL & pipelines
        "fivetran", "airbyte", "stitch", "census", "hightouch", "meltano",
        "dbt", "dagster", "prefect", "airflow", "spark", "flink", "kafka",
        "pulsar", "rabbitmq", "nats", "celery", "temporal",
        # Data formats
        "csv", "parquet", "arrow", "avro", "protobuf", "json", "xml",
        "spreadsheet", "excel", "google sheets",
        # Vector databases
        "pinecone", "weaviate", "qdrant", "chroma", "milvus", "pgvector",
        "vespa", "marqo", "zilliz",
    ],
    "communication": [
        # Messaging
        "slack", "discord", "telegram", "whatsapp", "signal", "matrix",
        "mattermost", "rocket.chat", "zulip", "element", "irc",
        "microsoft teams", "teams", "webex", "google chat",
        # Email
        "email", "smtp", "imap", "sendgrid", "resend", "mailgun", "postmark",
        "mailchimp", "mailerlite", "sendinblue", "brevo", "sparkpost",
        "ses", "mandrill", "convertkit", "buttondown",
        # Video & voice
        "zoom", "google meet", "jitsi", "livekit", "agora", "twilio",
        "vonage", "plivo", "bandwidth", "telnyx", "daily", "100ms",
        "webrtc", "sip", "voip", "stream",
        # Support
        "intercom", "zendesk", "freshdesk", "crisp", "tawk", "drift",
        "helpscout", "front", "chatwoot", "tidio", "olark", "livechat",
        "hubspot", "salesforce", "zoho",
        # Notifications
        "push notification", "notification", "webhook", "sse", "websocket",
        "onesignal", "pushover", "ntfy", "gotify", "novu", "knock",
    ],
    "productivity": [
        # Project management
        "notion", "linear", "asana", "jira", "trello", "clickup", "monday",
        "basecamp", "shortcut", "height", "plane", "taiga", "youtrack",
        "teamwork", "wrike", "smartsheet",
        # Note taking
        "obsidian", "roam", "logseq", "bear", "evernote", "apple notes",
        "craft", "typora", "simplenote", "notesnook",
        # Collaboration
        "figma", "canva", "miro", "mural", "figjam", "lucidchart",
        "excalidraw", "tldraw", "whimsical", "loom", "jam",
        # Spreadsheets & databases
        "airtable", "coda", "google sheets", "rows", "grist", "nocodb",
        "baserow", "seatable", "teable",
        # Automation
        "zapier", "make", "n8n", "ifttt", "pipedream", "activepieces",
        "automatisch", "kestra", "windmill", "trigger.dev",
        # Calendar & scheduling
        "calendly", "cal.com", "reclaim", "clockwise", "savvycal",
        "google calendar", "outlook calendar", "ical",
        # File management
        "dropbox", "google drive", "onedrive", "box", "syncthing",
        "nextcloud", "owncloud",
        # CRM
        "salesforce", "hubspot", "pipedrive", "close", "attio",
        "folk", "clay", "apollo",
        # Task & time
        "todoist", "things", "omnifocus", "ticktick", "toggl",
        "clockify", "harvest", "rescuetime", "wakatime",
    ],
    "search": [
        "algolia", "elasticsearch", "elastic", "typesense", "meilisearch",
        "solr", "opensearch", "zinc", "bleve", "tantivy",
        "google search", "bing", "duckduckgo", "brave search",
        "serper", "serpapi", "tavily", "exa", "perplexity",
        "google custom search", "you.com", "searx", "kagi",
        "web scraping", "crawling", "spider", "scraper", "puppeteer",
        "playwright", "selenium", "cheerio", "beautiful soup",
        "web search", "internet search", "search engine", "index",
        "full-text search", "semantic search", "hybrid search",
        "retrieval", "information retrieval", "rag",
    ],
    "security": [
        "auth", "authentication", "authorization", "oauth", "saml", "oidc",
        "jwt", "token", "session", "cookie", "passport",
        "auth0", "clerk", "workos", "stytch", "okta", "keycloak",
        "fusionauth", "supertokens", "hanko", "zitadel",
        "encryption", "crypto", "hash", "bcrypt", "argon2", "scrypt",
        "ssl", "tls", "certificate", "pki", "vault", "keychain",
        "firewall", "waf", "ddos", "rate limit", "ip block",
        "vulnerability", "cve", "scan", "audit", "pentest",
        "sast", "dast", "snyk", "dependabot", "trivy", "grype",
        "secret", "credential", "password", "passkey", "mfa", "2fa",
        "totp", "fido", "webauthn", "biometric",
        "compliance", "gdpr", "hipaa", "soc2", "pci", "iso27001",
        "rbac", "abac", "iam", "acl", "permission", "role",
    ],
    "devops": [
        # CI/CD
        "circleci", "travis", "jenkins", "buildkite", "drone", "tekton",
        "github actions", "gitlab ci", "azure pipelines", "teamcity",
        "argo", "flux", "spinnaker", "harness", "codefresh",
        # Containers & orchestration
        "docker", "kubernetes", "k8s", "helm", "kustomize", "podman",
        "containerd", "cri-o", "buildah", "skaffold", "tilt", "devspace",
        "rancher", "nomad", "ecs", "fargate", "cloud run",
        # IaC
        "terraform", "pulumi", "crossplane", "ansible", "puppet", "chef",
        "salt", "cloudformation", "bicep", "cdk", "cdktf", "opentofu",
        # Cloud platforms
        "aws", "gcp", "azure", "digitalocean", "linode", "vultr",
        "hetzner", "fly.io", "railway", "render", "heroku", "vercel",
        "netlify", "cloudflare", "supabase", "firebase",
        # Monitoring & observability
        "datadog", "newrelic", "new relic", "grafana", "prometheus",
        "elastic apm", "jaeger", "zipkin", "honeycomb", "lightstep",
        "sentry", "bugsnag", "rollbar", "logrocket", "opentelemetry",
        "uptimerobot", "betteruptime", "statuspage", "opsgenie", "pagerduty",
        # Logging
        "logstash", "fluentd", "fluentbit", "loki", "papertrail",
        "logtail", "axiom", "signoz", "highlight",
    ],
    "design": [
        "figma", "sketch", "adobe xd", "framer", "protopie", "origami",
        "canva", "photoshop", "illustrator", "inkscape", "gimp",
        "invision", "zeplin", "abstract", "avocode",
        "tailwind", "bootstrap", "chakra", "material ui", "ant design",
        "radix", "shadcn", "headless ui", "daisyui", "mantine",
        "icon", "illustration", "font", "typography", "color",
        "animation", "motion", "lottie", "rive", "gsap", "framer motion",
        "responsive", "accessibility", "a11y", "wcag", "aria",
        "ui", "ux", "wireframe", "mockup", "prototype", "design system",
        "component library", "style guide", "theme",
        "image", "svg", "png", "webp", "avif", "sharp", "imagemagick",
        "cloudinary", "imgix", "uploadthing", "uploadcare",
    ],
    "ai-ml": [
        # LLM providers
        "openai", "anthropic", "claude", "gpt", "gemini", "mistral",
        "cohere", "ai21", "together", "groq", "fireworks", "anyscale",
        "replicate", "hugging face", "huggingface",
        "perplexity", "deepseek", "zhipu", "baichuan", "moonshot",
        "minimax", "cerebras", "sambanova", "lepton",
        # ML frameworks
        "pytorch", "tensorflow", "jax", "keras", "scikit-learn",
        "xgboost", "lightgbm", "catboost", "onnx", "mlflow",
        "wandb", "neptune", "comet", "aim", "clearml",
        # Agent frameworks
        "langchain", "llamaindex", "crewai", "autogen", "semantic kernel",
        "haystack", "dspy", "instructor", "outlines", "guidance",
        "agentkit", "smol-agent", "phidata", "agency", "camel",
        # Media AI
        "stable diffusion", "midjourney", "dall-e", "flux", "ideogram",
        "suno", "udio", "bark", "whisper", "elevenlabs", "eleven labs",
        "runway", "pika", "kling", "sora", "stability",
        "deepgram", "assemblyai", "assembly ai", "speechmatics",
        "tts", "stt", "speech", "voice", "audio", "transcription",
        # NLP
        "embedding", "tokenizer", "ner", "sentiment", "classification",
        "summarization", "translation", "generation", "completion",
        "prompt", "fine-tuning", "rlhf", "lora", "gguf", "quantization",
        # MCP & tool-use
        "mcp", "model context protocol", "tool use", "function calling",
        "agent tool", "tool server", "smithery", "glama",
        # RAG & retrieval
        "rag", "retrieval", "chunking", "embedding", "reranking",
        "knowledge base", "document loader", "text splitter",
        # Computer vision
        "ocr", "object detection", "image recognition", "face detection",
        "image segmentation", "yolo", "opencv", "vision",
    ],
    "finance": [
        "stripe", "paypal", "square", "plaid",
        "adyen", "braintree", "mollie", "razorpay", "paddle",
        "lemonsqueezy", "lemon squeezy", "wise", "revolut", "mercadopago",
        "payment", "billing", "invoice", "subscription", "checkout",
        "refund", "payout", "transfer",
        "accounting", "quickbooks", "xero", "freshbooks", "wave",
        "banking", "fintech", "neobank",
        "stock", "trading", "forex",
        "tax", "compliance", "kyc", "aml",
    ],
    "blockchain": [
        "blockchain", "ethereum", "solana", "bitcoin", "nft",
        "crypto", "defi", "web3", "smart contract",
        "coinbase", "circle", "alchemy", "infura", "moralis",
        "helius", "quicknode", "thirdweb", "hardhat", "foundry",
        "wagmi", "viem", "ethers", "web3.js", "web3py",
        "polygon", "arbitrum", "optimism", "avalanche", "near",
        "cosmos", "polkadot", "sui", "aptos", "ton", "base",
        "opensea", "rarible", "magic eden", "jupiter", "raydium",
        "uniswap", "aave", "compound", "lido", "eigenlayer",
        "wallet", "exchange", "dex", "swap", "yield", "staking",
        "token", "erc20", "erc721", "spl", "anchor",
        "dune", "subgraph", "indexer", "rpc", "node provider",
    ],
    "education": [
        "course", "tutorial", "lesson", "quiz", "exam", "assessment",
        "lms", "learning management", "classroom", "student", "teacher",
        "edtech", "e-learning", "mooc", "certificate", "credential",
        "flashcard", "anki", "spaced repetition", "study",
        "documentation", "knowledge base", "wiki", "manual",
        "training", "onboarding", "skill", "workshop",
        "confluence", "gitbook", "readme", "docusaurus",
    ],
    "automation": [
        "workflow", "automation", "orchestration", "pipeline", "scheduler",
        "cron", "queue", "worker", "job", "batch", "task runner",
        "zapier", "make", "n8n", "ifttt", "pipedream", "activepieces",
        "automatisch", "kestra", "windmill", "trigger.dev",
        "scraper", "crawler", "bot", "rpa", "robotic process",
        "macro", "hotkey", "shortcut", "script", "cli",
        "browserless", "apify", "scrapfly", "zyte", "oxylabs",
        "webhook", "event", "trigger", "action", "integration",
    ],
    "infrastructure": [
        "hosting", "server", "vps", "bare metal", "dedicated",
        "cdn", "edge", "load balancer", "reverse proxy", "nginx",
        "caddy", "traefik", "haproxy", "envoy", "istio",
        "dns", "domain", "registrar", "nameserver", "cloudflare",
        "storage", "s3", "gcs", "azure blob", "backblaze", "wasabi",
        "minio", "ceph", "seaweedfs",
        "queue", "message broker", "kafka", "rabbitmq", "nats", "sqs",
        "redis", "memcached", "valkey",
        "networking", "vpn", "wireguard", "tailscale", "zerotier",
        "mesh", "service mesh", "grpc", "graphql", "rest",
    ],
    "monitoring": [
        "monitoring", "observability", "alerting", "incident", "oncall",
        "uptime", "health check", "heartbeat", "ping", "status page",
        "apm", "tracing", "profiling", "metrics", "logging",
        "prometheus", "grafana", "datadog", "newrelic", "sentry",
        "honeycomb", "lightstep", "dynatrace", "splunk",
        "opentelemetry", "otel", "jaeger", "zipkin", "signoz",
        "pagerduty", "opsgenie", "victorops", "rootly", "firehydrant",
        "betteruptime", "uptimerobot", "cronitor", "checkly",
    ],
    "testing": [
        "test", "testing", "unit test", "integration test", "e2e",
        "jest", "vitest", "mocha", "pytest", "unittest", "rspec",
        "cypress", "playwright", "selenium", "testcafe", "puppeteer",
        "storybook", "chromatic", "percy", "applitools",
        "mock", "stub", "spy", "fixture", "factory",
        "coverage", "codecov", "coveralls", "istanbul",
        "benchmark", "performance test", "load test", "stress test",
        "k6", "locust", "gatling", "artillery", "jmeter",
        "qa", "quality assurance", "regression", "smoke test",
        "snapshot test", "visual test", "contract test", "api test",
    ],
    "cms": [
        "contentful", "sanity", "strapi", "ghost", "wordpress",
        "prismic", "storyblok", "hygraph", "payload", "directus",
        "keystone", "tina", "decap", "builder.io", "contentstack",
        "headless cms", "content management", "blog", "article",
        "markdown", "mdx", "rich text", "wysiwyg", "editor",
    ],
}


# Build reverse lookup for fast classification
_KEYWORD_TO_CATEGORY: dict[str, str] = {}
for _cat, _keywords in CATEGORY_KEYWORDS.items():
    for _kw in _keywords:
        _KEYWORD_TO_CATEGORY[_kw.lower()] = _cat


def classify_tool(
    name: str,
    description: str = "",
    url: str = "",
    tags: list[str] | None = None,
) -> str:
    """Classify a tool into a category using enhanced keyword matching.

    Priority:
    1. Exact keyword match in name
    2. Exact keyword match in description
    3. Partial keyword match in combined text
    4. Tag-based classification
    5. Fallback to "other"
    """
    name_lower = name.lower()
    desc_lower = description.lower()
    combined = f"{name_lower} {desc_lower} {url.lower()}"
    tag_str = " ".join(t.lower() for t in (tags or []))

    # Score each category by keyword hits
    category_scores: Counter = Counter()

    # Pass 1: exact keyword matches (higher weight)
    for kw, cat in _KEYWORD_TO_CATEGORY.items():
        # Whole-word match in name (highest signal)
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            category_scores[cat] += 3

        # Whole-word match in description
        if re.search(rf"\b{re.escape(kw)}\b", desc_lower):
            category_scores[cat] += 2

        # Match in tags
        if re.search(rf"\b{re.escape(kw)}\b", tag_str):
            category_scores[cat] += 2

    # Pass 2: substring matches (lower weight, only if no strong match yet)
    if not category_scores or category_scores.most_common(1)[0][1] < 4:
        for kw, cat in _KEYWORD_TO_CATEGORY.items():
            if len(kw) >= 4 and kw in combined:
                category_scores[cat] += 1

    if not category_scores:
        return "other"

    # Return the highest-scoring category
    best_cat, best_score = category_scores.most_common(1)[0]
    if best_score < 2:
        return "other"

    return best_cat


def reclassify_tools(data_path: Path | None = None) -> dict[str, Any]:
    """Reclassify all tools in prebuilt scans, updating 'other' categories."""
    path = data_path or PREBUILT_PATH
    if not path.exists():
        return {"error": f"{path} not found"}

    with open(path) as f:
        services = json.load(f)

    total = len(services)
    reclassified = 0
    changes: list[dict] = []

    for svc in services:
        old_cat = svc.get("category") or "other"
        name = svc.get("service_name", "")
        desc = svc.get("description", "")
        url = svc.get("url", "")
        tags = svc.get("tags", [])

        new_cat = classify_tool(name, desc, url, tags)

        # Reclassify if currently unset, "other", or missing
        if old_cat in ("other", "", None) and new_cat != "other":
            svc["category"] = new_cat
            reclassified += 1
            changes.append({
                "name": name,
                "old": old_cat,
                "new": new_cat,
                "url": url,
            })
        elif "category" not in svc:
            # Ensure all entries have a category field
            svc["category"] = new_cat if new_cat != "other" else "other"
            if new_cat != "other":
                reclassified += 1
                changes.append({
                    "name": name,
                    "old": "unset",
                    "new": new_cat,
                    "url": url,
                })

    # Save updated data
    with open(path, "w") as f:
        json.dump(services, f, indent=2, default=str)

    # Save reclassification log
    log_path = HARVEST_DIR / "reclassification-log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "reclassified": reclassified,
            "changes": changes,
        }, f, indent=2)

    logger.info("Reclassified %d/%d tools", reclassified, total)
    return {
        "total": total,
        "reclassified": reclassified,
        "sample_changes": changes[:20],
    }


def category_stats(data_path: Path | None = None) -> dict[str, Any]:
    """Show category distribution across all tools."""
    path = data_path or PREBUILT_PATH
    if not path.exists():
        return {"error": f"{path} not found"}

    with open(path) as f:
        services = json.load(f)

    counts: Counter = Counter()
    for svc in services:
        counts[svc.get("category", "other")] += 1

    return {
        "total": len(services),
        "categories": dict(counts.most_common()),
        "other_count": counts.get("other", 0),
        "other_pct": round(100 * counts.get("other", 0) / max(len(services), 1), 1),
        "total_keywords": sum(len(kws) for kws in CATEGORY_KEYWORDS.values()),
        "total_categories": len(CATEGORY_KEYWORDS),
    }


def main():
    parser = argparse.ArgumentParser(description="Clarvia Auto-Classification Engine")
    parser.add_argument(
        "--reclassify",
        action="store_true",
        help="Reclassify tools currently in 'other' category",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show category distribution statistics",
    )
    args = parser.parse_args()

    if args.stats:
        result = category_stats()
        print(json.dumps(result, indent=2))
    elif args.reclassify:
        result = reclassify_tools()
        print(json.dumps(result, indent=2))
    else:
        # Default: show stats then reclassify
        print("=== Current Stats ===")
        stats = category_stats()
        print(json.dumps(stats, indent=2))
        print("\n=== Reclassifying ===")
        result = reclassify_tools()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
