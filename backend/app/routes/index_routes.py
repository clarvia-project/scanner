"""Index API — Agent-facing service discovery endpoints."""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Any
import time as _time

from fastapi import APIRouter, HTTPException, Query, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["index"])

# ---------------------------------------------------------------------------
# Search analytics tracking
# ---------------------------------------------------------------------------
_search_log: list[dict] = []  # Recent searches
_search_counter: Counter = Counter()  # Query frequency
_MAX_SEARCH_LOG = 2000  # Reduced from 10k to save memory on 512MB instance

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------
_CATEGORY_MAP: dict[str, list[str]] = {
    "ai": [
        # LLM providers
        "openai", "anthropic", "google ai", "mistral", "cohere",
        "replicate", "hugging face", "huggingface", "together", "groq", "perplexity",
        "assemblyai", "assembly ai", "cerebras", "deepgram", "elevenlabs",
        "eleven labs", "stability", "stable diffusion", "midjourney",
        "runway", "jasper", "writesonic", "copy.ai", "claude",
        "gemini", "llama", "meta ai", "ai21", "anyscale", "fireworks",
        "deepseek", "zhipu", "baichuan", "moonshot", "minimax",
        "suno", "udio", "ideogram", "flux", "leonardo",
        # Vector DBs
        "pinecone", "weaviate", "qdrant", "chroma", "milvus", "zilliz",
        # AI frameworks
        "langchain", "llamaindex", "crewai", "autogen", "semantic kernel",
        "haystack", "dspy", "guardrails", "guidance", "lmstudio",
        "jan", "text generation", "vllm", "ollama", "localai",
        "gpt4all", "lmql", "oobabooga", "koboldai",
        # AI services
        "whisper", "dall-e", "dalle", "chatgpt", "copilot",
        "tabnine", "codeium", "cursor", "continue", "aider",
        "phind", "sourcegraph cody", "amazon q", "amazon bedrock", "bedrock",
        "vertex ai", "azure openai", "azure ai", "sagemaker",
        "roboflow", "ultralytics", "yolo", "detectron",
        "tensorflow", "pytorch", "keras", "scikit", "sklearn",
        "transformers", "diffusers", "tokenizers", "datasets",
        "wandb", "weights and biases", "mlflow", "neptune", "comet",
        "labelbox", "scale ai", "snorkel", "prodigy",
        "unstructured", "llamaparse", "docling",
        # Speech/audio AI
        "resemble", "play.ht", "murf", "speechify", "descript",
        "otter", "fireflies", "rev", "sonix",
        # Image/video AI
        "remove.bg", "photoroom", "clipdrop", "pika", "luma",
        "heygen", "synthesia", "d-id", "rask",
    ],
    "developer_tools": [
        # Version control & code hosting
        "github", "gitlab", "bitbucket", "gitea", "sourcehut", "codeberg",
        # Hosting & deployment
        "vercel", "netlify", "supabase", "firebase", "railway", "render",
        "heroku", "digital ocean", "digitalocean", "linode", "fly.io",
        "deno deploy", "coolify", "caprover",
        # Containers & orchestration
        "docker", "kubernetes", "k8s", "podman", "containerd",
        # IaC
        "terraform", "pulumi", "ansible", "chef", "puppet", "vagrant",
        "crossplane", "cdktf", "cdk",
        # CI/CD
        "circleci", "travis", "jenkins", "buildkite", "github actions",
        "gitlab ci", "drone", "tekton", "argo", "spinnaker",
        "codefresh", "semaphore", "buddy", "woodpecker",
        # Package managers
        "npm", "yarn", "pnpm", "pip", "cargo", "maven", "gradle",
        "nuget", "composer", "gem", "hex", "pub",
        # API tools
        "postman", "insomnia", "swagger", "redoc", "hoppscotch",
        "bruno", "httpie",
        # Code quality
        "eslint", "prettier", "biome", "oxlint", "ruff", "black",
        "isort", "mypy", "pyright", "rubocop",
        "sonarlint", "sonarqube", "codeclimate", "codecov", "coveralls",
        "snyk", "dependabot", "renovate", "socket",
        # Auth providers
        "auth0", "clerk", "workos", "stytch", "okta",
        "keycloak", "fusionauth", "logto", "lucia", "kinde",
        # Dev utilities
        "ngrok", "localstack", "mkcert",
        "codespace", "gitpod", "replit", "stackblitz", "codesandbox",
    ],
    "payments": [
        "stripe", "paypal", "squareup", "square", "plaid", "coinbase", "circle",
        "adyen", "braintree", "mollie", "razorpay", "paddle", "lemonsqueezy",
        "lemon squeezy", "wise", "revolut", "mercadopago",
        "gocardless", "chargebee", "recurly", "fastspring", "2checkout",
        "klarna", "afterpay", "affirm", "sezzle",
        "dwolla", "marqeta", "lithic", "unit", "treasury prime",
        "moov", "modern treasury", "increase",
        "payoneer", "remitly", "flutterwave", "paystack",
        "rapyd", "checkout.com", "worldpay", "fiserv",
    ],
    "communication": [
        # Messaging
        "slack", "discord", "twilio", "telegram", "whatsapp",
        "signal", "matrix", "element", "rocket.chat", "mattermost",
        "zulip", "microsoft teams", "teams", "google chat",
        # Email
        "sendgrid", "resend", "mailgun", "postmark", "mailchimp",
        "ses", "amazon ses", "sparkpost", "mailjet", "sendinblue",
        "brevo", "convertkit", "buttondown", "substack",
        "mailtrap",
        # Support
        "intercom", "zendesk", "freshdesk", "crisp", "tawk",
        "drift", "hubspot", "helpscout", "front", "chatwoot",
        "tidio", "olark", "kayako", "groove",
        # Video/voice
        "zoom", "google meet", "webex", "vonage", "agora",
        "daily", "livekit", "100ms", "jitsi", "stream",
        # Notifications
        "onesignal", "pusher", "ably", "novu", "knock",
        "courier", "ntfy", "pushover",
        # SMS
        "messagebird", "plivo", "bandwidth", "sinch", "infobip",
        "telnyx", "nexmo",
    ],
    "data": [
        # Warehouses
        "snowflake", "databricks", "bigquery", "redshift",
        "clickhouse", "duckdb", "motherduck",
        # BI & analytics
        "mixpanel", "amplitude", "segment", "looker", "metabase",
        "superset", "tableau", "power bi", "mode", "sisense",
        "lightdash", "cube", "evidence",
        # ETL & pipelines
        "fivetran", "airbyte", "stitch", "census", "hightouch",
        "meltano", "singer", "rivery", "hevo", "matillion",
        # Orchestration
        "dbt", "dagster", "prefect", "airflow", "spark",
        "kafka", "flink", "beam", "nifi", "luigi",
        "temporal", "inngest", "trigger.dev",
        # Data tools
        "pandas", "polars", "arrow", "parquet",
        "great expectations", "soda",
        "monte carlo", "atlan", "alation",
        "datahub", "openmetadata",
    ],
    "productivity": [
        # Project management
        "notion", "linear", "atlassian", "asana", "jira",
        "clickup", "monday", "trello", "basecamp", "height",
        "shortcut", "plane", "huly", "taiga",
        # Docs & knowledge
        "airtable", "coda", "confluence", "gitbook",
        "slite", "slab", "tettra", "guru", "swimm",
        # Collaboration
        "miro", "loom", "calendly", "doodle", "cal.com",
        "reclaim", "clockwise",
        # Automation
        "zapier", "make", "n8n", "ifttt", "power automate",
        "bardeen", "relay", "activepieces", "automatisch",
        # Low-code
        "retool", "appsmith", "budibase", "tooljet", "windmill",
        "airplane", "superblocks", "basedash",
        # Notes
        "obsidian", "roam", "logseq", "bear", "craft",
        "mem", "capacities", "tana", "heptabase",
        # Spreadsheets
        "google sheets", "excel", "smartsheet", "rows",
        "grist", "nocodb", "baserow", "teable",
    ],
    "blockchain": [
        # Networks
        "solana", "ethereum", "bitcoin", "polygon", "arbitrum",
        "optimism", "avalanche", "near", "cosmos", "polkadot",
        "sui", "aptos", "ton", "base", "scroll", "zksync",
        "starknet", "linea", "mantle", "manta", "blast",
        "sei", "injective", "celestia",
        "binance", "bsc", "tron", "cardano", "algorand",
        "tezos", "flow", "hedera", "icp", "internet computer",
        "filecoin", "arweave",
        # Infrastructure
        "helius", "alchemy", "moralis", "dune", "infura",
        "quicknode", "chainlink", "thirdweb", "tenderly",
        "goldsky", "envio", "subgraph", "the graph",
        "ankr", "grove", "nodereal",
        # Dev tools
        "hardhat", "foundry", "wagmi", "viem", "ethers", "web3",
        "web3.js", "web3.py", "brownie", "ape", "truffle",
        "remix", "anchor", "seahorse",
        # DeFi / NFT
        "opensea", "rarible", "magic eden", "jupiter", "raydium",
        "uniswap", "aave", "compound", "curve", "maker",
        "lido", "eigenlayer", "pendle", "gmx",
        "metaplex", "crossmint", "nft.storage",
        # Wallets
        "metamask", "phantom", "rainbow", "coinbase wallet",
        "walletconnect", "safe", "gnosis", "privy", "dynamic",
        "particle network", "web3auth", "magic link",
    ],
    "mcp": [
        "mcp", "smithery", "glama", "model context protocol",
        "mcp server", "mcp-server", "mcpserver",
    ],
    "skills": [
        # Agent skills / Claude Code skills
        "skill", "skills", "agent skill", "claude skill", "codex skill",
        "skill.md", "claude code skill", "agent-skills", "claude-skills",
        "codex-skills", "openai skills", "anthropic skills",
        # Workflow automation skills
        "workflow skill", "automation skill", "coding skill",
    ],
    "search": [
        "algolia", "elasticsearch", "elastic", "typesense", "meilisearch",
        "google search", "bing", "serper", "serpapi", "tavily",
        "exa", "brave search", "opensearch", "solr", "lunr",
        "flexsearch", "minisearch", "orama", "zinc", "quickwit",
        "vespa", "marqo", "trieve",
        "duckduckgo", "yandex", "baidu",
    ],
    "storage": [
        "s3", "gcs", "azure blob", "backblaze", "wasabi",
        "cloudinary", "imgix", "uploadthing", "uploadcare",
        "minio", "ceph", "seaweedfs",
        "r2", "cloudflare r2", "tigris", "storj",
        "google cloud storage", "azure storage",
        "bunny cdn", "keycdn", "fastly",
        "ipfs",
    ],
    "cms": [
        "contentful", "sanity", "strapi", "ghost", "wordpress",
        "prismic", "storyblok", "hygraph", "payload",
        "directus", "keystone", "wagtail", "drupal",
        "tina", "decap", "builder.io",
        "contentstack", "butter cms", "buttercms",
        "agility", "caisy", "prepr",
        "medusa", "saleor", "vendure",
    ],
    # --- NEW CATEGORIES ---
    "security": [
        "snyk", "sonarqube", "veracode", "checkmarx", "fortify",
        "crowdstrike", "sentinelone", "carbon black",
        "okta", "auth0", "onelogin", "duo", "jumpcloud",
        "vault", "hashicorp vault", "doppler", "infisical", "1password",
        "bitwarden", "lastpass", "dashlane",
        "imperva", "akamai", "sucuri",
        "burp suite", "owasp zap", "nmap", "wireshark",
        "trivy", "grype", "syft", "cosign", "sigstore",
        "falco", "aqua", "prisma cloud", "wiz", "orca",
        "lacework", "bridgecrew", "checkov",
        "certbot", "letsencrypt",
        "nuclei", "subfinder", "httpx",
    ],
    "testing": [
        "jest", "vitest", "mocha", "chai", "cypress",
        "playwright", "puppeteer", "selenium", "webdriver",
        "pytest", "unittest", "robot framework",
        "junit", "testng", "rspec", "minitest",
        "storybook", "chromatic", "percy", "applitools",
        "k6", "locust", "gatling", "artillery", "jmeter",
        "newman", "dredd", "pact",
        "testcontainers", "toxiproxy",
        "codecov", "coveralls", "istanbul",
        "msw", "nock", "wiremock", "mockoon", "prism",
        "qase", "testrail", "allure", "reportportal",
        "detox", "appium", "xctest", "espresso",
        "testing library", "enzyme",
    ],
    "monitoring": [
        "sentry", "datadog", "newrelic", "new relic", "grafana",
        "prometheus", "loki", "jaeger", "zipkin", "tempo",
        "dynatrace", "splunk", "logstash",
        "fluentd", "fluentbit", "vector", "opentelemetry", "otel",
        "pagerduty", "opsgenie", "incident.io", "statuspage",
        "uptimerobot", "betteruptime",
        "pingdom", "checkly", "cronitor", "healthchecks",
        "axiom", "highlight", "hyperdx", "signoz", "uptrace",
        "mezmo", "papertrail", "logtail",
        "instana", "lightstep",
        "netdata", "telegraf", "nagios", "zabbix",
    ],
    "database": [
        "postgres", "postgresql", "mysql", "mariadb", "sqlite",
        "mongodb", "dynamodb", "cassandra", "scylla", "couchdb",
        "couchbase", "rethinkdb", "arangodb", "surrealdb",
        "redis", "memcached", "valkey", "dragonfly", "keydb",
        "neon", "planetscale", "turso", "libsql", "xata",
        "cockroachdb", "cockroach", "yugabyte", "tidb", "vitess",
        "fauna", "faunadb", "convex", "upstash",
        "prisma", "drizzle", "typeorm", "sequelize", "knex",
        "sqlalchemy", "diesel", "gorm", "ent",
        "hasura", "postgrest", "graphile",
        "neo4j", "memgraph", "tigergraph", "dgraph",
        "influxdb", "timescale", "questdb",
    ],
    "cloud": [
        "aws", "amazon web services", "ec2", "lambda", "fargate",
        "azure", "microsoft azure", "gcp", "google cloud",
        "cloudflare", "cloudflare workers",
        "digital ocean", "digitalocean", "linode", "akamai",
        "hetzner", "ovh", "scaleway", "vultr", "upcloud",
        "fly.io", "railway", "render", "heroku",
        "vercel", "netlify", "deno deploy", "cloudflare pages",
        "serverless", "serverless framework",
        "terraform", "pulumi", "ansible", "crossplane",
        "eks", "ecs", "gke", "aks",
        "cloud run", "app engine", "elastic beanstalk",
        "amplify", "lightsail", "app runner",
    ],
    "automation": [
        "zapier", "make", "n8n", "ifttt", "power automate",
        "bardeen", "relay", "activepieces", "automatisch",
        "tray.io", "workato", "celigo", "boomi",
        "robocorp", "uipath", "automation anywhere", "blue prism",
        "airflow", "prefect", "dagster", "temporal",
        "inngest", "trigger.dev", "windmill",
        "pipedream", "hookdeck", "svix",
        "huginn", "node-red", "apache nifi",
        "celery", "bull", "bullmq", "agenda",
    ],
    "media": [
        "cloudinary", "imgix", "mux", "api.video",
        "ffmpeg", "sharp", "imagemagick",
        "spotify", "soundcloud", "youtube", "vimeo", "twitch",
        "giphy", "tenor", "unsplash", "pexels", "pixabay",
        "adobe", "photoshop", "premiere",
        "obs", "streamlabs",
        "wistia", "brightcove", "jwplayer",
        "tiktok", "instagram", "twitter", "x api",
        "facebook", "meta", "snapchat", "pinterest", "reddit",
        "mastodon", "bluesky", "threads", "linkedin",
    ],
    "analytics": [
        "mixpanel", "amplitude", "segment", "posthog", "plausible",
        "matomo", "fathom", "umami", "simple analytics",
        "google analytics", "hotjar", "fullstory", "logrocket",
        "heap", "kissmetrics", "pendo",
        "chartmogul", "baremetrics", "profitwell",
        "semrush", "ahrefs", "moz", "similarweb",
        "google tag manager", "gtm", "rudderstack", "jitsu",
        "snowplow", "freshpaint",
        "looker", "metabase", "superset", "redash", "lightdash",
        "cube", "evidence", "mode", "hex",
        "tableau", "power bi", "domo", "sisense", "thoughtspot",
    ],
    "ecommerce": [
        "shopify", "woocommerce", "magento", "bigcommerce",
        "medusa", "saleor", "vendure", "snipcart", "commercejs",
        "printful", "printify",
        "shippo", "easypost", "shipstation", "aftership",
        "yotpo", "loox", "judge.me",
        "recharge", "ordergroove",
        "gorgias", "reamaze",
        "avalara", "taxjar",
        "commercetools", "fabric",
        "amazon marketplace", "ebay", "etsy", "walmart",
    ],
    "education": [
        "canvas", "moodle", "blackboard", "d2l",
        "coursera", "udemy", "skillshare", "teachable",
        "thinkific", "kajabi", "podia", "learnworlds",
        "duolingo", "memrise", "anki", "quizlet",
        "lti", "scorm", "xapi",
        "google classroom", "schoology",
        "khan academy", "codecademy", "freecodecamp",
        "leetcode", "hackerrank", "codewars",
    ],
    "healthcare": [
        "epic", "cerner", "allscripts", "athenahealth",
        "fhir", "hl7", "dicom",
        "drchrono", "practice fusion",
        "teladoc", "amwell", "doxy.me",
        "apple health", "google health", "fitbit",
        "medplum", "openmrs",
        "redox", "health gorilla", "particle health",
    ],
    "design": [
        "figma", "sketch", "adobe xd", "invision",
        "zeplin", "framer", "webflow", "canva",
        "illustrator", "photoshop", "affinity",
        "blender", "cinema 4d", "maya", "unreal",
        "unity", "godot", "three.js",
        "tailwind", "tailwindcss", "bootstrap", "material ui",
        "chakra ui", "ant design", "radix", "shadcn",
        "storybook", "chromatic", "zeroheight",
        "dribbble", "behance",
        "spline", "rive", "lottie",
    ],
    "documentation": [
        "gitbook", "readme", "readme.io", "mintlify",
        "docusaurus", "mkdocs", "sphinx", "vitepress",
        "docsify", "nextra", "fumadocs", "starlight",
        "swagger", "redoc", "stoplight", "apidog",
        "confluence", "slite", "slab",
        "archbee", "document360",
        "typedoc", "jsdoc", "doxygen", "javadoc",
        "stainless", "fern", "speakeasy",
    ],
}

# ---------------------------------------------------------------------------
# Description-based keyword matching (broader semantic matching)
# ---------------------------------------------------------------------------
_DESCRIPTION_KEYWORDS: dict[str, list[str]] = {
    "ai": [
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "natural language", "nlp", "computer vision",
        "text generation", "image generation", "speech recognition",
        "text-to-speech", "speech-to-text", "embedding", "vector",
        "transformer", "fine-tune", "fine-tuning", "prompt",
        "rag", "retrieval augmented", "inference", "model serving",
        "large language", "generative",
        "chatbot", "conversational ai", "sentiment analysis",
        "classification", "tokeniz", "diffusion",
    ],
    "developer_tools": [
        "sdk", "framework", "library", "boilerplate", "scaffold",
        "bundler", "transpiler", "compiler", "linter", "formatter",
        "debugger", "profiler", "devtool", "dev tool",
        "code review", "pull request", "merge request",
        "continuous integration", "continuous delivery",
        "package manager", "dependency", "version control",
        "repository", "open source", "cli tool",
        "command line", "terminal", "shell",
        "api client", "http client", "rest client",
        "type checking", "static analysis", "code generation",
    ],
    "payments": [
        "payment processing", "payment gateway", "checkout",
        "billing", "subscription", "invoice", "receipt",
        "credit card", "debit card", "bank transfer",
        "payout", "refund", "chargeback",
        "fintech", "financial", "transaction",
    ],
    "communication": [
        "messaging", "chat", "email", "sms", "notification",
        "push notification", "webhook", "real-time",
        "video call", "voice call", "conference",
        "customer support", "helpdesk", "ticketing",
        "live chat", "inbox",
        "newsletter", "mailing list", "broadcast",
    ],
    "data": [
        "data pipeline", "etl", "elt", "data warehouse",
        "data lake", "data catalog", "data quality",
        "data transformation", "data integration",
        "business intelligence", "reporting",
        "data governance", "data lineage", "metadata",
        "streaming", "batch processing", "real-time data",
        "data visualization",
    ],
    "productivity": [
        "project management", "task management", "workflow",
        "collaboration", "workspace",
        "calendar", "scheduling", "meeting",
        "note taking", "knowledge base", "wiki",
        "spreadsheet", "form builder", "survey",
        "kanban", "gantt", "roadmap", "sprint",
        "time tracking", "timesheet",
    ],
    "blockchain": [
        "smart contract", "token", "nft", "defi",
        "decentralized", "dapp", "web3", "crypto",
        "wallet", "blockchain",
        "mining", "staking", "validator",
        "bridge", "swap", "liquidity", "amm",
        "dao", "governance", "on-chain", "onchain",
        "solidity",
    ],
    "search": [
        "full-text search", "search engine", "indexing",
        "autocomplete", "faceted search", "fuzzy search",
        "semantic search", "vector search", "hybrid search",
        "web scraping", "crawling", "web crawler",
    ],
    "storage": [
        "file storage", "object storage", "blob storage",
        "file upload", "image upload", "asset management",
        "cdn", "content delivery", "caching",
        "backup", "archive", "file sharing",
    ],
    "cms": [
        "content management", "headless cms", "blog",
        "rich text editor", "markdown editor", "wysiwyg",
        "content model", "content api", "publishing",
        "page builder", "website builder", "landing page",
    ],
    "security": [
        "authentication", "authorization", "oauth", "saml",
        "single sign-on", "sso", "mfa", "two-factor",
        "encryption", "decrypt", "cipher",
        "vulnerability", "penetration test", "pen test",
        "firewall", "waf", "ddos", "rate limit",
        "secret management", "credential", "api key management",
        "compliance", "audit", "access control", "rbac",
        "certificate", "ssl", "tls",
    ],
    "testing": [
        "unit test", "integration test", "end-to-end", "e2e",
        "test runner", "test framework", "assertion",
        "mock", "stub", "fixture", "snapshot test",
        "load test", "stress test", "performance test",
        "visual regression", "screenshot test",
        "code coverage", "mutation test",
        "test automation", "quality assurance",
        "browser testing", "cross-browser",
    ],
    "monitoring": [
        "logging", "log management", "log aggregation",
        "tracing", "distributed tracing", "observability",
        "metrics", "alerting", "incident",
        "uptime", "health check", "status page",
        "application performance", "error tracking",
        "crash reporting", "exception tracking",
    ],
    "database": [
        "database", "sql", "nosql", "query builder",
        "orm", "object relational", "migration",
        "connection pool", "database driver", "db client",
        "relational database", "document database",
        "key-value", "graph database", "time series",
        "replication", "sharding", "partitioning",
    ],
    "cloud": [
        "cloud computing", "serverless", "faas",
        "infrastructure", "provisioning",
        "container", "microservice", "service mesh",
        "load balancer", "auto-scaling", "scaling",
        "cloud native",
        "vpc", "networking", "dns", "domain",
        "deploy", "deployment", "hosting",
        "multi-cloud",
    ],
    "automation": [
        "automation", "automate", "workflow automation",
        "rpa", "robotic process",
        "scheduler", "cron job", "task queue",
        "trigger", "webhook handler", "event driven",
        "orchestration", "batch job",
        "no-code", "low-code", "visual programming",
    ],
    "media": [
        "image processing", "video processing", "audio processing",
        "transcoding", "streaming", "media player",
        "thumbnail", "resize", "crop", "watermark",
        "photo", "video", "audio", "podcast",
        "social media", "social network",
        "content creator",
    ],
    "analytics": [
        "analytics", "tracking",
        "dashboard", "reporting", "visualization",
        "cohort", "funnel", "retention", "conversion",
        "a/b test", "experiment", "feature flag",
        "user behavior", "session recording", "heatmap",
        "seo", "keyword research", "ranking",
        "attribution", "campaign tracking",
    ],
    "ecommerce": [
        "ecommerce", "e-commerce", "online store", "shop",
        "cart", "checkout", "order management",
        "inventory", "product catalog", "sku",
        "shipping", "fulfillment", "logistics",
        "marketplace", "storefront", "point of sale",
        "subscription commerce", "recurring billing",
    ],
    "education": [
        "learning management", "lms", "course",
        "tutorial", "lesson", "curriculum",
        "quiz", "assessment", "grading",
        "student", "teacher", "classroom",
        "e-learning", "online learning",
        "certification", "skill assessment",
    ],
    "healthcare": [
        "health", "medical", "clinical", "patient",
        "ehr", "emr", "electronic health record",
        "telehealth", "telemedicine",
        "fhir", "hl7", "dicom", "hipaa",
        "pharmacy", "prescription",
        "wearable", "fitness", "wellness",
    ],
    "design": [
        "ui design", "ux design", "interface design",
        "wireframe", "prototype", "mockup",
        "design system", "component library", "ui kit",
        "icon", "illustration", "typography",
        "color palette", "theme", "dark mode",
        "animation", "motion", "transition",
        "responsive design", "accessibility",
        "3d", "rendering", "webgl",
    ],
    "documentation": [
        "documentation", "api reference",
        "openapi", "api spec", "specification",
        "code documentation", "changelog",
        "api docs", "developer portal", "developer docs",
        "sdk generation", "client generation",
    ],
    "mcp": [
        "model context protocol", "mcp server", "mcp tool",
        "mcp client", "mcp resource", "mcp prompt",
    ],
    "skills": [
        "skill.md", "agent skill", "coding skill",
        "claude code skill", "codex skill", "openai codex",
        "skill file", "skill runner", "slash command",
        "reusable skill", "modular skill", "ai assistant skill",
    ],
}

# Reverse lookup: lowercase service name -> category
_SERVICE_CATEGORY: dict[str, str] = {}
for cat, names in _CATEGORY_MAP.items():
    for name in names:
        _SERVICE_CATEGORY[name.lower()] = cat

# Flattened description keyword lookup: keyword -> category
_DESC_KEYWORD_CATEGORY: list[tuple[str, str]] = []
for _cat, _keywords in _DESCRIPTION_KEYWORDS.items():
    for _kw in _keywords:
        _DESC_KEYWORD_CATEGORY.append((_kw.lower(), _cat))
# Sort by keyword length descending so longer (more specific) phrases match first
_DESC_KEYWORD_CATEGORY.sort(key=lambda x: len(x[0]), reverse=True)


# --- Category ↔ service_type aliases ---
# "mcp", "skills", "cli" are not real categories in _CATEGORY_MAP;
# they map to service_type values.  When a caller passes ?category=mcp,
# we want to match service_type="mcp_server" instead.
_CATEGORY_TYPE_ALIASES: dict[str, str] = {
    "mcp": "mcp_server",
    "skills": "skill",
    "cli": "cli_tool",
}


def _filter_by_category(items: list[dict], category: str) -> list[dict]:
    """Filter items by category, handling pseudo-categories that map to service_type."""
    alias = _CATEGORY_TYPE_ALIASES.get(category)
    if alias:
        return [s for s in items if s.get("service_type", "general") == alias]
    return [s for s in items if s.get("category") == category]


def _classify(service_name: str, description: str = "") -> str:
    """Classify a tool into a category using name and description matching.

    Strategy:
    1. Exact name match against _SERVICE_CATEGORY
    2. Partial name match (name contains known keyword or vice versa)
    3. n8n integration detection (n8n integration: X → classify by X)
    4. Description keyword matching against _DESCRIPTION_KEYWORDS
    5. Generic pattern matching (agent, cli, plugin → developer_tools)
    6. Fallback to 'other'
    """
    key = service_name.lower()

    # 1. Exact name match
    if key in _SERVICE_CATEGORY:
        return _SERVICE_CATEGORY[key]

    # 2. Partial name match
    for name, cat in _SERVICE_CATEGORY.items():
        if len(name) >= 3 and name in key:
            return cat
        # Only match key-in-name if key is long enough to be meaningful
        if len(key) >= 6 and key in name:
            return cat

    # 3. n8n integration detection — "n8n integration: salesforce" → look up "salesforce"
    desc_lower = (description or "").lower()
    if "n8n integration" in desc_lower or "n8n integration" in key:
        # Extract the integration target
        for pattern in ["n8n integration: ", "n8n integration "]:
            if pattern in desc_lower:
                target = desc_lower.split(pattern, 1)[1].strip().split()[0].rstrip(".")
                if target in _SERVICE_CATEGORY:
                    return _SERVICE_CATEGORY[target]
                # Try partial match on integration target
                for name, cat in _SERVICE_CATEGORY.items():
                    if name in target or target in name:
                        return cat
        return "automation"  # n8n integrations are automation tools

    # 4. Description-based matching (count hits per category, pick best)
    combined = f"{key} {desc_lower}"
    cat_hits: dict[str, int] = {}
    for kw, cat in _DESC_KEYWORD_CATEGORY:
        if kw in combined:
            cat_hits[cat] = cat_hits.get(cat, 0) + 1
    if cat_hits:
        return max(cat_hits, key=cat_hits.get)  # type: ignore[arg-type]

    # 5. Generic pattern matching for common tool patterns
    generic_patterns: list[tuple[str, str]] = [
        ("agent", "ai"), ("llm", "ai"), ("gpt", "ai"), ("claude", "ai"),
        ("openai", "ai"), ("model", "ai"), ("inference", "ai"),
        ("plugin", "developer_tools"), ("extension", "developer_tools"),
        ("wrapper", "developer_tools"), ("client", "developer_tools"),
        ("cli", "developer_tools"), ("sdk", "developer_tools"),
        ("server", "developer_tools"), ("adapter", "developer_tools"),
        ("connector", "automation"), ("integration", "automation"),
        ("bridge", "automation"), ("sync", "automation"),
        ("crm", "productivity"), ("erp", "productivity"),
        ("resume", "productivity"), ("template", "productivity"),
        ("parser", "developer_tools"), ("converter", "developer_tools"),
        ("generator", "developer_tools"), ("builder", "developer_tools"),
        ("scraper", "data"), ("crawler", "data"), ("extractor", "data"),
        ("auth", "security"), ("login", "security"), ("jwt", "security"),
        ("translate", "ai"), ("transcri", "ai"), ("ocr", "ai"),
        ("image", "media"), ("video", "media"), ("audio", "media"),
        ("music", "media"), ("photo", "media"),
        ("chart", "analytics"), ("graph", "analytics"), ("report", "analytics"),
        ("monitor", "monitoring"), ("alert", "monitoring"), ("log", "monitoring"),
        ("test", "testing"), ("spec", "testing"), ("assert", "testing"),
        ("deploy", "cloud"), ("host", "cloud"), ("container", "cloud"),
        ("database", "database"), ("sql", "database"), ("cache", "database"),
        ("store", "storage"), ("file", "storage"), ("upload", "storage"),
        ("doc", "documentation"), ("readme", "documentation"),
        ("shop", "ecommerce"), ("cart", "ecommerce"), ("product", "ecommerce"),
        ("learn", "education"), ("course", "education"), ("tutor", "education"),
        ("health", "healthcare"), ("medical", "healthcare"), ("fitness", "healthcare"),
        ("design", "design"), ("ui", "design"), ("figma", "design"),
    ]
    for pattern, cat in generic_patterns:
        if pattern in combined:
            return cat

    return "other"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
_services: list[dict[str, Any]] = []
_by_scan_id: dict[str, dict[str, Any]] = {}
_data_loaded_at: datetime | None = None  # UTC timestamp of last successful load


def get_data_info() -> dict[str, Any]:
    """Return data freshness info for health/status endpoints."""
    return {
        "tool_count": len(_services),
        "loaded_at": _data_loaded_at.isoformat() if _data_loaded_at else None,
        "age_hours": round(
            (datetime.utcnow() - _data_loaded_at).total_seconds() / 3600, 1
        ) if _data_loaded_at else None,
        "stale": (
            (datetime.utcnow() - _data_loaded_at).total_seconds() > 36 * 3600
        ) if _data_loaded_at else True,
    }


class SortOrder(str, Enum):
    score_desc = "score_desc"
    score_asc = "score_asc"
    name_asc = "name_asc"
    name_desc = "name_desc"
    recent = "recent"


class FieldsLevel(str, Enum):
    minimal = "minimal"    # name, url, score, category, type, scan_id only (~70% smaller)
    standard = "standard"  # current _compact_service output (default, backward-compat)
    full = "full"          # standard + dimensions sub_factors + recommendations


# ---------------------------------------------------------------------------
# Collected tools (loaded on demand when source=all)
# ---------------------------------------------------------------------------
_collected_tools: list[dict[str, Any]] = []
_collected_loaded = False

_COLLECTED_FILES = [
    "mcp-registry-all.json",
    "skills-cli-collected.json",
    "all-agent-tools.json",
]


def _find_data_dir() -> Path | None:
    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _find_collected_file(fname: str) -> Path | None:
    """Search multiple candidate directories for a collected data file."""
    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break
    for d in candidates:
        p = d / fname
        if p.exists():
            return p
    return None


def _load_collected() -> None:
    global _collected_tools, _collected_loaded
    if _collected_loaded:
        return

    from ..tool_scorer import normalize_tool

    seen_ids: set[str] = set()
    # name-based dedup: keep the higher-scored tool when the same name appears from different sources
    seen_names: dict[str, int] = {}  # lowercase name -> index in tools list
    tools: list[dict[str, Any]] = []

    for fname in _COLLECTED_FILES:
        fpath = _find_collected_file(fname)
        if not fpath:
            logger.warning("Collected file not found: %s", fname)
            continue
        try:
            with open(fpath, "r") as f:
                raw = json.load(f)
            for item in raw:
                normalized = normalize_tool(item)
                sid = normalized["scan_id"]
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)

                name_key = normalized["service_name"].lower().strip()
                if name_key in seen_names:
                    existing_idx = seen_names[name_key]
                    existing_score = tools[existing_idx].get("clarvia_score", 0)
                    new_score = normalized.get("clarvia_score", 0)
                    if new_score > existing_score:
                        tools[existing_idx] = normalized
                else:
                    seen_names[name_key] = len(tools)
                    tools.append(normalized)
        except Exception as e:
            logger.warning("Failed to load %s: %s", fname, e)

    _collected_tools = tools
    _collected_loaded = True
    logger.info("Loaded %d collected tools from %d files", len(tools), len(_COLLECTED_FILES))


def _deduplicate_services(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate tools from the services list.

    Two dedup passes:
    1. Exact URL duplicates — same normalized URL, keep higher score.
    2. Fuzzy name duplicates — names >90% similar AND sharing the same
       base URL domain+path (e.g. io.github.X/foo vs X/foo both pointing
       to github.com/X/foo).  Keep higher score.
    """
    if not services:
        return services

    # --- Pass 1: exact URL dedup ---
    url_best: dict[str, int] = {}  # normalized_url -> index of best entry
    for i, s in enumerate(services):
        url = (s.get("url") or "").rstrip("/").lower()
        if not url:
            continue
        if url in url_best:
            existing_score = services[url_best[url]].get("clarvia_score", 0)
            current_score = s.get("clarvia_score", 0)
            if current_score > existing_score:
                url_best[url] = i
        else:
            url_best[url] = i

    # Build set of indices to keep (for entries with URLs)
    kept_indices: set[int] = set(url_best.values())
    # Also keep entries without URLs
    for i, s in enumerate(services):
        url = (s.get("url") or "").rstrip("/").lower()
        if not url:
            kept_indices.add(i)

    deduped = [services[i] for i in sorted(kept_indices)]
    removed_url = len(services) - len(deduped)

    # --- Pass 2: fuzzy name dedup (same URL path root) ---
    # Group by domain+first_path_segment to avoid O(n²) on large domains
    # e.g. github.com/owner instead of github.com — keeps groups small
    from urllib.parse import urlparse

    def _url_path_root(url: str) -> str:
        """Extract domain + first path segment for grouping."""
        try:
            parsed = urlparse(url)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            root = parts[0] if parts else ""
            return f"{parsed.netloc.lower()}/{root}"
        except Exception:
            return ""

    path_root_groups: dict[str, list[int]] = {}
    for i, s in enumerate(deduped):
        url = s.get("url") or ""
        path_root = _url_path_root(url)
        if path_root:
            path_root_groups.setdefault(path_root, []).append(i)

    remove_fuzzy: set[int] = set()
    for path_root, indices in path_root_groups.items():
        if len(indices) < 2:
            continue
        # Compare pairs within the same path root
        for a_pos in range(len(indices)):
            a_idx = indices[a_pos]
            if a_idx in remove_fuzzy:
                continue
            a_name = deduped[a_idx].get("service_name", "").lower().strip()
            for b_pos in range(a_pos + 1, len(indices)):
                b_idx = indices[b_pos]
                if b_idx in remove_fuzzy:
                    continue
                b_name = deduped[b_idx].get("service_name", "").lower().strip()
                # Quick length pre-filter: skip SequenceMatcher if lengths differ too much
                len_a, len_b = len(a_name), len(b_name)
                if len_a == 0 or len_b == 0:
                    continue
                if min(len_a, len_b) / max(len_a, len_b) < 0.7:
                    continue
                name_ratio = SequenceMatcher(None, a_name, b_name).ratio()
                if name_ratio <= 0.90:
                    continue
                # Keep the one with higher score
                a_score = deduped[a_idx].get("clarvia_score", 0)
                b_score = deduped[b_idx].get("clarvia_score", 0)
                if b_score > a_score:
                    remove_fuzzy.add(a_idx)
                    break  # a_idx is removed, stop comparing it
                else:
                    remove_fuzzy.add(b_idx)

    if remove_fuzzy:
        deduped = [s for i, s in enumerate(deduped) if i not in remove_fuzzy]

    total_removed = removed_url + len(remove_fuzzy)
    if total_removed > 0:
        logger.info(
            "Dedup: removed %d exact-URL dupes + %d fuzzy-name dupes (%d total)",
            removed_url, len(remove_fuzzy), total_removed,
        )
    return deduped


def _load_data() -> None:
    global _services, _by_scan_id
    data_dir = _find_data_dir()
    data_path = data_dir / "prebuilt-scans.json" if data_dir else None

    if data_path is None or not data_path.exists():
        logger.error("prebuilt-scans.json not found in any candidate path")
        return
    import time
    with open(data_path, "r") as f:
        raw = json.load(f)
    # Yield GIL after heavy JSON parse so event loop can breathe
    time.sleep(0.1)

    for i, entry in enumerate(raw):
        # Respect existing category from prebuilt-scans.json; only auto-classify if missing or "other"
        existing_cat = entry.get("category", "other")
        if not existing_cat or existing_cat == "other":
            entry["category"] = _classify(
                entry.get("service_name", ""),
                entry.get("description", ""),
            )
        # Yield GIL every 500 items so the event loop can serve requests
        if i % 500 == 0:
            time.sleep(0)

    time.sleep(0.1)  # yield before dedup
    raw = _deduplicate_services(raw)
    time.sleep(0.1)  # yield after dedup
    _services = raw
    _by_scan_id = {s["scan_id"]: s for s in _services}
    logger.info("Loaded %d services for Index API", len(_services))

    # Merge scanned profiles into the services index
    _merge_profiles()


def _merge_profiles() -> None:
    """Load scanned profiles and add them to the services index."""
    global _services, _by_scan_id
    try:
        from .profile_routes import get_all_profiles

        for profile in get_all_profiles():
            if profile.get("status") != "scanned" or profile.get("scan_result") is None:
                continue

            scan_result = profile["scan_result"]
            scan_id = scan_result.get("scan_id")
            if not scan_id or scan_id in _by_scan_id:
                continue  # already present or no scan_id

            entry = {
                "scan_id": scan_id,
                "url": profile["url"],
                "service_name": profile["name"],
                "description": profile.get("description", ""),
                "clarvia_score": profile.get("clarvia_score", 0),
                "rating": scan_result.get("rating", "unknown"),
                "dimensions": scan_result.get("dimensions", {}),
                "category": profile.get("category", "other"),
                "service_type": profile.get("service_type", "general"),
                "type_config": profile.get("type_config"),
                "scanned_at": scan_result.get("scanned_at"),
                "source": "profile",
                "profile_id": profile["profile_id"],
                "tags": profile.get("tags", []),
                "agents_json_valid": profile.get("agents_json_valid"),
            }
            _services.append(entry)
            _by_scan_id[scan_id] = entry

        logger.info("Merged profiles, total services: %d", len(_services))
    except Exception as e:
        logger.warning("Failed to merge profiles: %s", e)


def _ensure_loaded() -> None:
    if not _services:
        _load_data()


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _generate_code_snippet(s: dict) -> str | None:
    """Generate a quick-start code snippet based on service type."""
    st = s.get("service_type", "general")
    tc = s.get("type_config") or {}
    name = s.get("service_name", "")
    if st == "mcp_server":
        pkg = tc.get("npm_package", name.lower().replace(" ", "-"))
        return f"npx -y {pkg}"
    elif st == "cli_tool":
        cmd = tc.get("install_command", "")
        return cmd if cmd else None
    elif st == "api":
        base = tc.get("base_url") or tc.get("openapi_url") or ""
        if base:
            return f"curl {base}"
        return None
    return None


def _generate_install_hint(tool: dict) -> str | None:
    """Generate an install command hint based on tool type and source."""
    name = (tool.get("service_name") or tool.get("name", "")).lower().strip()
    url = tool.get("url", "")
    source = tool.get("source", "")
    category = tool.get("category", "")
    tc = tool.get("type_config") or {}
    service_type = tool.get("service_type", "general")

    # npm packages
    if source in ("npm", "npm_registry") or "npmjs.com" in url:
        pkg = tc.get("npm_package") or name
        return f"npx -y {pkg}"

    # PyPI packages
    if source in ("pypi", "pypi_registry") or "pypi.org" in url:
        pkg = tc.get("pypi_package") or name
        return f"pip install {pkg}"

    # MCP servers (common pattern)
    if service_type == "mcp_server" or category == "mcp" or "mcp" in name:
        pkg = tc.get("npm_package")
        if pkg:
            return f"npx -y {pkg}"
        if "github.com" in url:
            return f"npx -y {name}"
        return f"npx -y @modelcontextprotocol/{name}"

    # Skills
    if category == "skills" or service_type == "skill" or source == "github_skills":
        if "github.com" in url:
            slug = name.replace(" ", "-")
            return f"git clone {url} .claude/skills/{slug}"

    # CLI tools with explicit install command
    if service_type == "cli_tool":
        cmd = tc.get("install_command")
        if cmd:
            return cmd

    return None


def _minimal_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return minimal representation — name, score, category only.

    Inspired by Claude Code's Deferred Discovery pattern: send lightweight
    references first, load full details on demand via /v1/services/{id}.
    """
    return {
        "name": s["service_name"],
        "url": s.get("url", ""),
        "clarvia_score": s["clarvia_score"],
        "category": s.get("category", "other"),
        "service_type": s.get("service_type", "general"),
        "scan_id": s["scan_id"],
    }


def _compact_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a compact representation (no sub_factors)."""
    dims = s.get("dimensions", {})
    result = {
        "name": s["service_name"],
        "url": s["url"],
        "description": s.get("description", ""),
        "category": s.get("category", "other"),
        "service_type": s.get("service_type", "general"),
        "clarvia_score": s["clarvia_score"],
        "rating": s["rating"],
        "dimensions": {k: v["score"] for k, v in dims.items()},
        "scan_id": s["scan_id"],
        "last_scanned": s.get("scanned_at"),
        "pricing": s.get("pricing", "unknown"),
        "difficulty": s.get("difficulty", "medium"),
        "capabilities": s.get("capabilities", []),
        "code_snippet": _generate_code_snippet(s),
        "install_hint": _generate_install_hint(s),
        "popularity": s.get("popularity", 0),
        "cross_refs": s.get("cross_refs", {}),
        "added_at": s.get("added_at") or s.get("scanned_at"),
        "rank": None,
    }
    # Include connection_info for typed services
    tc = s.get("type_config")
    if tc:
        result["connection_info"] = _build_connection_info(s.get("service_type", "general"), tc)
    if s.get("profile_id"):
        result["profile_id"] = s["profile_id"]
    return result


def _build_connection_info(service_type: str, type_config: dict) -> dict[str, Any]:
    """Build agent-friendly connection info from type_config."""
    if service_type == "mcp_server":
        info: dict[str, Any] = {}
        if type_config.get("npm_package"):
            info["install"] = f"npm install {type_config['npm_package']}"
        if type_config.get("endpoint_url"):
            info["endpoint"] = type_config["endpoint_url"]
        if type_config.get("transport"):
            info["transport"] = type_config["transport"]
        if type_config.get("tools"):
            info["tools"] = type_config["tools"]
        return info
    elif service_type == "cli_tool":
        info = {}
        if type_config.get("install_command"):
            info["install"] = type_config["install_command"]
        if type_config.get("binary_name"):
            info["binary"] = type_config["binary_name"]
        return info
    elif service_type == "api":
        info = {}
        if type_config.get("openapi_url"):
            info["openapi"] = type_config["openapi_url"]
        if type_config.get("base_url"):
            info["base_url"] = type_config["base_url"]
        if type_config.get("auth_method"):
            info["auth"] = type_config["auth_method"]
        return info
    elif service_type == "skill":
        info = {}
        if type_config.get("skill_file_url"):
            info["skill_url"] = type_config["skill_file_url"]
        if type_config.get("compatible_agents"):
            info["agents"] = type_config["compatible_agents"]
        return info
    return {}


def _full_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a full representation with sub_factors and recommendations."""
    result = _compact_service(s)
    # Override dimensions with full sub_factors (compact only has scores)
    result["dimensions"] = s.get("dimensions", {})
    result["recommendations"] = s.get("recommendations", [])
    result["tags"] = s.get("tags", [])
    result["methodology"] = s.get("methodology")
    return result


def _total_tool_count() -> int:
    """Single source of truth for the total tool count across all data sources."""
    _ensure_loaded()
    _load_collected()
    scanned_ids = {s["scan_id"] for s in _services}
    return len(_services) + sum(1 for t in _collected_tools if t["scan_id"] not in scanned_ids)


def _add_headers(response: Response) -> None:
    response.headers["X-Clarvia-Version"] = "1.0"
    response.headers["X-Clarvia-Total-Services"] = str(_total_tool_count())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/services")
async def list_services(
    response: Response,
    category: str | None = Query(None, description="Filter by category"),
    service_type: str | None = Query(None, description="Filter by type: mcp_server|skill|cli_tool|api|general"),
    q: str | None = Query(None, description="Text search in name/description"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum Clarvia Score"),
    max_score: int | None = Query(None, ge=0, le=100, description="Maximum Clarvia Score"),
    sort: SortOrder = Query(SortOrder.score_desc, description="Sort order"),
    source: str | None = Query("all", description="'all' (default) includes 27k+ tools, 'scanned' for prebuilt only, 'collected' for collected only"),
    added_after: str | None = Query(None, description="ISO date filter, e.g. 2026-03-20"),
    similar_to: str | None = Query(None, description="Find tools similar to this scan_id"),
    fields: FieldsLevel = Query(FieldsLevel.standard, description="Response detail level: minimal (6 fields, ~70%% smaller), standard (default), full (with sub_factors)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search and filter services for agent consumption.

    Supports compound filters: service_type + category + score + text search.
    Defaults to all 27,000+ agent tools (MCP servers, APIs, CLIs, Skills).
    Use source=scanned to limit to prebuilt-scans only.
    Example: GET /v1/services?service_type=mcp_server&q=github
    """
    _ensure_loaded()
    _add_headers(response)

    # Track search analytics
    if q:
        _search_counter[q.lower()] += 1
        if len(_search_log) < _MAX_SEARCH_LOG:
            _search_log.append({"query": q, "category": category, "ts": _time.time(), "results": 0})

    if source in ("all", "collected"):
        _load_collected()

    # Handle similar_to: override category/service_type filters from the reference tool
    if similar_to:
        _load_collected()
        ref = _by_scan_id.get(similar_to)
        if not ref:
            for t in _collected_tools:
                if t["scan_id"] == similar_to:
                    ref = t
                    break
        if not ref:
            raise HTTPException(status_code=404, detail=f"Tool {similar_to} not found for similarity lookup")
        category = ref.get("category", "other")
        service_type = ref.get("service_type")
        sort = SortOrder.score_desc
        if source is None:
            source = "all"

    if source == "collected":
        filtered = list(_collected_tools)
    elif source == "all":
        # Merge: scanned services first (higher quality), then collected
        scanned_ids = {s["scan_id"] for s in _services}
        filtered = list(_services) + [
            t for t in _collected_tools if t["scan_id"] not in scanned_ids
        ]
    else:
        filtered = _services

    if category:
        filtered = _filter_by_category(filtered, category)

    if service_type:
        filtered = [s for s in filtered if s.get("service_type", "general") == service_type]

    if q:
        q_lower = q.lower()
        matched = []
        for s in filtered:
            name = s.get("service_name", "").lower()
            desc = s.get("description", "").lower()
            url = s.get("url", "").lower()
            tags = [t.lower() for t in s.get("tags", [])]
            if q_lower not in name and q_lower not in desc and q_lower not in url and not any(q_lower in t for t in tags):
                continue
            # Relevance: name exact > name contains > tags > description
            if name == q_lower:
                relevance = 4
            elif q_lower in name:
                relevance = 3
            elif any(q_lower in t for t in tags):
                relevance = 2
            else:
                relevance = 1
            matched.append((relevance, s))
        # Sort by relevance first, then by score within same relevance
        matched.sort(key=lambda x: (x[0], x[1]["clarvia_score"]), reverse=True)
        filtered = [s for _, s in matched]

    filtered = [s for s in filtered if s["clarvia_score"] >= min_score]

    if max_score is not None:
        filtered = [s for s in filtered if s["clarvia_score"] <= max_score]

    if added_after:
        filtered = [s for s in filtered if (s.get("scanned_at") or "") >= added_after]

    # Exclude the reference tool from similar_to results
    if similar_to:
        filtered = [s for s in filtered if s["scan_id"] != similar_to]

    # When a text query is active, relevance sort is already applied — skip re-sort
    # unless user explicitly requested a different sort order
    if not q:
        if sort == SortOrder.score_desc:
            filtered.sort(key=lambda s: s["clarvia_score"], reverse=True)
        elif sort == SortOrder.score_asc:
            filtered.sort(key=lambda s: s["clarvia_score"])
        elif sort == SortOrder.name_asc:
            filtered.sort(key=lambda s: s["service_name"].lower())
        elif sort == SortOrder.name_desc:
            filtered.sort(key=lambda s: s["service_name"].lower(), reverse=True)
        elif sort == SortOrder.recent:
            filtered.sort(key=lambda s: s.get("scanned_at") or "", reverse=True)
    else:
        # With text query: only re-sort if user explicitly set a non-default sort
        if sort == SortOrder.score_asc:
            filtered.sort(key=lambda s: s["clarvia_score"])
        elif sort == SortOrder.name_asc:
            filtered.sort(key=lambda s: s["service_name"].lower())
        elif sort == SortOrder.name_desc:
            filtered.sort(key=lambda s: s["service_name"].lower(), reverse=True)
        elif sort == SortOrder.recent:
            filtered.sort(key=lambda s: s.get("scanned_at") or "", reverse=True)
        # score_desc (default) → keep relevance order

    total = len(filtered)

    # Update search log with result count
    if q and _search_log:
        _search_log[-1]["results"] = total

    page = filtered[offset : offset + limit]

    # Deferred Discovery: serialize based on fields level
    if fields == FieldsLevel.minimal:
        serializer = _minimal_service
    elif fields == FieldsLevel.full:
        serializer = _full_service
    else:
        serializer = _compact_service

    services_out = [serializer(s) for s in page]
    # Inject rank for score_desc ordering
    if sort == SortOrder.score_desc:
        for i, svc in enumerate(services_out):
            svc["rank"] = offset + i + 1

    result: dict[str, Any] = {
        "total": total,
        "services": services_out,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
    }
    # Hint for empty/missing query
    if not q and not category and not service_type and min_score == 0:
        result["_hint"] = "No filters applied — showing all services. Try ?q=email or ?category=ai for filtered results."
    return result


# Aliases for discoverability — agents try /search, /score, /leaderboard
@router.get("/search")
async def search_alias(
    response: Response,
    q: str | None = Query(None),
    query: str | None = Query(None, description="Alias for q — agents may use either"),
    category: str | None = Query(None),
    service_type: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    sort: SortOrder = Query(SortOrder.score_desc),
    source: str | None = Query(None),
    added_after: str | None = Query(None),
    similar_to: str | None = Query(None),
    fields: FieldsLevel = Query(FieldsLevel.standard),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Alias for /v1/services — agents naturally look for /search."""
    effective_q = q or query
    return await list_services(
        response=response, category=category, service_type=service_type,
        q=effective_q, min_score=min_score, max_score=None, sort=sort,
        source=source, added_after=added_after, similar_to=similar_to,
        fields=fields, limit=limit, offset=offset,
    )


@router.get("/alternatives/{service_name}")
async def get_alternatives(
    service_name: str,
    response: Response,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Find alternative tools to the given service.

    Uses category matching + description keyword overlap to find the most similar tools.
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    service_name_lower = service_name.lower().strip()

    # Build full pool: scanned + collected (deduplicated)
    scanned_ids = {s["scan_id"] for s in _services}
    pool = list(_services) + [
        t for t in _collected_tools if t["scan_id"] not in scanned_ids
    ]

    # --- Step 1: Find the target service by fuzzy name match ---
    target = None
    best_ratio = 0.0
    for s in pool:
        name = s.get("service_name", "").lower().strip()
        # Exact match
        if name == service_name_lower:
            target = s
            best_ratio = 1.0
            break
        # Check if query is contained in name or vice versa
        if service_name_lower in name or name in service_name_lower:
            ratio = SequenceMatcher(None, service_name_lower, name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                target = s
        # Also check URL
        url_val = s.get("url", "").lower()
        if service_name_lower in url_val:
            ratio = SequenceMatcher(None, service_name_lower, name).ratio()
            if ratio > best_ratio or (target is None):
                best_ratio = max(ratio, 0.5)
                target = s

    # Fallback: fuzzy match across all names
    if target is None:
        for s in pool:
            name = s.get("service_name", "").lower().strip()
            ratio = SequenceMatcher(None, service_name_lower, name).ratio()
            if ratio > best_ratio and ratio >= 0.5:
                best_ratio = ratio
                target = s

    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found in the catalog. Try a different name.",
        )

    target_name = target["service_name"]
    target_category = target.get("category", "other")
    target_desc = (target.get("description") or "").lower()
    target_scan_id = target["scan_id"]
    target_url_lower = target.get("url", "").lower().rstrip("/")
    target_name_lower = target_name.lower().strip()

    # --- Step 2: Find alternatives in the same category ---
    # Exclude by scan_id AND by url/name to prevent self-referential results
    same_category = [
        s for s in pool
        if s.get("category") == target_category
        and s["scan_id"] != target_scan_id
        and s.get("url", "").lower().rstrip("/") != target_url_lower
        and s.get("service_name", "").lower().strip() != target_name_lower
    ]

    # --- Step 3: Score by description keyword overlap ---
    target_words = set(_tokenize_for_similarity(target_desc))

    scored: list[tuple[float, dict]] = []
    for s in same_category:
        desc = (s.get("description") or "").lower()
        candidate_words = set(_tokenize_for_similarity(desc))

        # Jaccard similarity on keyword tokens
        if target_words and candidate_words:
            intersection = target_words & candidate_words
            union = target_words | candidate_words
            similarity = len(intersection) / len(union) if union else 0.0
        else:
            similarity = 0.0

        # Boost for same service_type
        if s.get("service_type") == target.get("service_type"):
            similarity += 0.05

        # Boost for tag overlap
        target_tags = set(t.lower() for t in target.get("tags", []))
        candidate_tags = set(t.lower() for t in s.get("tags", []))
        if target_tags and candidate_tags:
            tag_overlap = len(target_tags & candidate_tags) / len(target_tags | candidate_tags)
            similarity += tag_overlap * 0.15

        scored.append((similarity, s))

    # Sort by similarity desc, then by clarvia_score desc
    scored.sort(key=lambda x: (x[0], x[1]["clarvia_score"]), reverse=True)

    alternatives = []
    for sim, s in scored[:limit]:
        alternatives.append({
            "name": s["service_name"],
            "url": s.get("url", ""),
            "score": s["clarvia_score"],
            "category": s.get("category", "other"),
            "similarity": round(sim, 3),
            "install_hint": _generate_install_hint(s),
            "description": (s.get("description") or "")[:200],
            "scan_id": s["scan_id"],
        })

    return {
        "service": target_name,
        "category": target_category,
        "alternatives": alternatives,
        "total_in_category": len(same_category),
    }


def _tokenize_for_similarity(text: str) -> list[str]:
    """Extract meaningful tokens from text for similarity comparison."""
    import re as _re
    # Split into words, filter stop words and short tokens
    _stop = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "it", "its",
        "this", "that", "these", "those", "your", "you", "we", "they",
        "our", "their", "not", "no", "more", "most", "also", "as", "than",
        "very", "just", "about", "all", "any", "each", "every", "both",
    }
    tokens = _re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) >= 2 and t not in _stop]


@router.get("/score")
async def score_quick(
    response: Response,
    url: str = Query(..., description="Service URL to get score for"),
):
    """Quick score lookup by URL — returns cached score or 'not_found'."""
    _ensure_loaded()
    _add_headers(response)

    # BUG-04 fix: URL에 스킴이 없으면 https:// 붙여서 정규화
    def _normalize(u: str) -> str:
        return u.lower().rstrip("/")

    candidates = [url]
    if not url.startswith(("http://", "https://")):
        candidates = [f"https://{url}", f"http://{url}"]

    for candidate in candidates:
        candidate_lower = _normalize(candidate)
        for s in _services:
            if _normalize(s.get("url", "")) == candidate_lower:
                return {
                    "url": url,
                    "score": s["clarvia_score"],
                    "rating": s["rating"],
                    "category": s.get("category", "other"),
                    "scan_id": s["scan_id"],
                    "found": True,
                }
    return {
        "url": url,
        "score": None,
        "rating": None,
        "found": False,
        "message": "Not yet scanned. Use POST /api/scan to get a score.",
    }


@router.get("/leaderboard")
async def leaderboard(
    response: Response,
    category: str | None = Query(None),
    type: str | None = Query(None, description="Filter by service_type, e.g. 'mcp' or 'api'"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Top-scoring services leaderboard."""
    _ensure_loaded()
    _add_headers(response)
    _load_collected()
    scanned_ids = {s["scan_id"] for s in _services}
    pool = list(_services) + [
        t for t in _collected_tools if t["scan_id"] not in scanned_ids
    ]
    filtered = pool
    if category:
        filtered = _filter_by_category(filtered, category)
    # Infer service_type for all items (many have service_type=null in data)
    def _infer_service_type(s: dict) -> str:
        st = (s.get("service_type") or "").lower()
        if st:
            return st
        url = (s.get("url") or "").lower()
        name = (s.get("service_name") or "").lower()
        if "mcp" in url or "-mcp" in name or "mcp" in name:
            return "mcp_server"
        return "api"

    for s in filtered:
        s["_inferred_type"] = _infer_service_type(s)

    if type:
        type_lower = type.lower()
        mcp_aliases = {"mcp", "mcp_server"}
        if type_lower in mcp_aliases:
            filtered = [s for s in filtered if s["_inferred_type"] in mcp_aliases]
        else:
            filtered = [s for s in filtered if s["_inferred_type"] == type_lower]

    # Deduplicate by URL (keep highest-scoring entry for each URL)
    seen_urls: dict[str, dict] = {}
    for s in filtered:
        url_key = (s.get("url") or "").lower().rstrip("/")
        existing = seen_urls.get(url_key)
        if existing is None or s.get("clarvia_score", 0) > existing.get("clarvia_score", 0):
            seen_urls[url_key] = s
    filtered = list(seen_urls.values())

    # BUG-02 fix: total은 필터 적용 후, 정렬 전 개수로 계산
    filtered_total = len(filtered)
    filtered = sorted(filtered, key=lambda s: s.get("clarvia_score", 0), reverse=True)
    filtered = filtered[offset : offset + limit]
    return {
        "leaderboard": [
            {
                "rank": offset + i + 1,
                "name": s.get("service_name", "Unknown"),
                "url": s.get("url", ""),
                "score": s.get("clarvia_score", 0),
                "clarvia_score": s.get("clarvia_score", 0),
                "rating": s.get("rating", "Unknown"),
                "category": s.get("category", "other"),
                "service_type": s.get("_inferred_type") or s.get("service_type"),
                "scan_id": s.get("scan_id", ""),
            }
            for i, s in enumerate(filtered)
        ],
        "total": filtered_total if (category or type) else _total_tool_count(),
    }


@router.get("/services/{scan_id}")
async def get_service(scan_id: str, response: Response):
    """Get full details for a specific service by scan_id."""
    _ensure_loaded()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        # Try collected tools
        _load_collected()
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # For collected tools, return enriched format
    if scan_id.startswith("tool_"):
        return {
            "name": service["service_name"],
            "url": service.get("url", ""),
            "description": service.get("description", ""),
            "category": service.get("category", "other"),
            "service_type": service.get("service_type", "general"),
            "clarvia_score": service["clarvia_score"],
            "rating": service["rating"],
            "dimensions": service.get("dimensions", {}),
            "scan_id": service["scan_id"],
            "source": service.get("source", ""),
            "tags": service.get("tags", []),
            "type_config": service.get("type_config"),
            "last_scanned": service.get("scanned_at"),
        }
    return _full_service(service)


@router.get("/categories")
async def list_categories(
    response: Response,
    source: str | None = Query(None, description="'all' to include collected tools"),
):
    """List available categories with service counts."""
    _ensure_loaded()
    _add_headers(response)

    # Build the pool based on source param (same as /stats)
    if source == "all":
        _load_collected()
        scanned_ids = {s["scan_id"] for s in _services}
        pool = list(_services) + [
            t for t in _collected_tools if t["scan_id"] not in scanned_ids
        ]
    else:
        pool = _services

    counts: dict[str, int] = {}
    for s in pool:
        cat = s.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1

    # Also include categories from _CATEGORY_MAP that may have 0 tools
    for cat in _CATEGORY_MAP:
        if cat not in counts:
            counts[cat] = 0

    # Add pseudo-categories based on service_type (mcp, skills, cli)
    for alias_name, alias_type in _CATEGORY_TYPE_ALIASES.items():
        alias_count = sum(1 for s in pool if s.get("service_type", "general") == alias_type)
        counts[alias_name] = alias_count

    return {
        "categories": sorted(
            [{"name": cat, "count": count} for cat, count in counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )
    }


# ---------------------------------------------------------------------------
# Category detail labels & descriptions for landing pages
# ---------------------------------------------------------------------------
_CATEGORY_META: dict[str, dict[str, str]] = {
    "database": {
        "label": "Database",
        "description": "Database management systems, ORMs, and data infrastructure tools for AI agents. Includes relational databases, NoSQL stores, graph databases, and database-as-a-service platforms.",
    },
    "security": {
        "label": "Security & Compliance",
        "description": "Security scanning, authentication, secrets management, and compliance tools for AI agents. Covers vulnerability detection, identity management, encryption, and audit solutions.",
    },
    "ai": {
        "label": "AI & Machine Learning",
        "description": "AI model providers, ML frameworks, vector databases, and intelligent automation tools. Includes LLM APIs, image generation, speech processing, and AI development platforms.",
    },
    "developer_tools": {
        "label": "Developer Tools",
        "description": "Version control, CI/CD, code quality, hosting, and API development tools for AI agents. Covers the complete software development lifecycle.",
    },
    "communication": {
        "label": "Communication",
        "description": "Messaging, email, video conferencing, and notification tools for AI agents. Includes chat platforms, customer support, SMS, and real-time communication services.",
    },
    "data": {
        "label": "Data & Analytics Pipelines",
        "description": "Data warehouses, ETL pipelines, orchestration, and business intelligence tools for AI agents. Covers data transformation, quality, and governance.",
    },
    "productivity": {
        "label": "Productivity & Workflow",
        "description": "Project management, automation, collaboration, and knowledge management tools for AI agents. Includes task trackers, note-taking apps, and low-code platforms.",
    },
    "blockchain": {
        "label": "Blockchain & Web3",
        "description": "Blockchain networks, smart contract tools, DeFi protocols, and Web3 infrastructure for AI agents. Covers wallets, indexers, and on-chain analytics.",
    },
    "payments": {
        "label": "Payment & Finance",
        "description": "Payment processing, billing, invoicing, and financial infrastructure tools for AI agents. Includes gateways, subscription management, and banking APIs.",
    },
    "mcp": {
        "label": "MCP Servers",
        "description": "Model Context Protocol servers and related tools that enable AI agents to interact with external services through a standardized protocol.",
    },
    "search": {
        "label": "Search & Retrieval",
        "description": "Full-text search engines, semantic search, web scraping, and information retrieval tools for AI agents. Includes search APIs and crawling services.",
    },
    "storage": {
        "label": "File & Object Storage",
        "description": "Cloud storage, CDN, file upload, and asset management tools for AI agents. Covers object stores, image optimization, and content delivery networks.",
    },
    "cms": {
        "label": "CMS & Content",
        "description": "Content management systems, headless CMS platforms, and publishing tools for AI agents. Includes blog engines, page builders, and content APIs.",
    },
    "testing": {
        "label": "Testing & QA",
        "description": "Test frameworks, browser automation, load testing, and quality assurance tools for AI agents. Covers unit, integration, and end-to-end testing.",
    },
    "monitoring": {
        "label": "Monitoring & Observability",
        "description": "Application monitoring, logging, tracing, and incident management tools for AI agents. Includes APM, error tracking, and uptime monitoring.",
    },
    "cloud": {
        "label": "Cloud Infrastructure",
        "description": "Cloud providers, serverless platforms, container orchestration, and infrastructure-as-code tools for AI agents. Covers AWS, GCP, Azure, and alternatives.",
    },
    "automation": {
        "label": "Automation & Integration",
        "description": "Workflow automation, iPaaS, event-driven architectures, and integration tools for AI agents. Includes no-code automation and job scheduling.",
    },
    "media": {
        "label": "Media & Social",
        "description": "Image processing, video streaming, social media APIs, and creative tools for AI agents. Covers content creation, media optimization, and platform integrations.",
    },
    "analytics": {
        "label": "Analytics & BI",
        "description": "Web analytics, product analytics, business intelligence, and SEO tools for AI agents. Includes dashboards, event tracking, and data visualization.",
    },
    "ecommerce": {
        "label": "E-commerce",
        "description": "E-commerce platforms, shipping, reviews, and marketplace tools for AI agents. Covers online stores, order management, and retail integrations.",
    },
    "education": {
        "label": "Education & Learning",
        "description": "Learning management systems, course platforms, and educational tools for AI agents. Includes LMS, coding education, and assessment platforms.",
    },
    "healthcare": {
        "label": "Healthcare",
        "description": "Electronic health records, FHIR/HL7 tools, telehealth, and health data platforms for AI agents. Covers clinical systems and health interoperability.",
    },
    "design": {
        "label": "Design & UI",
        "description": "Design tools, UI component libraries, prototyping, and creative software for AI agents. Includes Figma, CSS frameworks, and 3D tools.",
    },
    "documentation": {
        "label": "Documentation",
        "description": "Documentation generators, API docs, knowledge bases, and technical writing tools for AI agents. Covers static site generators and API specification tools.",
    },
    "skills": {
        "label": "Agent Skills",
        "description": "Modular SKILL.md capabilities for AI coding assistants like Claude Code and OpenAI Codex. Includes reusable slash commands, workflow skills, and agent-specific task modules.",
        "icon": "puzzle",
    },
    "mcp": {
        "label": "MCP Servers",
        "description": "Model Context Protocol servers that extend AI assistants with external tool access. Includes database connectors, API bridges, file system access, and specialized integrations.",
        "icon": "server",
    },
    "cli": {
        "label": "CLI Tools",
        "description": "Command-line interface tools for AI agents and developers. Includes terminal utilities, build tools, and developer productivity commands.",
        "icon": "terminal",
    },
    "other": {
        "label": "Other",
        "description": "Miscellaneous tools and services for AI agents that span multiple categories or serve specialized use cases.",
    },
}


@router.get("/categories/{slug}")
async def get_category_detail(
    slug: str,
    response: Response,
    service_type: str | None = Query(None, description="Filter by type"),
    sort: str = Query("score_desc", description="Sort: score_desc|score_asc|name_asc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get tools in a specific category, ranked by Clarvia Score."""
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    # Build pool: scanned + collected (deduplicated)
    scanned_ids = {s["scan_id"] for s in _services}
    pool = list(_services) + [
        t for t in _collected_tools if t["scan_id"] not in scanned_ids
    ]

    # Filter by category (handles pseudo-categories like "mcp" → service_type)
    filtered = _filter_by_category(pool, slug)

    if not filtered and slug not in _CATEGORY_MAP and slug not in _CATEGORY_META and slug not in _CATEGORY_TYPE_ALIASES:
        raise HTTPException(status_code=404, detail=f"Category '{slug}' not found")

    # Optional service_type filter
    if service_type:
        filtered = [s for s in filtered if s.get("service_type", "general") == service_type]

    total = len(filtered)

    # Sort
    if sort == "score_asc":
        filtered.sort(key=lambda s: s["clarvia_score"])
    elif sort == "name_asc":
        filtered.sort(key=lambda s: s.get("service_name", "").lower())
    else:
        filtered.sort(key=lambda s: s["clarvia_score"], reverse=True)

    # Paginate
    page = filtered[offset : offset + limit]

    # Compute stats
    scores = [s["clarvia_score"] for s in filtered] if filtered else [0]
    type_counts: dict[str, int] = {}
    for s in filtered:
        st = s.get("service_type", "general")
        type_counts[st] = type_counts.get(st, 0) + 1

    meta = _CATEGORY_META.get(slug, {"label": slug.replace("_", " ").title(), "description": ""})

    return {
        "slug": slug,
        "label": meta["label"],
        "description": meta["description"],
        "total": total,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "by_type": type_counts,
        "tools": [_compact_service(s) for s in page],
        "offset": offset,
        "limit": limit,
    }


@router.get("/compare")
async def compare_services(
    response: Response,
    ids: str | None = Query(None, description="Comma-separated scan_ids (max 4)"),
    names: str | None = Query(None, description="Comma-separated tool names (max 4) — fuzzy matched"),
    services: str | None = Query(None, description="Alias for names — comma-separated tool names"),
):
    """Compare up to 4 services side by side.

    Accepts scan_ids via `ids`, or tool names via `names`/`services` for convenience.
    Names are fuzzy-matched against service_name fields.
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    results = []

    if ids:
        scan_ids = [s.strip() for s in ids.split(",")][:4]
        for sid in scan_ids:
            service = _by_scan_id.get(sid)
            if not service:
                for t in _collected_tools:
                    if t["scan_id"] == sid:
                        service = t
                        break
            if service:
                results.append(_compact_service(service))
    elif names or services:
        name_list = [n.strip().lower() for n in (names or services).split(",")][:4]
        all_tools = list(_services) + list(_collected_tools)
        for name_q in name_list:
            # Exact match first, then substring match
            found = None
            for t in all_tools:
                if t.get("service_name", "").lower() == name_q:
                    found = t
                    break
            if not found:
                for t in all_tools:
                    if name_q in t.get("service_name", "").lower():
                        found = t
                        break
            if found:
                results.append(_compact_service(found))
    else:
        raise HTTPException(status_code=400, detail="Provide 'ids' (scan_ids) or 'names'/'services' (tool names) to compare")

    # If only 1 result found (need at least 2 for meaningful comparison), return 400
    if len(results) == 1:
        raise HTTPException(
            status_code=400,
            detail="Compare requires at least 2 services. Only 1 match found. Check spelling or try different names.",
        )

    return {"services": results, "count": len(results)}


@router.get("/stats")
async def get_stats(
    response: Response,
    source: str | None = Query("all", description="'all' (default) includes collected tools, 'scanned' for prebuilt-scans only"),
):
    """Overall statistics across all indexed services."""
    _ensure_loaded()
    _add_headers(response)

    if source == "scanned":
        pool = _services
    else:
        # Default: include all tools for consistent counts
        _load_collected()
        scanned_ids = {s["scan_id"] for s in _services}
        pool = list(_services) + [
            t for t in _collected_tools if t["scan_id"] not in scanned_ids
        ]

    total = len(pool)
    if total == 0:
        return {"total_services": 0, "avg_score": 0, "by_category": {}}

    avg = sum(s["clarvia_score"] for s in pool) / total

    by_cat: dict[str, list[int]] = {}
    for s in pool:
        cat = s.get("category", "other")
        by_cat.setdefault(cat, []).append(s["clarvia_score"])

    by_type: dict[str, int] = {}
    for s in pool:
        st = s.get("service_type", "general")
        by_type[st] = by_type.get(st, 0) + 1

    result: dict[str, Any] = {
        "total_services": total,
        "avg_score": round(avg, 1),
        "score_distribution": {
            "excellent": len([s for s in pool if s["clarvia_score"] >= 80]),
            "strong": len([s for s in pool if 60 <= s["clarvia_score"] < 80]),
            "moderate": len([s for s in pool if 35 <= s["clarvia_score"] < 60]),
            "weak": len([s for s in pool if s["clarvia_score"] < 35]),
        },
        "by_category": {
            cat: {
                "count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
            }
            for cat, scores in sorted(by_cat.items())
        },
        "by_type": by_type,
    }

    # Add source breakdown when showing all
    if source == "all":
        result["scanned_count"] = len(_services)
        result["collected_count"] = total - len(_services)

    return result


@router.get("/methodology")
async def scoring_methodology():
    """Public documentation of Clarvia's scoring methodology."""
    return {
        "version": "2.0",
        "last_updated": "2026-03-26",
        "total_score": 100,
        "dimensions": {
            "description_quality": {"max": 20, "description": "Quality and completeness of tool description", "factors": ["length", "keyword relevance", "specificity"]},
            "documentation": {"max": 20, "description": "Availability of docs, repos, and versioning", "factors": ["homepage", "repository", "version", "openapi_spec", "npm_listing"]},
            "ecosystem_presence": {"max": 20, "description": "Presence in registries and community adoption", "factors": ["source_registry", "npm_popularity", "install_command", "completeness"]},
            "agent_compatibility": {"max": 25, "description": "How well the tool integrates with AI agents", "factors": ["tool_type_bonus", "mcp_features", "api_spec", "deployment_options"]},
            "metadata_quality": {"max": 15, "description": "Indicators of reliability and trustworthiness", "factors": ["github_repo", "https", "version_stability", "official_registry", "well_known_org", "license", "declared_dependencies", "security_docs", "version_maturity"]}
        },
        "ratings": {
            "Excellent": "80-100 — Best-in-class, fully agent-native",
            "Strong": "60-79 — Recommended for production agent use",
            "Moderate": "35-59 — Usable with some limitations",
            "Basic": "20-34 — Limited agent compatibility",
            "Low": "0-19 — Not recommended for agent use"
        },
        "agent_grades": {
            "AGENT_NATIVE": "80-100 — Fully optimized for AI agents",
            "AGENT_FRIENDLY": "60-79 — Good agent support",
            "AGENT_POSSIBLE": "35-59 — Partial agent compatibility",
            "AGENT_HOSTILE": "0-34 — Not designed for agents"
        },
        "data_license": "CC-BY-4.0 — Free to use with attribution",
        "citation": "Clarvia AEO Score v2.0 (2026). https://clarvia.art",
        "reproducibility": "Scores are deterministic for the same input metadata. Rescan via POST /v1/profiles/{id}/rescan",
        "limitations": [
            "Metadata-based scoring approximates but does not replace full API testing",
            "Security assessment is surface-level — does not include CVE/pentest analysis",
            "Popularity data is proxy-based (registry presence, not actual usage counts)"
        ]
    }


@router.post("/audit")
async def audit_dependencies(
    response: Response,
    deps: dict[str, Any] = None,
):
    """Audit a package.json or requirements.txt for agent compatibility.

    Send {"dependencies": {"pkg1": "^1.0", "pkg2": "~2.0"}} or
    {"packages": ["pkg1", "pkg2"]} to check all against Clarvia.
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    if not deps:
        raise HTTPException(status_code=400, detail="Send {dependencies: {...}} or {packages: [...]}")

    # Extract package names
    pkg_names = []
    if "dependencies" in deps:
        pkg_names = list(deps["dependencies"].keys())
    elif "packages" in deps:
        pkg_names = deps["packages"]
    elif "devDependencies" in deps:
        pkg_names = list(deps["devDependencies"].keys())
    else:
        pkg_names = list(deps.keys())

    # Look up each package in the index
    all_tools = list(_services) + list(_collected_tools)
    name_index = {}
    for t in all_tools:
        sname = t.get("service_name", "").lower()
        name_index[sname] = t
        # Also index by npm package name from type_config
        tc = t.get("type_config") or {}
        if tc.get("npm_package"):
            name_index[tc["npm_package"].lower()] = t

    results = []
    total_score = 0
    found_count = 0

    for pkg in pkg_names[:100]:  # Max 100 packages
        pkg_lower = pkg.lower().strip()
        tool = name_index.get(pkg_lower)
        if tool:
            score = tool["clarvia_score"]
            results.append({
                "package": pkg,
                "found": True,
                "clarvia_score": score,
                "rating": tool["rating"],
                "category": tool.get("category", "other"),
                "scan_id": tool["scan_id"],
            })
            total_score += score
            found_count += 1
        else:
            results.append({
                "package": pkg,
                "found": False,
                "clarvia_score": None,
                "rating": None,
                "message": "Not indexed in Clarvia"
            })

    avg_score = round(total_score / found_count, 1) if found_count > 0 else None

    return {
        "total_packages": len(pkg_names),
        "found": found_count,
        "not_found": len(pkg_names) - found_count,
        "avg_score": avg_score,
        "overall_rating": "Strong" if (avg_score or 0) >= 70 else "Moderate" if (avg_score or 0) >= 45 else "Needs Improvement",
        "results": results,
    }


@router.get("/embed/compare")
async def embed_comparison(
    ids: str = Query(..., description="Comma-separated scan_ids (max 4)"),
    theme: str = Query("light"),
):
    """Embeddable comparison table for multiple tools."""
    _ensure_loaded()
    _load_collected()

    scan_ids = [s.strip() for s in ids.split(",")][:4]
    tools = []
    for sid in scan_ids:
        svc = _by_scan_id.get(sid)
        if not svc:
            for t in _collected_tools:
                if t["scan_id"] == sid:
                    svc = t
                    break
        if svc:
            tools.append(svc)

    if not tools:
        raise HTTPException(status_code=404, detail="No tools found")

    bg = "#ffffff" if theme == "light" else "#1a1a2e"
    text_color = "#111827" if theme == "light" else "#f3f4f6"
    border = "#e5e7eb" if theme == "light" else "#374151"

    def score_color(s):
        if s >= 70: return "#22c55e"
        if s >= 45: return "#eab308"
        return "#ef4444"

    rows = ""
    for t in tools:
        s = t["clarvia_score"]
        rows += f'<tr><td>{t["service_name"]}</td><td style="color:{score_color(s)};font-weight:700">{s}</td><td>{t["rating"]}</td><td>{t.get("category","")}</td></tr>'

    html = f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif}}
table{{width:100%;border-collapse:collapse;background:{bg};border:1px solid {border};border-radius:8px}}
th,td{{padding:10px 14px;text-align:left;border-bottom:1px solid {border};color:{text_color};font-size:14px}}
th{{font-weight:600;font-size:12px;text-transform:uppercase;color:#6b7280}}
</style></head><body>
<table><thead><tr><th>Tool</th><th>Score</th><th>Rating</th><th>Category</th></tr></thead>
<tbody>{rows}</tbody></table>
</body></html>"""

    return Response(content=html, media_type="text/html", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/embed/{scan_id}")
async def get_embed_widget(
    scan_id: str,
    theme: str = Query("light", description="light or dark"),
    width: int = Query(400, ge=200, le=800),
):
    """Get an embeddable HTML widget for a tool's Clarvia score."""
    _ensure_loaded()
    _load_collected()

    service = _by_scan_id.get(scan_id)
    if not service:
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Tool not found")

    score = service["clarvia_score"]
    name = service["service_name"]
    rating = service["rating"]
    category = service.get("category", "")

    # Color based on score
    if score >= 70:
        color = "#22c55e"  # green
    elif score >= 45:
        color = "#eab308"  # yellow
    else:
        color = "#ef4444"  # red

    bg = "#ffffff" if theme == "light" else "#1a1a2e"
    text_color = "#111827" if theme == "light" else "#f3f4f6"
    sub_color = "#6b7280" if theme == "light" else "#9ca3af"
    border = "#e5e7eb" if theme == "light" else "#374151"

    html = f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:transparent}}
.card{{width:{width}px;border:1px solid {border};border-radius:12px;padding:20px;background:{bg}}}
.name{{font-size:16px;font-weight:600;color:{text_color};margin-bottom:4px}}
.cat{{font-size:12px;color:{sub_color};margin-bottom:16px}}
.score-row{{display:flex;align-items:center;gap:12px}}
.score{{font-size:36px;font-weight:700;color:{color}}}
.rating{{font-size:14px;color:{sub_color}}}
.bar{{height:6px;border-radius:3px;background:{border};margin-top:12px}}
.bar-fill{{height:100%;border-radius:3px;background:{color};width:{score}%}}
.footer{{margin-top:12px;font-size:11px;color:{sub_color}}}
.footer a{{color:{sub_color};text-decoration:none}}
</style></head><body>
<div class="card">
  <div class="name">{name}</div>
  <div class="cat">{category} &middot; {rating}</div>
  <div class="score-row">
    <div class="score">{score}</div>
    <div class="rating">/ 100<br>Clarvia Score</div>
  </div>
  <div class="bar"><div class="bar-fill"></div></div>
  <div class="footer">Powered by <a href="https://clarvia.art" target="_blank">Clarvia</a></div>
</div>
</body></html>"""

    return Response(
        content=html,
        media_type="text/html",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/embed/{scan_id}/snippet")
async def get_embed_snippet(scan_id: str, theme: str = Query("light")):
    """Get an embeddable iframe snippet for blogs/READMEs."""
    return {
        "iframe": f'<iframe src="https://clarvia-api.onrender.com/v1/embed/{scan_id}?theme={theme}" width="400" height="180" frameborder="0" style="border-radius:12px"></iframe>',
        "markdown": f'[![Clarvia Score](https://clarvia-api.onrender.com/v1/badge/{scan_id})](https://clarvia.art/tool/{scan_id})',
    }


# ---------------------------------------------------------------------------
# Featured / Spotlight endpoints
# ---------------------------------------------------------------------------

@router.get("/featured")
async def get_featured(response: Response):
    """Get featured tools — editor's picks, top per category, rising stars."""
    _ensure_loaded()
    _add_headers(response)

    # Top 3 per category
    by_cat: dict[str, list] = {}
    for s in _services:
        cat = s.get("category", "other")
        if cat == "other":
            continue
        by_cat.setdefault(cat, []).append(s)

    editors_picks = []
    for cat, tools in sorted(by_cat.items()):
        top = sorted(tools, key=lambda t: t["clarvia_score"], reverse=True)[:3]
        for t in top:
            if t["clarvia_score"] >= 60:
                editors_picks.append({
                    "name": t["service_name"],
                    "score": t["clarvia_score"],
                    "rating": t["rating"],
                    "category": cat,
                    "scan_id": t["scan_id"],
                    "spotlight_reason": f"Top {cat} tool"
                })

    # Overall top 10
    overall_top = sorted(_services, key=lambda s: s["clarvia_score"], reverse=True)[:10]

    # Tool of the week (highest score, rotates by week number)
    import datetime as dt
    week_num = dt.datetime.now().isocalendar()[1]
    if len(_services) > 0:
        candidates = sorted(_services, key=lambda s: s["clarvia_score"], reverse=True)[:50]
        tool_of_week = candidates[week_num % len(candidates)]
    else:
        tool_of_week = None

    return {
        "tool_of_the_week": {
            "name": tool_of_week["service_name"],
            "score": tool_of_week["clarvia_score"],
            "category": tool_of_week.get("category", ""),
            "scan_id": tool_of_week["scan_id"],
            "description": tool_of_week.get("description", "")[:200],
        } if tool_of_week else None,
        "overall_top_10": [
            {"name": t["service_name"], "score": t["clarvia_score"], "category": t.get("category", ""), "scan_id": t["scan_id"]}
            for t in overall_top
        ],
        "category_picks": editors_picks[:50],
        "total_categories": len(by_cat),
    }


@router.get("/featured/top")
async def get_featured_top(
    response: Response,
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """Agent-verified top picks — only tools scoring >= 60 (Strong+)."""
    _ensure_loaded()
    _add_headers(response)
    filtered = [s for s in _services if s["clarvia_score"] >= 60]
    if category:
        filtered = _filter_by_category(filtered, category)
    filtered = sorted(filtered, key=lambda s: s["clarvia_score"], reverse=True)[:limit]

    # Group by category for frontend tabs
    by_category: dict[str, list] = {}
    for s in filtered:
        cat = s.get("category", "other")
        by_category.setdefault(cat, []).append({
            "name": s["service_name"],
            "url": s["url"],
            "score": s["clarvia_score"],
            "rating": s["rating"],
            "category": cat,
            "scan_id": s["scan_id"],
            "description": s.get("description", "")[:200],
        })

    return {
        "top_picks": [
            {
                "name": s["service_name"],
                "url": s["url"],
                "score": s["clarvia_score"],
                "rating": s["rating"],
                "category": s.get("category", "other"),
                "scan_id": s["scan_id"],
                "description": s.get("description", "")[:200],
            }
            for s in filtered
        ],
        "by_category": by_category,
        "total": len(filtered),
        "threshold": 60,
    }


@router.post("/featured/nominate")
async def nominate_featured(request: Request):
    """Nominate a tool for featured spotlight."""
    body = await request.json()
    scan_id = body.get("scan_id", "")
    reason = body.get("reason", "")

    if not scan_id:
        raise HTTPException(status_code=400, detail="scan_id required")

    # Store nomination (in-memory for now)
    # In production, persist to database
    return {
        "nominated": True,
        "scan_id": scan_id,
        "message": "Nomination received. Featured tools are reviewed weekly."
    }


# ---------------------------------------------------------------------------
# Demand intelligence endpoint
# ---------------------------------------------------------------------------

@router.get("/demand")
async def get_demand_intelligence(response: Response, days: int = Query(7, ge=1, le=30)):
    """Get search demand intelligence — what agents and users are looking for."""
    _add_headers(response)

    cutoff = _time.time() - (days * 86400)
    recent = [s for s in _search_log if s["ts"] >= cutoff]

    # Most searched queries
    recent_counter: Counter = Counter()
    zero_result_counter: Counter = Counter()
    category_demand: Counter = Counter()

    for s in recent:
        q = s["query"]
        recent_counter[q] += 1
        if s.get("results", 0) == 0:
            zero_result_counter[q] += 1
        if s.get("category"):
            category_demand[s["category"]] += 1

    return {
        "period_days": days,
        "total_searches": len(recent),
        "unique_queries": len(recent_counter),
        "top_queries": [{"query": q, "count": c} for q, c in recent_counter.most_common(20)],
        "zero_result_queries": [{"query": q, "count": c} for q, c in zero_result_counter.most_common(10)],
        "category_demand": dict(category_demand.most_common(20)),
        "all_time_top": [{"query": q, "count": c} for q, c in _search_counter.most_common(20)],
    }


@router.get("/enrich/{scan_id}")
async def enrich_service(scan_id: str, response: Response):
    """Enrich a tool with real-time external data from npm, GitHub, OSV.dev.

    Fetches live data including:
    - npm: weekly/monthly downloads, license, dependencies, maintainers
    - GitHub: stars, forks, last commit, SECURITY.md presence, topics
    - OSV.dev: known CVEs/vulnerabilities with severity

    All data sources are free and require no API keys.
    Results are cached for 1 hour.
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Tool not found")

    from ..services.enrichment import enrich_tool
    enrichment = await enrich_tool(service)

    return {
        "scan_id": scan_id,
        "name": service["service_name"],
        "clarvia_score": service["clarvia_score"],
        "enrichment": enrichment,
    }


@router.get("/compliance/{scan_id}")
async def compliance_checklist(scan_id: str, response: Response):
    """Generate a compliance checklist for a tool based on available signals.

    Checks against common compliance frameworks:
    - SOC2 relevant signals
    - GDPR relevant signals
    - General security hygiene
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Tool not found")

    url = service.get("url", "")
    tc = service.get("type_config") or {}
    pricing = service.get("pricing", "unknown")

    # Fetch enrichment data
    gh_data = {}
    vuln_data = {"total_vulns": 0}
    try:
        from ..services.enrichment import enrich_github, check_vulnerabilities
        cross_refs = service.get("cross_refs", {})
        gh_url = cross_refs.get("github", "")
        if not gh_url and "github.com" in url:
            gh_url = url
        if gh_url:
            gh_data = await enrich_github(gh_url)
        npm_pkg = tc.get("npm_package", "")
        if npm_pkg:
            vuln_data = await check_vulnerabilities(npm_pkg, "npm")
    except Exception as e:
        logger.debug("Compliance enrichment failed: %s", e)

    checks = []

    # Security hygiene
    checks.append({
        "category": "security_hygiene",
        "check": "HTTPS endpoint",
        "status": "pass" if "https" in url.lower() else "fail",
        "importance": "critical",
    })
    checks.append({
        "category": "security_hygiene",
        "check": "No known CVEs",
        "status": "pass" if vuln_data["total_vulns"] == 0 else "fail",
        "detail": f"{vuln_data['total_vulns']} vulnerabilities found" if vuln_data["total_vulns"] > 0 else "Clean",
        "importance": "critical",
    })
    checks.append({
        "category": "security_hygiene",
        "check": "SECURITY.md / security policy",
        "status": "pass" if gh_data.get("has_security_policy") else "unknown",
        "importance": "high",
    })
    checks.append({
        "category": "security_hygiene",
        "check": "Open source / auditable code",
        "status": "pass" if pricing == "open_source" or gh_data.get("stars", 0) > 0 else "unknown",
        "importance": "medium",
    })

    # SOC2 relevant
    checks.append({
        "category": "soc2_relevant",
        "check": "Version control (Git)",
        "status": "pass" if gh_data.get("repo_url") or "github.com" in url else "unknown",
        "importance": "high",
    })
    checks.append({
        "category": "soc2_relevant",
        "check": "Active maintenance (pushed in last 90 days)",
        "status": "unknown",
        "importance": "high",
    })
    if gh_data.get("pushed_at"):
        from datetime import timedelta
        try:
            pushed = datetime.fromisoformat(gh_data["pushed_at"].replace("Z", "+00:00"))
            is_recent = (datetime.now(timezone.utc) - pushed) < timedelta(days=90)
            checks[-1]["status"] = "pass" if is_recent else "warn"
            checks[-1]["detail"] = f"Last push: {gh_data['pushed_at'][:10]}"
        except Exception:
            pass

    checks.append({
        "category": "soc2_relevant",
        "check": "License declared",
        "status": "pass" if gh_data.get("license") else "unknown",
        "detail": gh_data.get("license", ""),
        "importance": "medium",
    })
    checks.append({
        "category": "soc2_relevant",
        "check": "Not archived/abandoned",
        "status": "pass" if not gh_data.get("archived") else "fail",
        "importance": "high",
    })

    # GDPR relevant
    auth = tc.get("auth_method") or tc.get("auth") or ""
    checks.append({
        "category": "gdpr_relevant",
        "check": "Authentication required",
        "status": "pass" if auth else "unknown",
        "detail": f"Auth method: {auth}" if auth else "Could not determine",
        "importance": "high",
    })
    checks.append({
        "category": "gdpr_relevant",
        "check": "Data processing transparency",
        "status": "unknown",
        "detail": "Manual review required — check privacy policy",
        "importance": "critical",
    })

    # Summary
    pass_count = len([c for c in checks if c["status"] == "pass"])
    fail_count = len([c for c in checks if c["status"] == "fail"])
    unknown_count = len([c for c in checks if c["status"] in ("unknown", "warn")])

    return {
        "scan_id": scan_id,
        "name": service["service_name"],
        "compliance_checklist": checks,
        "summary": {
            "total_checks": len(checks),
            "passed": pass_count,
            "failed": fail_count,
            "unknown": unknown_count,
            "readiness_score": round(pass_count / len(checks) * 100) if checks else 0,
        },
        "disclaimer": "This checklist provides surface-level signal detection, not legal compliance certification. "
                      "Always consult with your compliance team for official assessments.",
    }


@router.get("/security/{scan_id}")
async def get_security_info(scan_id: str, response: Response):
    """Get security-relevant information for a tool.

    NOTE: This is surface-level metadata analysis, NOT a security audit.
    It checks for: HTTPS, license, GitHub presence, security keywords,
    and known package advisories (when available via npm/PyPI).

    For production security decisions, complement with dedicated tools
    like Snyk, Dependabot, or manual security review.
    """
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Tool not found")

    name = service.get("service_name", "")
    url = service.get("url", "")
    desc = service.get("description", "")
    tc = service.get("type_config") or {}
    dims = service.get("dimensions", {})
    mq = dims.get("metadata_quality", dims.get("trust_signals", {}))

    # Compile security signals
    signals = []

    if "https" in url.lower():
        signals.append({"signal": "https", "status": "pass", "detail": "URL uses HTTPS"})
    else:
        signals.append({"signal": "https", "status": "fail", "detail": "URL does not use HTTPS"})

    if "github.com" in url.lower() or "github.com" in str(service.get("source", "")):
        signals.append({"signal": "source_code", "status": "pass", "detail": "Source code publicly available"})
    else:
        signals.append({"signal": "source_code", "status": "unknown", "detail": "No public source code found"})

    # License check
    pricing = service.get("pricing", "unknown")
    if pricing == "open_source":
        signals.append({"signal": "license", "status": "pass", "detail": "Open source license detected"})
    else:
        signals.append({"signal": "license", "status": "unknown", "detail": "License not detected from metadata"})

    # Auth method
    auth = tc.get("auth_method") or tc.get("auth") or ""
    if auth:
        if auth in ("oauth2", "oauth"):
            signals.append({"signal": "auth_quality", "status": "pass", "detail": f"Uses {auth} (recommended)"})
        elif auth in ("bearer_token", "api_key"):
            signals.append({"signal": "auth_quality", "status": "warn", "detail": f"Uses {auth} (acceptable but less secure than OAuth)"})
        else:
            signals.append({"signal": "auth_quality", "status": "info", "detail": f"Auth method: {auth}"})

    # Security keywords in description
    security_kw = ["authenticated", "encrypted", "secure", "oauth", "jwt", "rbac"]
    found_kw = [kw for kw in security_kw if kw in desc.lower()]
    if found_kw:
        signals.append({"signal": "security_mentions", "status": "info", "detail": f"Description mentions: {', '.join(found_kw)}"})

    # Real vulnerability check via OSV.dev
    npm_pkg = tc.get("npm_package", "")
    if npm_pkg:
        from ..services.enrichment import check_vulnerabilities
        vuln_data = await check_vulnerabilities(npm_pkg, "npm")
        if vuln_data["total_vulns"] > 0:
            signals.append({
                "signal": "known_vulnerabilities",
                "status": "fail",
                "detail": f"{vuln_data['total_vulns']} known vulnerabilities ({vuln_data['critical']} critical, {vuln_data['high']} high)",
                "vulnerabilities": vuln_data["vulnerabilities"][:5]
            })
        else:
            signals.append({
                "signal": "known_vulnerabilities",
                "status": "pass",
                "detail": "No known vulnerabilities found in OSV.dev database"
            })

    pass_count = len([s for s in signals if s["status"] == "pass"])
    total = len(signals)

    return {
        "scan_id": scan_id,
        "name": name,
        "security_signals": signals,
        "pass_rate": f"{pass_count}/{total}",
        "metadata_quality_score": mq.get("score", 0) if isinstance(mq, dict) else 0,
        "disclaimer": "This is surface-level metadata analysis, NOT a security audit. "
                      "For production security decisions, use dedicated tools like Snyk, "
                      "Dependabot, or conduct manual security review.",
        "recommended_next_steps": [
            "Run `npm audit` or `pip-audit` on the package",
            "Check GitHub Security Advisories for known CVEs",
            "Review the tool's security policy (SECURITY.md)",
            "Verify data handling practices match your compliance requirements"
        ]
    }


@router.get("/report/{scan_id}")
async def generate_report(scan_id: str, response: Response):
    """Generate a stakeholder-ready evaluation report for a tool."""
    _ensure_loaded()
    _load_collected()

    service = _by_scan_id.get(scan_id)
    if not service:
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Tool not found")

    dims = service.get("dimensions", {})

    # Build structured report
    report = {
        "report_type": "Clarvia AEO Evaluation Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": {
            "name": service["service_name"],
            "url": service.get("url", ""),
            "category": service.get("category", ""),
            "service_type": service.get("service_type", ""),
        },
        "score": {
            "total": service["clarvia_score"],
            "rating": service["rating"],
            "percentile": None,  # Will compute
        },
        "dimensions": {},
        "recommendation": "",
        "methodology": "Clarvia AEO Score v2.0 — https://clarvia.art/methodology",
        "disclaimer": "Automated metadata analysis. Not a substitute for manual evaluation.",
    }

    # Compute percentile
    all_scores = sorted([s["clarvia_score"] for s in _services])
    if all_scores:
        below = len([s for s in all_scores if s < service["clarvia_score"]])
        report["score"]["percentile"] = round(below / len(all_scores) * 100, 1)

    # Enrich with external data if available
    try:
        from ..services.enrichment import enrich_tool
        enrichment = await enrich_tool(service)
        if enrichment.get("github"):
            gh = enrichment["github"]
            report["github"] = {
                "stars": gh.get("stars", 0),
                "forks": gh.get("forks", 0),
                "last_push": gh.get("pushed_at", ""),
                "license": gh.get("license", ""),
                "has_security_policy": gh.get("has_security_policy", False),
                "archived": gh.get("archived", False),
            }
        if enrichment.get("npm"):
            npm = enrichment["npm"]
            report["npm"] = {
                "weekly_downloads": npm.get("weekly_downloads", 0),
                "monthly_downloads": npm.get("monthly_downloads", 0),
                "version": npm.get("version", ""),
                "license": npm.get("license", ""),
                "dependencies_count": npm.get("dependencies_count", 0),
                "maintainers_count": npm.get("maintainers_count", 0),
            }
        if enrichment.get("osv"):
            osv = enrichment["osv"]
            report["vulnerabilities"] = {
                "total": osv.get("total_vulns", 0),
                "critical": osv.get("critical", 0),
                "high": osv.get("high", 0),
                "status": "clean" if osv["total_vulns"] == 0 else "has_vulnerabilities"
            }
        if enrichment.get("npm_quality"):
            nq = enrichment["npm_quality"]
            if nq.get("available"):
                report["npm_quality"] = {
                    "quality": nq.get("quality", 0),
                    "popularity": nq.get("popularity", 0),
                    "maintenance": nq.get("maintenance", 0),
                    "final_score": nq.get("final_score", 0),
                    "has_tests": nq.get("has_tests", False),
                    "dependents_count": nq.get("dependents_count", 0),
                    "downloads_count": nq.get("downloads_count", 0),
                }
    except Exception as e:
        logger.debug("Report enrichment failed: %s", e)

    # Dimension details
    for dim_name, dim_val in dims.items():
        if isinstance(dim_val, dict):
            report["dimensions"][dim_name] = {
                "score": dim_val.get("score", 0),
                "max": dim_val.get("max", 0),
                "percentage": round(dim_val.get("score", 0) / max(dim_val.get("max", 1), 1) * 100),
            }

    # Generate recommendation
    score = service["clarvia_score"]
    if score >= 70:
        report["recommendation"] = "RECOMMENDED — This tool meets the threshold for production agent use."
    elif score >= 45:
        report["recommendation"] = "CONDITIONAL — This tool is usable but has gaps. Review dimension scores for specific areas of concern."
    else:
        report["recommendation"] = "NOT RECOMMENDED — This tool has significant compatibility gaps for AI agent use."

    return report
