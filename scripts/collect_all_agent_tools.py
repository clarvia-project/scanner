"""Collect ALL agent tools from every known source.

Sources:
1. Composio — 250+ app integrations for agents
2. APIs.guru — OpenAPI directory (25,000+ APIs)
3. n8n — 1,000+ workflow nodes
4. LangChain — Community tools index
5. Zapier — App directory
6. RapidAPI — API marketplace

Usage:
    python3 scripts/collect_all_agent_tools.py
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)


# ─── 1. Composio (Agent tool integrations) ───

def collect_composio() -> list[dict]:
    """Collect tools from Composio sitemap."""
    print("  Fetching Composio sitemap...")
    try:
        req = urllib.request.Request("https://composio.dev/sitemap.xml",
                                     headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode()

        # Look for sub-sitemaps
        sitemaps = re.findall(r"<loc>(https://composio\.dev/[^<]*sitemap[^<]*)</loc>", data)
        tool_urls = re.findall(r"<loc>(https://composio\.dev/tools/[^<]+)</loc>", data)

        for sm in sitemaps[:10]:
            try:
                req2 = urllib.request.Request(sm, headers={"User-Agent": "clarvia-collector/1.0"})
                resp2 = urllib.request.urlopen(req2, timeout=30)
                data2 = resp2.read().decode()
                more = re.findall(r"<loc>(https://composio\.dev/tools/[^<]+)</loc>", data2)
                tool_urls.extend(more)
                print(f"    sub-sitemap {sm.split('/')[-1]}: {len(more)} tools")
            except:
                pass

        unique = list(dict.fromkeys(tool_urls))
        results = []
        for u in unique:
            name = u.split("/tools/")[-1].rstrip("/")
            results.append({
                "name": name,
                "url": u,
                "source": "composio",
                "type": "connector",
                "install_command": f"composio add {name}",
                "description": f"Composio integration: {name}",
            })
        print(f"  → {len(results)} Composio tools")
        return results
    except Exception as e:
        print(f"  Composio error: {e}")
        return []


# ─── 2. APIs.guru (OpenAPI Directory) ───

def collect_apis_guru() -> list[dict]:
    """Collect from APIs.guru — the Wikipedia of APIs."""
    print("  Fetching APIs.guru directory...")
    try:
        url = "https://api.apis.guru/v2/list.json"
        req = urllib.request.Request(url, headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())

        results = []
        for api_name, api_info in data.items():
            preferred = api_info.get("preferred", "")
            versions = api_info.get("versions", {})
            latest = versions.get(preferred, {})
            info = latest.get("info", {})

            results.append({
                "name": api_name,
                "description": info.get("description", "")[:500] if info.get("description") else "",
                "title": info.get("title", ""),
                "version": preferred,
                "url": info.get("x-origin", [{}])[0].get("url", "") if info.get("x-origin") else "",
                "homepage": latest.get("externalDocs", {}).get("url", ""),
                "openapi_url": latest.get("swaggerUrl", ""),
                "source": "apis_guru",
                "type": "api",
                "category": info.get("x-apisguru-categories", ["other"])[0] if info.get("x-apisguru-categories") else "other",
            })

        print(f"  → {len(results)} APIs")
        return results
    except Exception as e:
        print(f"  APIs.guru error: {e}")
        return []


# ─── 3. n8n Nodes (Workflow automation) ───

def collect_n8n() -> list[dict]:
    """Collect n8n integration nodes from sitemap."""
    print("  Fetching n8n integrations...")
    try:
        req = urllib.request.Request("https://n8n.io/sitemap.xml",
                                     headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode()

        # Find integration sitemaps
        sitemaps = re.findall(r"<loc>(https://n8n\.io/[^<]*sitemap[^<]*)</loc>", data)
        integration_urls = re.findall(r"<loc>(https://n8n\.io/integrations/[^<]+)</loc>", data)

        for sm in sitemaps:
            if "integrations" in sm.lower() or "sitemap" in sm.lower():
                try:
                    req2 = urllib.request.Request(sm, headers={"User-Agent": "clarvia-collector/1.0"})
                    resp2 = urllib.request.urlopen(req2, timeout=30)
                    data2 = resp2.read().decode()
                    more = re.findall(r"<loc>(https://n8n\.io/integrations/[^<]+)</loc>", data2)
                    integration_urls.extend(more)
                except:
                    pass

        unique = list(dict.fromkeys(integration_urls))
        results = []
        for u in unique:
            name = u.split("/integrations/")[-1].rstrip("/")
            if name and "/" not in name:  # top-level integrations only
                results.append({
                    "name": name,
                    "url": u,
                    "source": "n8n",
                    "type": "connector",
                    "description": f"n8n integration: {name}",
                })

        print(f"  → {len(results)} n8n integrations")
        return results
    except Exception as e:
        print(f"  n8n error: {e}")
        return []


# ─── 4. Zapier Apps ───

def collect_zapier() -> list[dict]:
    """Collect Zapier app directory from sitemap."""
    print("  Fetching Zapier apps...")
    try:
        req = urllib.request.Request("https://zapier.com/sitemap.xml",
                                     headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode()

        sitemaps = re.findall(r"<loc>(https://zapier\.com/[^<]*sitemap[^<]*)</loc>", data)
        app_urls = re.findall(r"<loc>(https://zapier\.com/apps/[^<]+)</loc>", data)

        for sm in sitemaps:
            if "apps" in sm.lower():
                try:
                    req2 = urllib.request.Request(sm, headers={"User-Agent": "clarvia-collector/1.0"})
                    resp2 = urllib.request.urlopen(req2, timeout=30)
                    data2 = resp2.read().decode()
                    more = re.findall(r"<loc>(https://zapier\.com/apps/[^<]+)</loc>", data2)
                    app_urls.extend(more)
                    print(f"    sub-sitemap: {len(more)} apps")
                except:
                    pass

        unique = list(dict.fromkeys(app_urls))
        results = []
        for u in unique:
            parts = u.replace("https://zapier.com/apps/", "").rstrip("/").split("/")
            name = parts[0] if parts else ""
            if name and len(parts) == 1:  # top-level app pages only
                results.append({
                    "name": name,
                    "url": u,
                    "source": "zapier",
                    "type": "connector",
                    "description": f"Zapier app: {name}",
                })

        print(f"  → {len(results)} Zapier apps")
        return results
    except Exception as e:
        print(f"  Zapier error: {e}")
        return []


# ─── 5. RapidAPI ───

def collect_rapidapi() -> list[dict]:
    """Collect from RapidAPI sitemap."""
    print("  Fetching RapidAPI...")
    try:
        req = urllib.request.Request("https://rapidapi.com/sitemap.xml",
                                     headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read().decode()

        sitemaps = re.findall(r"<loc>(https://rapidapi\.com/[^<]*sitemap[^<]*)</loc>", data)
        api_urls = []

        for sm in sitemaps[:5]:  # Limit to first 5 sub-sitemaps
            if "hub" in sm.lower() or "api" in sm.lower():
                try:
                    req2 = urllib.request.Request(sm, headers={"User-Agent": "clarvia-collector/1.0"})
                    resp2 = urllib.request.urlopen(req2, timeout=30)
                    data2 = resp2.read().decode()
                    more = re.findall(r"<loc>(https://rapidapi\.com/[^<]*/api/[^<]+)</loc>", data2)
                    api_urls.extend(more)
                    print(f"    sub-sitemap: {len(more)} APIs")
                except:
                    pass

        unique = list(dict.fromkeys(api_urls))
        results = []
        for u in unique[:5000]:  # Cap at 5000
            name = u.split("/api/")[-1].rstrip("/") if "/api/" in u else ""
            if name:
                results.append({
                    "name": name,
                    "url": u,
                    "source": "rapidapi",
                    "type": "api",
                    "description": f"RapidAPI: {name}",
                })

        print(f"  → {len(results)} RapidAPI APIs")
        return results
    except Exception as e:
        print(f"  RapidAPI error: {e}")
        return []


# ─── Main ───

def main():
    print("🦉 Clarvia ALL Agent Tools Collector\n" + "=" * 60)

    all_items = []
    stats = {}

    collectors = [
        ("Composio", collect_composio),
        ("APIs.guru", collect_apis_guru),
        ("n8n", collect_n8n),
        ("Zapier", collect_zapier),
        ("RapidAPI", collect_rapidapi),
    ]

    for name, fn in collectors:
        print(f"\n{'─' * 40}")
        print(f"📡 {name}")
        items = fn()
        all_items.extend(items)
        stats[name] = len(items)

    # Save
    output = DATA / "all-agent-tools.json"
    with open(output, "w") as f:
        json.dump(all_items, f)

    print(f"\n{'=' * 60}")
    print(f"📊 총 수집: {len(all_items):,}")
    for name, count in stats.items():
        print(f"  {name}: {count:,}")
    print(f"📁 저장: {output}")

    # Combine with existing data
    existing_files = [
        ("MCP Registry", DATA / "mcp-scan-urls.json"),
        ("Glama MCP", DATA / "glama-scan-urls.json"),
        ("GitHub MCP", DATA / "github-mcp-repos.json"),
        ("Skills/CLI", DATA / "skills-cli-collected.json"),
    ]

    total_existing = 0
    for name, path in existing_files:
        if path.exists():
            with open(path) as f:
                count = len(json.load(f))
            print(f"  + {name}: {count:,}")
            total_existing += count

    print(f"\n🏆 전체 데이터: {total_existing + len(all_items):,}개 에이전트 도구")


if __name__ == "__main__":
    main()
