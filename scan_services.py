import json
import time
import requests
from datetime import datetime, timezone

services = [
    # AI/LLM
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
    # Developer Tools
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
    # Payment/Fintech
    ("Stripe", "https://stripe.com"),
    ("PayPal", "https://paypal.com"),
    ("Square", "https://squareup.com"),
    ("Plaid", "https://plaid.com"),
    ("Coinbase", "https://coinbase.com"),
    ("Circle", "https://circle.com"),
    # Communication
    ("Slack", "https://slack.com"),
    ("Discord", "https://discord.com"),
    ("Twilio", "https://twilio.com"),
    ("SendGrid", "https://sendgrid.com"),
    ("Resend", "https://resend.com"),
    # Data/Analytics
    ("Snowflake", "https://snowflake.com"),
    ("Databricks", "https://databricks.com"),
    ("Mixpanel", "https://mixpanel.com"),
    ("Amplitude", "https://amplitude.com"),
    ("Segment", "https://segment.com"),
    # Productivity
    ("Notion", "https://notion.so"),
    ("Linear", "https://linear.app"),
    ("Jira", "https://atlassian.com/software/jira"),
    ("Asana", "https://asana.com"),
    ("Figma", "https://figma.com"),
    ("Canva", "https://canva.com"),
    # Blockchain
    ("Solana", "https://solana.com"),
    ("Ethereum", "https://ethereum.org"),
    ("Helius", "https://helius.dev"),
    ("Alchemy", "https://alchemy.com"),
    ("Moralis", "https://moralis.io"),
    ("Dune", "https://dune.com"),
    # MCP Registries
    ("MCP.so", "https://mcp.so"),
    ("Smithery.ai", "https://smithery.ai"),
    ("Glama.ai", "https://glama.ai"),
]

API_URL = "https://clarvia-api.onrender.com/api/scan"
results = []
total = len(services)

for i, (name, url) in enumerate(services, 1):
    print(f"[{i}/{total}] Scanning {name} ({url})...", flush=True)
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
            print(f"  -> Score: {data.get('clarvia_score')}, Rating: {data.get('rating')}", flush=True)
        else:
            print(f"  -> FAILED (HTTP {resp.status_code}): {resp.text[:100]}", flush=True)
    except Exception as e:
        print(f"  -> ERROR: {e}", flush=True)
    
    if i < total:
        time.sleep(3)

# Sort by score descending
results.sort(key=lambda x: (x.get("clarvia_score") or 0), reverse=True)

output_path = "/Users/sangho/클로드 코드/scanner/data/prebuilt-scans.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nDone! {len(results)}/{total} services scanned successfully.")
print(f"Saved to {output_path}")
