# Clarvia AEO Check

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Clarvia%20AEO%20Check-purple?logo=github)](https://github.com/marketplace/actions/clarvia-aeo-check)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A GitHub Action that analyzes your MCP (Model Context Protocol) server configurations for **AEO (AI Engine Optimization)** readiness. It auto-detects configs in your repository, scores them via the Clarvia API, and posts results as PR comments.

## What is AEO?

AEO (AI Engine Optimization) measures how well your API or MCP server is optimized for AI agent consumption. Clarvia evaluates four dimensions:

| Dimension | What it measures |
|-----------|-----------------|
| **API Accessibility** | Can AI agents discover and reach your API? |
| **Data Structuring** | Is your data formatted for machine consumption? |
| **Agent Compatibility** | Does your API support agentic workflows? |
| **Trust Signals** | Does your API provide verifiable trust indicators? |

## Quick Start

### Auto-detect MCP configs in your repo

```yaml
name: AEO Check
on: [pull_request]

jobs:
  aeo:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: clarvia/aeo-check@v1
```

The action automatically finds MCP config files (`mcp.json`, `server.json`, `claude_desktop_config.json`, etc.) and scans any URLs defined in them.

### Scan a specific URL

```yaml
- uses: clarvia/aeo-check@v1
  with:
    url: 'https://api.example.com'
    fail-under: '60'
```

### Scan specific config files

```yaml
- uses: clarvia/aeo-check@v1
  with:
    config-paths: 'config/mcp.json,server.json'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | No | — | URL to scan. If omitted, auto-detects MCP configs in the repo. |
| `config-paths` | No | — | Comma-separated config file paths to scan. Overrides auto-detection. |
| `fail-under` | No | `0` | Minimum AEO score (0-100). Fails the check if below threshold. |
| `api-url` | No | `https://clarvia-api.onrender.com` | Clarvia API base URL. |
| `api-key` | No | — | Clarvia API key for authenticated scans (higher rate limits). |
| `post-comment` | No | `true` | Post results as a PR comment on pull_request events. |
| `comment-header` | No | `<!-- clarvia-aeo-check -->` | HTML comment used to identify and update existing comments. |
| `fail-on-error` | No | `false` | Fail the action if the API is unreachable. |
| `github-token` | No | `${{ github.token }}` | Token for posting PR comments. |

## Outputs

| Output | Description |
|--------|-------------|
| `score` | Overall AEO score (0-100) |
| `rating` | Rating: `excellent`, `strong`, `moderate`, or `weak` |
| `agent-grade` | Grade: `AGENT_NATIVE`, `AGENT_FRIENDLY`, `AGENT_POSSIBLE`, `AGENT_HOSTILE` |
| `scan-id` | Unique scan ID |
| `badge-url` | Dynamic AEO badge SVG URL |
| `details-url` | Full report URL on Clarvia |
| `passed` | Whether the score meets `fail-under` (`true`/`false`) |
| `configs-found` | Number of MCP configs detected |
| `results-json` | Full results as JSON string |

## Auto-detected Config Files

The action searches for these files in your repository:

| File | Description |
|------|-------------|
| `mcp.json` | Standard MCP server config |
| `server.json` | MCP server config (alt name) |
| `claude_desktop_config.json` | Claude Desktop config |
| `.cursor/mcp.json` | Cursor editor MCP config |
| `.vscode/mcp.json` | VS Code MCP config |
| `.claude/mcp.json` | Claude CLI config |
| `smithery.yaml` | Smithery MCP registry config |
| `package.json` | npm packages with `mcp` keywords or `mcp` field |

It also checks common subdirectories (`src/`, `config/`, `configs/`, `.config/`, `mcp/`) for `mcp.json` and `server.json`.

## Examples

### Enforce a minimum score

```yaml
name: AEO Gate
on: [pull_request]

jobs:
  aeo:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: clarvia/aeo-check@v1
        with:
          url: 'https://my-mcp-server.example.com'
          fail-under: '70'
```

### Use outputs in subsequent steps

```yaml
- uses: clarvia/aeo-check@v1
  id: aeo
  with:
    url: 'https://api.example.com'

- run: |
    echo "Score: ${{ steps.aeo.outputs.score }}/100"
    echo "Grade: ${{ steps.aeo.outputs.agent-grade }}"
    echo "Passed: ${{ steps.aeo.outputs.passed }}"
```

### Authenticated scan with API key

```yaml
- uses: clarvia/aeo-check@v1
  with:
    url: 'https://api.example.com'
    api-key: ${{ secrets.CLARVIA_API_KEY }}
```

### Add badge to your README

After a successful scan, use the `badge-url` output or construct it manually:

```markdown
[![Clarvia AEO Score](https://clarvia-api.onrender.com/api/badge/YOUR_SERVICE)](https://clarvia.art)
```

### Multiple scans in a matrix

```yaml
jobs:
  aeo:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        url:
          - 'https://api-a.example.com'
          - 'https://api-b.example.com'
    steps:
      - uses: clarvia/aeo-check@v1
        with:
          url: ${{ matrix.url }}
          fail-under: '50'
```

### Conditional failure (warn but don't block)

```yaml
- uses: clarvia/aeo-check@v1
  id: aeo
  with:
    url: 'https://api.example.com'

- if: steps.aeo.outputs.score < 50
  run: echo "::warning::AEO score is low (${{ steps.aeo.outputs.score }}/100)"
```

## PR Comment

When running on a `pull_request` event with `post-comment: true`, the action posts (or updates) a comment like this:

> ## :owl: Clarvia AEO Check Results
>
> **Score: 72/100** :white_check_mark: Strong
> **Agent Grade:** :handshake: AGENT_FRIENDLY
>
> | Dimension | Score | Bar |
> |-----------|-------|-----|
> | API Accessibility | 20/25 | `████████████████░░░░` |
> | Data Structuring | 18/25 | `██████████████░░░░░░` |
> | Agent Compatibility | 16/25 | `████████████░░░░░░░░` |
> | Trust Signals | 18/25 | `██████████████░░░░░░` |

## Job Summary

Scan results are also written to the GitHub Actions [Job Summary](https://github.blog/2022-05-09-supercharging-github-actions-with-job-summaries/) with a full score breakdown table and badge.

## Development

```bash
# Install dependencies
npm install

# Build the dist bundle (required before committing)
npm run build

# Run tests
npm test
```

The action uses `@vercel/ncc` to compile all source files and dependencies into a single `dist/index.js` file. Always run `npm run build` before committing changes.

## How It Works

1. **Config Detection**: Scans the repository for MCP server config files (or uses the provided URL/paths).
2. **URL Extraction**: Parses config files to extract server URLs (supports SSE, stdio, and HTTP transports).
3. **API Scan**: Sends each URL to the Clarvia API for AEO analysis.
4. **Result Formatting**: Formats results as a PR comment and Job Summary.
5. **Threshold Check**: Optionally fails the workflow if the score is below a minimum.

## License

MIT
