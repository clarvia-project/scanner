#!/usr/bin/env python3
"""
Keyword-based category re-classification for Clarvia's prebuilt-scans.json.

Usage:
    python3 scripts/reclassify_categories.py --dry-run   # preview only
    python3 scripts/reclassify_categories.py             # apply changes
"""

import argparse
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "prebuilt-scans.json"

# ---------------------------------------------------------------------------
# Keyword rules — ordered by specificity (more specific first)
# Each value is a list of lowercase substrings to match against
# name + description combined (lowercased).
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    # --- Existing categories we want to EXPAND ---
    "blockchain": [
        "blockchain", "ethereum", "solana", "web3", "nft", "defi",
        "crypto", "wallet", "smart contract", "token contract",
        "erc-20", "erc20", "erc721", "polygon", "avalanche",
        "arbitrum", "optimism", "base chain", "tenderly", "alchemy",
        "infura", "moralis", "thirdweb", "helius", "anchor protocol",
        "raydium", "serum", "jupiter swap",
    ],
    "security": [
        "authentication", "oauth", "jwt", "permission", "firewall",
        "audit trail", "compliance", "secret manager", "vault",
        "sso", "saml", "2fa", "two-factor", "mfa", "multi-factor",
        "password", "rbac", "access control", "penetration", "pentest",
        "vulnerability", "siem", "intrusion", "zero trust", "identity",
        "okta", "auth0", "keycloak", "ldap", "active directory",
    ],
    "database": [
        "database", " sql ", "postgresql", "postgres", "mysql",
        "mongodb", "redis", "supabase", "sqlite", "db ", "query",
        "orm ", "nosql", "dynamodb", "firestore", "cassandra",
        "clickhouse", "bigquery", "snowflake", "cockroachdb", "planetscale",
        "neon db", "turso", "prisma", "drizzle", "typeorm",
        "data warehouse", "relational", "schema migration",
    ],
    "search": [
        "search engine", "full-text search", "elasticsearch",
        "algolia", "meilisearch", "typesense", "vector search",
        "semantic search", "retrieval", "embedding search",
        "pinecone", "weaviate", "qdrant", "chroma", "faiss",
        "opensearch", "solr", "lucene",
    ],
    "communication": [
        "slack", "telegram", "discord", "whatsapp", "sms",
        "webhook", "notification", "chat api", "messaging api",
        "push notification", "twilio", "sendgrid", "mailgun",
        "postmark", "vonage", "nexmo", "bandwidth", "telnyx",
        "ringcentral", "zoom", "teams api", "intercom",
    ],
    "email": [
        "email api", "email service", "transactional email",
        "email delivery", "email marketing", "newsletter",
        "mailchimp", "sendgrid", "mailgun", "postmark",
        "sendinblue", "brevo", "constant contact", "klaviyo",
        "smtp", "imap", "email verification",
    ],
    "storage": [
        "file storage", "object storage", "cloud storage",
        "s3 bucket", "blob storage", "cdn ", "r2 storage",
        "gcs bucket", "azure blob", "cloudinary", "imgix",
        "uploadthing", "uploadcare", "file upload", "media storage",
    ],
    "monitoring": [
        "monitoring", "logging", "log management", "metrics",
        "observability", "distributed tracing", "alerting",
        "sentry", "datadog", "new relic", "grafana", "prometheus",
        "opentelemetry", "pagerduty", "uptime", "status page",
        "error tracking", "apm ", "application performance",
    ],
    "payments": [
        "payment", "stripe", "billing", "subscription",
        "invoice", "checkout", "revenue", "paypal", "braintree",
        "adyen", "square", "klarna", "afterpay", "chargebee",
        "recurly", "paddle", "lemon squeezy", "merchant",
        "card processing", "pci ",
    ],
    "cms": [
        " cms ", "content management", "wordpress",
        "contentful", "sanity.io", "strapi", "headless cms",
        "directus", "payload cms", "ghost blog", "storyblok",
        "prismic", "kentico", "sitecore", "drupal", "joomla",
    ],
    "data_analytics": [
        "data pipeline", "etl ", "data transformation",
        "data visualization", "dashboard analytics", "business intelligence",
        "bi tool", "dbt ", "airbyte", "fivetran", "stitch",
        "tableau", "looker", "metabase", "apache spark",
        "data lake", "data lakehouse", "segment.io", "mixpanel",
        "amplitude", "posthog", "heap analytics",
    ],
    "productivity": [
        "calendar api", "task management", "to-do", "project management",
        "jira", "linear.app", "notion api", "asana", "trello",
        "monday.com", "basecamp", "clickup", "airtable",
        "time tracking", "scheduling", "meeting", "booking",
        "google workspace", "microsoft 365", "office 365",
    ],
    "ecommerce": [
        "ecommerce", "e-commerce", "shopify", "woocommerce",
        "magento", "bigcommerce", "product catalog", "cart",
        "inventory", "order management", "fulfillment",
        "shipping api", "vtex", "commerce layer",
    ],
    "financial": [
        "banking api", "fintech", "open banking", "plaid",
        "financial data", "stock market", "trading api",
        "investment", "portfolio", "forex", "currency conversion",
        "exchange rate", "mastercard", "visa api", "swift",
        "ach transfer", "wire transfer",
    ],
    "healthcare": [
        "healthcare", "medical", "ehr ", "fhir", "hl7",
        "patient data", "clinical", "pharmacy", "drug",
        "diagnosis", "telemedicine", "health record",
        "infermedica", "epic systems",
    ],
    "maps_location": [
        "mapping", "geolocation", "geocoding", "routing",
        "navigation", "google maps", "mapbox", "here maps",
        "openstreetmap", "geospatial", "coordinates", "latitude",
        "ip geolocation", "address validation",
    ],
    "social": [
        "social media", "twitter api", "x api", "instagram api",
        "facebook api", "linkedin api", "youtube api",
        "tiktok api", "reddit api", "social graph",
        "social login", "feed api",
    ],
    "machine_learning": [
        "machine learning", "deep learning", "neural network",
        "computer vision", "image recognition", "nlp ",
        "natural language", "sentiment analysis", "classification",
        "regression", "hugging face", "tensorflow", "pytorch",
        "scikit-learn", "model training", "inference api",
    ],
}

# Mapping normalized category names to canonical values
# (keeps existing categories consistent)
CANONICAL_MAP: dict[str, str] = {
    "payments": "payment",
    "email": "communication",
    "maps_location": "location",
    "machine_learning": "ai",
    "data_analytics": "analytics",
}


def classify_tool(name: str, description: str) -> str | None:
    """Return a category if keywords match, else None."""
    text = f"{name} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                canonical = CANONICAL_MAP.get(category, category)
                return canonical
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-classify 'other' tools by keyword matching")
    parser.add_argument("--dry-run", action="store_true", help="Preview only — do not write")
    parser.add_argument("--all", action="store_true", help="Re-classify ALL tools, not just 'other'")
    args = parser.parse_args()

    print(f"Loading {DATA_FILE} ...")
    with open(DATA_FILE, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    print(f"Total tools: {len(data)}")

    # Count before
    before_counts = Counter(item.get("category", "MISSING") for item in data)
    print(f"\nCurrent distribution (top 15):")
    for cat, count in sorted(before_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {cat}: {count}")

    # Classify
    moved: dict[str, list[str]] = defaultdict(list)  # new_category -> [tool names]
    unchanged = 0
    no_match = 0

    for item in data:
        current = item.get("category", "other")
        should_reclassify = (current == "other") or args.all

        if not should_reclassify:
            unchanged += 1
            continue

        new_cat = classify_tool(
            item.get("service_name", ""),
            item.get("description", ""),
        )

        if new_cat and new_cat != current:
            moved[new_cat].append(item.get("service_name", "?"))
            if not args.dry_run:
                item["category"] = new_cat
        else:
            no_match += 1

    # Summary
    total_moved = sum(len(v) for v in moved.values())
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Re-classification results:")
    print(f"  Tools examined:   {len(data) - unchanged}")
    print(f"  Would reclassify: {total_moved}")
    print(f"  No match found:   {no_match}")
    print(f"\nBreakdown by new category:")
    for cat, tools in sorted(moved.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(tools)}")
        for t in tools[:5]:
            print(f"    - {t}")
        if len(tools) > 5:
            print(f"    ... and {len(tools) - 5} more")

    if args.dry_run:
        print("\nDry run complete. Run without --dry-run to apply changes.")
        return

    # Backup
    backup_path = DATA_FILE.with_suffix(f".pre-reclassify-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    shutil.copy2(DATA_FILE, backup_path)
    print(f"\nBackup saved: {backup_path.name}")

    # Write
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
    print(f"Written: {DATA_FILE}")

    # After counts
    after_counts = Counter(item.get("category", "MISSING") for item in data)
    print(f"\nAfter distribution (top 15):")
    for cat, count in sorted(after_counts.items(), key=lambda x: -x[1])[:15]:
        delta = count - before_counts.get(cat, 0)
        sign = f"+{delta}" if delta > 0 else str(delta)
        print(f"  {cat}: {count}  ({sign})")

    print("\nDone.")


if __name__ == "__main__":
    main()
