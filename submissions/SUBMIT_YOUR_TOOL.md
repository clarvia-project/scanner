# Submit Your Tool to Clarvia

**Clarvia** is the quality index for AI agent tools — MCP servers, APIs, CLI tools, and agent frameworks. Getting indexed means your tool shows up when agents search for the best tools to use.

## Why Get Indexed?

- **Visibility** — Your tool appears in the Clarvia catalog searched by thousands of AI agents daily
- **Trust Signal** — A Clarvia score badge shows users and agents that your tool has been independently evaluated
- **Quality Feedback** — Get a detailed breakdown across 5 dimensions: description quality, documentation, ecosystem presence, agent compatibility, and trust signals
- **Discoverability** — Agents using Clarvia's API (`/v1/services`) find your tool automatically
- **Free** — Submission and indexing are completely free

## How to Submit

### Option 1: API Submission (Recommended)

```bash
curl -X POST https://clarvia-api.onrender.com/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/your-org/your-tool",
    "name": "Your Tool Name",
    "description": "Brief description of what your tool does",
    "contact_email": "you@example.com"
  }'
```

**Response:**
```json
{
  "submission_id": "sub_abc123def456",
  "status": "queued",
  "estimated_time": "5-30 minutes",
  "message": "Tool submitted successfully. It will be scanned and indexed automatically.",
  "badge_preview": "https://clarvia-api.onrender.com/v1/badge/sub_abc123def456"
}
```

### Option 2: Check Status

```bash
curl https://clarvia-api.onrender.com/v1/submissions/sub_abc123def456
```

### Supported URL Types

| Type | Example URL |
|------|-------------|
| GitHub Repository | `https://github.com/org/mcp-server-example` |
| npm Package | `https://www.npmjs.com/package/@org/tool` |
| PyPI Package | `https://pypi.org/project/mcp-server-example/` |
| API Documentation | `https://api.example.com/docs` |
| Any Web URL | `https://your-tool.example.com` |

## Add a Clarvia Badge

Once your tool is indexed, add a badge to your README:

### Markdown

```markdown
[![Clarvia Score](https://clarvia-api.onrender.com/v1/badge/{scan_id})](https://clarvia.art/tool/{scan_id})
```

### HTML

```html
<a href="https://clarvia.art/tool/{scan_id}">
  <img src="https://clarvia-api.onrender.com/v1/badge/{scan_id}" alt="Clarvia Score">
</a>
```

### Badge Examples

| Score Range | Badge |
|-------------|-------|
| 75+ (Strong) | ![Clarvia 8.5/10](https://img.shields.io/badge/Clarvia-8.5%2F10-brightgreen) |
| 50-74 (Moderate) | ![Clarvia 6.2/10](https://img.shields.io/badge/Clarvia-6.2%2F10-green) |
| 30-49 (Basic) | ![Clarvia 3.8/10](https://img.shields.io/badge/Clarvia-3.8%2F10-yellow) |
| <30 (Low) | ![Clarvia 1.5/10](https://img.shields.io/badge/Clarvia-1.5%2F10-red) |

## Scoring Dimensions

Your tool is evaluated across 5 dimensions (total: 100 points):

| Dimension | Max Points | What We Look For |
|-----------|-----------|------------------|
| Description Quality | 20 | Clear, detailed description with relevant keywords |
| Documentation | 20 | Homepage, repository, versioning, API docs |
| Ecosystem Presence | 20 | Registry listings, download counts, install commands |
| Agent Compatibility | 25 | MCP support, tool definitions, API specs, agent frameworks |
| Trust Signals | 15 | Known org, HTTPS, semantic versioning, official registries |

## Improve Your Score

Tips to maximize your Clarvia score:

1. **Write a comprehensive README** with clear descriptions of what your tool does
2. **Publish to registries** — npm, PyPI, MCP Registry
3. **Include an OpenAPI spec** or MCP tool definitions
4. **Use semantic versioning** (e.g., `1.2.3`)
5. **Host documentation** at a dedicated URL
6. **Add keywords/topics** to your GitHub repo and package.json
7. **Provide install commands** (`npm install`, `pip install`, etc.)

## API Reference

### `POST /v1/submit`

Submit a tool for scanning.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Tool URL (GitHub, npm, API docs, etc.) |
| `name` | string | No | Tool name (auto-detected if omitted) |
| `description` | string | No | Brief tool description |
| `contact_email` | string | No | Email for status updates |

### `GET /v1/submissions/{submission_id}`

Check submission status.

**Response Fields:**
| Field | Description |
|-------|-------------|
| `status` | `queued` \| `indexed` \| `scan_failed` \| `duplicate` |
| `scan_id` | Assigned after successful scan |
| `clarvia_score` | 0-100 quality score |
| `badge` | Badge URLs and embed codes |

### `GET /v1/badge/{identifier}`

Get an SVG badge for your tool.

**Parameters:**
| Param | Default | Options |
|-------|---------|---------|
| `style` | `flat` | `flat`, `flat-square` |

**Caching:** Badges are cached for 24 hours.

## Questions?

- **API Docs:** `https://clarvia-api.onrender.com/openapi.json`
- **Catalog:** `https://clarvia.art`
- **GitHub:** `https://github.com/clarvia`
