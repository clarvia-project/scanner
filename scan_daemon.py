#!/usr/bin/env python3
"""
Clarvia Scanner Daemon - scans remaining services with rate limit handling.
Runs as background process, sleeps between batches.
"""
import json
import time
import requests
import sys
import os
from datetime import datetime, timezone

OUTPUT_PATH = "/Users/sangho/클로드 코드/scanner/data/prebuilt-scans.json"
LOG_PATH = "/Users/sangho/클로드 코드/scanner/data/scan_daemon.log"
API_URL = "https://clarvia-api.onrender.com/api/scan"
BATCH_SIZE = 9
WAIT_BETWEEN_BATCHES = 3300  # 55 minutes

ALL_SERVICES = [
    ("OpenAI", "https://openai.com"),
    ("Anthropic", "https://anthropic.com"),
    ("Google AI", "https://ai.google.dev"),
    ("Mistral", "https://mistral.ai"),
    ("Cohere", "https://cohere.com"),
    ("Replicate", "https://replicate.com"),
    ("Hugging Face", "https://huggingface.co"),
    ("Together AI", "https://together.ai"),
    ("Groq", "https://groq.com"),
    ("Perplexity", "https://perplexity.ai"),
    ("GitHub", "https://github.com"),
    ("GitLab", "https://gitlab.com"),
    ("Vercel", "https://vercel.com"),
    ("Netlify", "https://netlify.com"),
    ("Supabase", "https://supabase.com"),
    ("Firebase", "https://firebase.google.com"),
    ("AWS", "https://aws.amazon.com"),
    ("Cloudflare", "https://cloudflare.com"),
    ("Railway", "https://railway.app"),
    ("Render", "https://render.com"),
    ("Stripe", "https://stripe.com"),
    ("PayPal", "https://paypal.com"),
    ("Square", "https://squareup.com"),
    ("Plaid", "https://plaid.com"),
    ("Coinbase", "https://coinbase.com"),
    ("Circle", "https://circle.com"),
    ("Slack", "https://slack.com"),
    ("Discord", "https://discord.com"),
    ("Twilio", "https://twilio.com"),
    ("SendGrid", "https://sendgrid.com"),
    ("Resend", "https://resend.com"),
    ("Snowflake", "https://snowflake.com"),
    ("Databricks", "https://databricks.com"),
    ("Mixpanel", "https://mixpanel.com"),
    ("Amplitude", "https://amplitude.com"),
    ("Segment", "https://segment.com"),
    ("Notion", "https://notion.so"),
    ("Linear", "https://linear.app"),
    ("Jira", "https://atlassian.com/software/jira"),
    ("Asana", "https://asana.com"),
    ("Figma", "https://figma.com"),
    ("Canva", "https://canva.com"),
    ("Solana", "https://solana.com"),
    ("Ethereum", "https://ethereum.org"),
    ("Helius", "https://helius.dev"),
    ("Alchemy", "https://alchemy.com"),
    ("Moralis", "https://moralis.io"),
    ("Dune", "https://dune.com"),
    ("MCP.so", "https://mcp.so"),
    ("Smithery.ai", "https://smithery.ai"),
    ("Glama.ai", "https://glama.ai"),
]

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def load_results():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    return []

def save_results(results):
    results.sort(key=lambda x: (x.get("clarvia_score") or 0), reverse=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def scan_one(name, url):
    try:
        resp = requests.post(API_URL, json={"url": url}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "url": url,
                "service_name": name,
                "clarvia_score": data.get("clarvia_score"),
                "rating": data.get("rating"),
                "dimensions": data.get("dimensions"),
                "scan_id": data.get("scan_id"),
                "scanned_at": datetime.now(timezone.utc).isoformat()
            }
        elif resp.status_code == 429:
            return "RATE_LIMITED"
        else:
            log(f"  HTTP {resp.status_code}")
            return None
    except Exception as e:
        log(f"  ERROR: {e}")
        return None

def main():
    results = load_results()
    scanned_urls = {r["url"] for r in results}
    remaining = [(n, u) for n, u in ALL_SERVICES if u not in scanned_urls]
    
    log(f"Daemon started. Scanned: {len(scanned_urls)}, Remaining: {len(remaining)}")
    
    while remaining:
        batch = remaining[:BATCH_SIZE]
        log(f"--- Batch of {len(batch)} starting ---")
        
        for name, url in batch:
            log(f"Scanning {name} ({url})...")
            result = scan_one(name, url)
            
            if result == "RATE_LIMITED":
                log(f"  Rate limited! Waiting {WAIT_BETWEEN_BATCHES//60}min...")
                time.sleep(WAIT_BETWEEN_BATCHES)
                # Retry
                result = scan_one(name, url)
                if result == "RATE_LIMITED":
                    log(f"  Still rate limited. Skipping.")
                    continue
            
            if result and result != "RATE_LIMITED":
                results.append(result)
                scanned_urls.add(url)
                save_results(results)
                log(f"  Score: {result['clarvia_score']}, Rating: {result['rating']}")
            
            time.sleep(3)
        
        remaining = [(n, u) for n, u in ALL_SERVICES if u not in scanned_urls]
        
        if remaining:
            log(f"Batch done. {len(remaining)} remaining. Waiting {WAIT_BETWEEN_BATCHES//60}min for rate limit reset...")
            time.sleep(WAIT_BETWEEN_BATCHES)
    
    log(f"ALL DONE! Total: {len(results)} services scanned.")
    save_results(results)

if __name__ == "__main__":
    main()
