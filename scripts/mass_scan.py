#!/usr/bin/env python3
"""Mass scan 200+ services for Clarvia leaderboard."""
import asyncio
import json
import sys
import time

import aiohttp

API_URL = "http://localhost:8002/api/scan"

SERVICES = [
    # AI/LLM APIs
    "https://openai.com", "https://anthropic.com", "https://ai.google.dev",
    "https://mistral.ai", "https://cohere.com", "https://replicate.com",
    "https://together.ai", "https://fireworks.ai", "https://groq.com",
    "https://deepseek.com", "https://perplexity.ai", "https://huggingface.co",
    "https://stability.ai", "https://midjourney.com",
    "https://elevenlabs.io", "https://assemblyai.com", "https://deepgram.com",
    "https://runpod.io", "https://modal.com", "https://anyscale.com",
    "https://baseten.co", "https://banana.dev", "https://lepton.ai",
    "https://cerebras.ai", "https://sambanova.ai",

    # Developer Tools
    "https://github.com", "https://gitlab.com", "https://bitbucket.org",
    "https://vercel.com", "https://netlify.com", "https://railway.app",
    "https://fly.io", "https://render.com", "https://heroku.com",
    "https://digitalocean.com", "https://linode.com", "https://vultr.com",
    "https://cloudflare.com", "https://fastly.com", "https://akamai.com",
    "https://supabase.com", "https://firebase.google.com", "https://neon.tech",
    "https://planetscale.com", "https://cockroachlabs.com", "https://turso.tech",
    "https://upstash.com", "https://redis.io", "https://mongodb.com",

    # Communication/Email
    "https://twilio.com", "https://sendgrid.com", "https://resend.com",
    "https://postmark.com", "https://mailgun.com", "https://brevo.com",
    "https://pusher.com", "https://ably.com", "https://stream.io",

    # Payment/Fintech
    "https://stripe.com", "https://paypal.com", "https://square.com",
    "https://plaid.com", "https://wise.com", "https://revolut.com",
    "https://adyen.com", "https://braintreepayments.com",

    # Search/Vector DBs
    "https://pinecone.io", "https://weaviate.io", "https://qdrant.tech",
    "https://milvus.io", "https://zilliz.com", "https://elastic.co",
    "https://algolia.com", "https://typesense.org", "https://meilisearch.com",

    # Analytics/Data
    "https://mixpanel.com", "https://amplitude.com", "https://segment.com",
    "https://posthog.com", "https://plausible.io", "https://datadog.com",
    "https://grafana.com", "https://newrelic.com", "https://sentry.io",
    "https://logtail.com", "https://axiom.co",

    # Crypto/Web3
    "https://alchemy.com", "https://moralis.io", "https://helius.dev",
    "https://solana.com", "https://ethereum.org", "https://polygon.technology",
    "https://thegraph.com", "https://chainlink.com", "https://infura.io",
    "https://quicknode.com", "https://ankr.com", "https://tatum.io",
    "https://nansen.ai", "https://dune.com", "https://defined.fi",
    "https://birdeye.so", "https://jup.ag", "https://raydium.io",

    # Auth/Identity
    "https://auth0.com", "https://clerk.com", "https://stytch.com",
    "https://workos.com", "https://fusionauth.io", "https://supertokens.com",

    # CMS/Content
    "https://contentful.com", "https://sanity.io", "https://strapi.io",
    "https://prismic.io", "https://hygraph.com", "https://directus.io",

    # CI/CD/DevOps
    "https://circleci.com", "https://travis-ci.com", "https://buildkite.com",
    "https://semaphoreci.com", "https://earthly.dev", "https://dagger.io",

    # Design/Media
    "https://canva.com", "https://figma.com", "https://cloudinary.com",
    "https://imgix.com", "https://uploadthing.com", "https://uploadcare.com",

    # Productivity/SaaS
    "https://notion.so", "https://slack.com", "https://linear.app",
    "https://asana.com", "https://monday.com", "https://clickup.com",
    "https://airtable.com", "https://retool.com", "https://appsmith.com",

    # MCP-specific
    "https://smithery.ai", "https://glama.ai", "https://mcp.so",
    "https://modelcontextprotocol.io",

    # Testing/QA
    "https://playwright.dev", "https://cypress.io", "https://browserstack.com",
    "https://lambdatest.com",

    # Misc APIs
    "https://openweathermap.org", "https://newsapi.org",
    "https://serpapi.com", "https://scrapingbee.com", "https://apify.com",
    "https://rapidapi.com", "https://postman.com", "https://insomnia.rest",
    "https://hoppscotch.io",

    # AI Agent Frameworks
    "https://langchain.com", "https://llamaindex.ai", "https://crewai.com",
    "https://autogen.microsoft.com", "https://docs.agno.com",
    "https://mastra.ai", "https://composio.dev",

    # More developer services
    "https://doppler.com", "https://vault.hashicorp.com",
    "https://launchdarkly.com", "https://flagsmith.com",
    "https://novu.co", "https://knock.app",
    "https://inngest.com", "https://trigger.dev",
    "https://temporal.io", "https://prefect.io",

    # Documentation
    "https://readme.com", "https://mintlify.com", "https://gitbook.com",
    "https://docusaurus.io", "https://nextra.site",

    # E-commerce
    "https://shopify.com", "https://snipcart.com", "https://medusa-commerce.com",
    "https://saleor.io",

    # Maps/Location
    "https://mapbox.com", "https://here.com", "https://opencagedata.com",

    # Storage
    "https://backblaze.com", "https://wasabi.com", "https://storj.io",
    "https://filebase.com",
]

async def scan_one(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore) -> dict | None:
    async with sem:
        try:
            async with session.post(API_URL, json={"url": url}, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    score = data.get("clarvia_score", 0)
                    name = data.get("service_name", "?")
                    print(f"  OK  {url} -> {name} score={score}")
                    return data
                else:
                    text = await resp.text()
                    print(f"  ERR {url} -> {resp.status}")
                    return None
        except Exception as e:
            print(f"  ERR {url} -> {type(e).__name__}")
            return None


async def main():
    # Deduplicate
    urls = list(dict.fromkeys(SERVICES))
    print(f"Scanning {len(urls)} services...")
    start = time.time()

    sem = asyncio.Semaphore(3)  # 3 concurrent scans
    results = []

    async with aiohttp.ClientSession() as session:
        tasks = [scan_one(session, url, sem) for url in urls]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)

    elapsed = time.time() - start
    print(f"\nCompleted: {len(results)}/{len(urls)} in {elapsed:.1f}s")

    # Sort by score descending
    results.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)

    # Save
    for path in [
        "./data/prebuilt-scans.json",
        "./backend/data/prebuilt-scans.json",
    ]:
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved to {path}")

    # Summary
    scores = [r.get("clarvia_score", 0) for r in results]
    print(f"\nSummary:")
    print(f"  Total: {len(results)}")
    print(f"  Avg: {sum(scores)/len(scores):.1f}")
    print(f"  Max: {max(scores)} ({results[0].get('service_name')})")
    print(f"  Min: {min(scores)} ({results[-1].get('service_name')})")

    # Grade distribution
    from collections import Counter
    ratings = Counter(r.get("rating", "?") for r in results)
    print(f"  Ratings: {dict(ratings)}")


if __name__ == "__main__":
    asyncio.run(main())
