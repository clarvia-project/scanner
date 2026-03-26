# Clarvia AEO Score Badge

Add a Clarvia badge to your README to show your tool's agent-readiness score. The badge is generated dynamically from your latest scan.

## Get Your Badge

1. Submit your tool: `https://clarvia-api.onrender.com/v1/submit`
2. Use the returned `scan_id` in the badge URL below

## Badge URL Format

```
https://clarvia-api.onrender.com/v1/badge/{scan_id}
```

Returns an SVG badge. Cached for 24 hours.

---

## Markdown

```markdown
[![Clarvia AEO Score](https://clarvia-api.onrender.com/v1/badge/{scan_id})](https://clarvia.art/tool/{scan_id})
```

**Example (replace `abc123` with your scan_id):**

```markdown
[![Clarvia AEO Score](https://clarvia-api.onrender.com/v1/badge/abc123)](https://clarvia.art/tool/abc123)
```

---

## HTML

```html
<a href="https://clarvia.art/tool/{scan_id}">
  <img src="https://clarvia-api.onrender.com/v1/badge/{scan_id}" alt="Clarvia AEO Score" />
</a>
```

**Example:**

```html
<a href="https://clarvia.art/tool/abc123">
  <img src="https://clarvia-api.onrender.com/v1/badge/abc123" alt="Clarvia AEO Score" />
</a>
```

---

## reStructuredText

```rst
.. image:: https://clarvia-api.onrender.com/v1/badge/{scan_id}
   :target: https://clarvia.art/tool/{scan_id}
   :alt: Clarvia AEO Score
```

**Example:**

```rst
.. image:: https://clarvia-api.onrender.com/v1/badge/abc123
   :target: https://clarvia.art/tool/abc123
   :alt: Clarvia AEO Score
```

---

## AsciiDoc

```asciidoc
image:https://clarvia-api.onrender.com/v1/badge/{scan_id}[Clarvia AEO Score, link=https://clarvia.art/tool/{scan_id}]
```

---

## Badge Style Options

Add `?style=` query parameter:

| Style | URL |
|-------|-----|
| Flat (default) | `https://clarvia-api.onrender.com/v1/badge/{scan_id}?style=flat` |
| Flat Square | `https://clarvia-api.onrender.com/v1/badge/{scan_id}?style=flat-square` |

---

## Score Ranges

| Score | Grade | Color |
|-------|-------|-------|
| 75-100 | Strong | Green |
| 50-74 | Moderate | Blue |
| 30-49 | Basic | Yellow |
| 0-29 | Low | Red |

---

## Full README Example

```markdown
# My MCP Server

[![npm version](https://img.shields.io/npm/v/my-mcp-server)](https://npmjs.com/package/my-mcp-server)
[![Clarvia AEO Score](https://clarvia-api.onrender.com/v1/badge/abc123)](https://clarvia.art/tool/abc123)

An MCP server that does amazing things for AI agents.
```
