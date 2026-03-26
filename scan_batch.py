import json
import time
import requests
from datetime import datetime, timezone

# Load existing results
output_path = "/Users/sangho/클로드 코드/scanner/data/prebuilt-scans.json"
with open(output_path) as f:
    existing = json.load(f)

scanned_urls = {r["url"] for r in existing}

all_services = [
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

remaining = [(n, u) for n, u in all_services if u not in scanned_urls]
print(f"Already scanned: {len(scanned_urls)}, Remaining: {len(remaining)}")

API_URL = "https://clarvia-api.onrender.com/api/scan"
results = list(existing)
batch_count = 0
total_remaining = len(remaining)

for i, (name, url) in enumerate(remaining, 1):
    # Rate limit: 10 per hour. After every 9 scans, wait 55 minutes.
    if batch_count >= 9:
        wait_secs = 55 * 60
        print(f"\n--- Rate limit approaching. Waiting {wait_secs//60} minutes... ---", flush=True)
        time.sleep(wait_secs)
        batch_count = 0
    
    print(f"[{len(results)+1}/51] Scanning {name} ({url})...", flush=True)
    try:
        resp = requests.post(API_URL, json={"url": url}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "url": url,
                "service_name": name,
                "clarvia_score": data.get("clarvia_score"),
                "rating": data.get("rating"),
                "dimensions": data.get("dimensions"),
                "scan_id": data.get("scan_id"),
                "scanned_at": datetime.now(timezone.utc).isoformat()
            }
            results.append(result)
            batch_count += 1
            print(f"  -> Score: {data.get('clarvia_score')}, Rating: {data.get('rating')}", flush=True)
        elif resp.status_code == 429:
            # Parse retry time
            try:
                retry_after = resp.json().get("retry_after", 3600)
            except:
                retry_after = 3600
            wait = min(retry_after + 10, 3700)
            print(f"  -> Rate limited. Waiting {wait//60}m {wait%60}s...", flush=True)
            time.sleep(wait)
            batch_count = 0
            # Retry this one
            resp2 = requests.post(API_URL, json={"url": url}, timeout=60)
            if resp2.status_code == 200:
                data = resp2.json()
                result = {
                    "url": url,
                    "service_name": name,
                    "clarvia_score": data.get("clarvia_score"),
                    "rating": data.get("rating"),
                    "dimensions": data.get("dimensions"),
                    "scan_id": data.get("scan_id"),
                    "scanned_at": datetime.now(timezone.utc).isoformat()
                }
                results.append(result)
                batch_count += 1
                print(f"  -> Retry OK. Score: {data.get('clarvia_score')}, Rating: {data.get('rating')}", flush=True)
            else:
                print(f"  -> Retry FAILED ({resp2.status_code})", flush=True)
        else:
            print(f"  -> FAILED (HTTP {resp.status_code})", flush=True)
    except Exception as e:
        print(f"  -> ERROR: {e}", flush=True)
    
    # Save progress after each scan
    results_sorted = sorted(results, key=lambda x: (x.get("clarvia_score") or 0), reverse=True)
    with open(output_path, "w") as f:
        json.dump(results_sorted, f, indent=2, ensure_ascii=False)
    
    if i < total_remaining:
        time.sleep(3)

print(f"\nDone! {len(results)}/51 services scanned total.")
