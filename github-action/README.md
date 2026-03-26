# Clarvia AEO Score Check

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Clarvia%20AEO-purple?logo=github)](https://github.com/marketplace/actions/clarvia-aeo-score-check)

Check your API or MCP server's **AEO (AI Engine Optimization)** readiness score directly in your CI/CD pipeline. Clarvia evaluates four dimensions:

- **API Accessibility** — Can AI agents discover and reach your API?
- **Data Structuring** — Is your data formatted for machine consumption?
- **Agent Compatibility** — Does your API support agentic workflows?
- **Trust Signals** — Does your API provide verifiable trust indicators?

## Quick Start

```yaml
name: AEO Check
on: [push, pull_request]

jobs:
  aeo-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: digitamaz/clarvia-action@v1
        with:
          url: 'api.example.com'
          fail-under: '50'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | — | URL to scan for AEO readiness |
| `fail-under` | No | `0` | Minimum score threshold (fails the step if score is below) |
| `api-url` | No | `https://clarvia.art` | Clarvia API base URL |
| `format` | No | `text` | Output format: `text`, `json`, or `sarif` |

## Outputs

| Output | Description |
|--------|-------------|
| `score` | AEO score (0–100) |
| `rating` | Rating: `excellent`, `strong`, `moderate`, or `weak` |
| `scan-id` | Unique scan ID for referencing results |
| `badge-url` | URL to the dynamic AEO badge SVG |

## Examples

### Basic scan

```yaml
- uses: digitamaz/clarvia-action@v1
  with:
    url: 'stripe.com'
```

### Enforce a minimum score

```yaml
- uses: digitamaz/clarvia-action@v1
  with:
    url: 'api.example.com'
    fail-under: '60'
```

### Use outputs in subsequent steps

```yaml
- uses: digitamaz/clarvia-action@v1
  id: aeo
  with:
    url: 'api.example.com'

- run: echo "AEO Score is ${{ steps.aeo.outputs.score }}/100 (${{ steps.aeo.outputs.rating }})"
```

### Upload SARIF to GitHub Code Scanning

```yaml
- uses: digitamaz/clarvia-action@v1
  with:
    url: 'api.example.com'
    format: 'sarif'

- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: clarvia-results.sarif
```

### Add badge to PR comment

```yaml
- uses: digitamaz/clarvia-action@v1
  id: aeo
  with:
    url: 'api.example.com'

- uses: marocchino/sticky-pull-request-comment@v2
  with:
    message: |
      ## AEO Score: ${{ steps.aeo.outputs.score }}/100
      ![AEO Badge](${{ steps.aeo.outputs.badge-url }})
```

## Badge Usage

After scanning, a dynamic badge SVG is available at the `badge-url` output. Add it to your project README:

```markdown
[![Clarvia AEO Score](https://clarvia.art/api/badge/YOUR_SERVICE_NAME)](https://clarvia.art)
```

The badge updates automatically whenever a new scan is completed.

## Job Summary

When running on GitHub Actions, scan results are automatically written to the **Job Summary** with a score breakdown table and badge.

## Dependencies

This action uses only `curl` and `jq`, which are pre-installed on all GitHub-hosted runners. No additional runtimes (Python, Node.js) required.

## License

MIT
