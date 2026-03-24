"""Collect skills and CLI tools from multiple sources for Clarvia registry.

Sources:
1. npm Registry — AI/agent/mcp related packages
2. GitHub — claude-skills, agent-tools topics
3. PyPI — AI/agent CLI tools
4. LangChain/CrewAI — tool directories

Usage:
    python3 scripts/collect_skills_cli.py
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)


# ─── npm Registry ───

def collect_npm(keywords: list[str], max_per_keyword: int = 250) -> list[dict]:
    """Search npm registry for AI/agent related packages."""
    all_packages = {}

    for kw in keywords:
        offset = 0
        while offset < max_per_keyword:
            url = f"https://registry.npmjs.org/-/v1/search?text={urllib.parse.quote(kw)}&size=250&from={offset}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "clarvia-collector/1.0"})
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                objects = data.get("objects", [])
                if not objects:
                    break

                for obj in objects:
                    pkg = obj.get("package", {})
                    name = pkg.get("name", "")
                    if name and name not in all_packages:
                        all_packages[name] = {
                            "name": name,
                            "description": pkg.get("description", ""),
                            "version": pkg.get("version", ""),
                            "keywords": pkg.get("keywords", []),
                            "homepage": pkg.get("links", {}).get("homepage", ""),
                            "repository": pkg.get("links", {}).get("repository", ""),
                            "npm_url": pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}"),
                            "author": pkg.get("author", {}).get("name", "") if isinstance(pkg.get("author"), dict) else str(pkg.get("author", "")),
                            "score": obj.get("score", {}).get("final", 0),
                            "source": "npm",
                            "type": "cli_tool",
                            "install_command": f"npm install {name}",
                        }

                print(f"  npm [{kw}] offset={offset}: {len(objects)} packages")
                offset += 250
                total = data.get("total", 0)
                if offset >= total:
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"  npm [{kw}] error: {e}")
                break

    return list(all_packages.values())


# ─── GitHub Topics ───

def collect_github(topics: list[str], max_per_topic: int = 1000) -> list[dict]:
    """Search GitHub repos by topic."""
    all_repos = {}

    for topic in topics:
        page = 1
        while len([r for r in all_repos.values() if topic in r.get("_topics", [])]) < max_per_topic:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=stars&per_page=100&page={page}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "clarvia-collector/1.0"})
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                items = data.get("items", [])
                if not items:
                    break

                for repo in items:
                    name = repo["full_name"]
                    if name not in all_repos:
                        all_repos[name] = {
                            "name": repo["name"],
                            "full_name": name,
                            "description": repo.get("description", "") or "",
                            "url": repo["html_url"],
                            "homepage": repo.get("homepage", "") or "",
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language", ""),
                            "updated_at": repo.get("updated_at", ""),
                            "topics": repo.get("topics", []),
                            "source": "github",
                            "type": "skill" if "skill" in topic else "cli_tool",
                            "_topics": [topic],
                        }
                    else:
                        all_repos[name]["_topics"].append(topic)

                print(f"  github [{topic}] page={page}: {len(items)} repos (total: {data.get('total_count', 0)})")
                page += 1
                if page > 10:  # GitHub limit
                    break
                time.sleep(2)  # Rate limit
            except Exception as e:
                print(f"  github [{topic}] page={page}: error {str(e)[:50]}")
                time.sleep(10)
                break

    # Clean up internal field
    for r in all_repos.values():
        r.pop("_topics", None)

    return list(all_repos.values())


# ─── Homebrew ───

def collect_homebrew_ai() -> list[dict]:
    """Get AI-related Homebrew formulae."""
    try:
        url = "https://formulae.brew.sh/api/formula.json"
        req = urllib.request.Request(url, headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=60)
        formulae = json.loads(resp.read())

        ai_keywords = {"ai", "agent", "llm", "gpt", "openai", "anthropic", "langchain",
                       "machine-learning", "ml", "neural", "transformer", "mcp"}

        results = []
        for f in formulae:
            name = f.get("name", "").lower()
            desc = f.get("desc", "").lower()
            combined = f"{name} {desc}"
            if any(kw in combined for kw in ai_keywords):
                results.append({
                    "name": f["name"],
                    "description": f.get("desc", ""),
                    "homepage": f.get("homepage", ""),
                    "version": f.get("versions", {}).get("stable", ""),
                    "source": "homebrew",
                    "type": "cli_tool",
                    "install_command": f"brew install {f['name']}",
                })

        print(f"  homebrew: {len(results)} AI-related formulae (out of {len(formulae)} total)")
        return results
    except Exception as e:
        print(f"  homebrew: error {e}")
        return []


# ─── SkillsMP ───

def collect_skillsmp() -> list[dict]:
    """Try to collect from SkillsMP."""
    # Try sitemap first
    try:
        url = "https://skillsmp.com/sitemap.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "clarvia-collector/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode()

        import re
        urls = re.findall(r"<loc>(https://skillsmp\.com/skill/[^<]+)</loc>", data)
        print(f"  skillsmp sitemap: {len(urls)} skill URLs")

        # Also check for sub-sitemaps
        sitemaps = re.findall(r"<loc>(https://skillsmp\.com/[^<]*sitemap[^<]*)</loc>", data)
        for sm in sitemaps[:5]:
            try:
                req2 = urllib.request.Request(sm, headers={"User-Agent": "clarvia-collector/1.0"})
                resp2 = urllib.request.urlopen(req2, timeout=15)
                data2 = resp2.read().decode()
                more = re.findall(r"<loc>(https://skillsmp\.com/skill/[^<]+)</loc>", data2)
                urls.extend(more)
                print(f"  skillsmp sub-sitemap {sm}: {len(more)} URLs")
            except:
                pass

        unique_urls = list(dict.fromkeys(urls))
        results = [{"name": u.split("/skill/")[-1], "url": u, "source": "skillsmp", "type": "skill"} for u in unique_urls]
        return results
    except Exception as e:
        print(f"  skillsmp: error {e}")
        return []


# ─── Main ───

def main():
    print("🦉 Clarvia Skills & CLI Collector\n" + "=" * 60)

    all_items = []

    # 1. npm
    print("\n📦 Collecting from npm...")
    npm_keywords = [
        "mcp-server", "ai-agent", "llm-tool", "agent-tool",
        "langchain-tool", "crewai", "ai-cli", "claude-skill",
        "openai-plugin", "agent-framework",
    ]
    npm_items = collect_npm(npm_keywords)
    all_items.extend(npm_items)
    print(f"  → {len(npm_items)} npm packages")

    # 2. GitHub
    print("\n🐙 Collecting from GitHub...")
    gh_topics = [
        "claude-skills", "agent-skills", "mcp-tools",
        "ai-agent-tools", "langchain-tools", "crewai-tools",
    ]
    gh_items = collect_github(gh_topics)
    all_items.extend(gh_items)
    print(f"  → {len(gh_items)} GitHub repos")

    # 3. Homebrew
    print("\n🍺 Collecting from Homebrew...")
    brew_items = collect_homebrew_ai()
    all_items.extend(brew_items)
    print(f"  → {len(brew_items)} Homebrew formulae")

    # 4. SkillsMP
    print("\n✨ Collecting from SkillsMP...")
    skillsmp_items = collect_skillsmp()
    all_items.extend(skillsmp_items)
    print(f"  → {len(skillsmp_items)} SkillsMP skills")

    # Save
    output = DATA / "skills-cli-collected.json"
    with open(output, "w") as f:
        json.dump(all_items, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"📊 총 수집: {len(all_items)}")
    print(f"  npm: {len(npm_items)}")
    print(f"  GitHub: {len(gh_items)}")
    print(f"  Homebrew: {len(brew_items)}")
    print(f"  SkillsMP: {len(skillsmp_items)}")
    print(f"📁 저장: {output}")


if __name__ == "__main__":
    main()
