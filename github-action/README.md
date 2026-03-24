# Clarvia AEO Scan GitHub Action

Automatically check your API's AEO (AI Engine Optimization) readiness score in CI/CD.

## Quick start

```yaml
name: AEO Check
on: [push, pull_request]

jobs:
  aeo-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: clarvia/scanner/github-action@v1
        with:
          url: 'api.example.com'
          fail-under: '50'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | - | URL to scan for AEO readiness |
| `fail-under` | No | `0` | Minimum score threshold (fails if below) |
| `api-url` | No | `https://clarvia.art` | Clarvia API base URL |
| `format` | No | `text` | Output format: `text`, `json`, or `sarif` |

## Outputs

| Output | Description |
|--------|-------------|
| `score` | The Clarvia AEO score (0-100) |
| `rating` | Rating: excellent, strong, moderate, or weak |
| `scan-id` | Scan ID for referencing results |
| `badge-url` | URL to the AEO badge SVG |

## Examples

### Basic scan

```yaml
- uses: clarvia/scanner/github-action@v1
  with:
    url: 'stripe.com'
```

### Fail if score drops

```yaml
- uses: clarvia/scanner/github-action@v1
  with:
    url: 'api.example.com'
    fail-under: '60'
```

### Use outputs in subsequent steps

```yaml
- uses: clarvia/scanner/github-action@v1
  id: aeo
  with:
    url: 'api.example.com'

- run: echo "AEO Score is ${{ steps.aeo.outputs.score }}"
```

### Upload SARIF to GitHub Code Scanning

```yaml
- uses: clarvia/scanner/github-action@v1
  with:
    url: 'api.example.com'
    format: 'sarif'

- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: clarvia-results.sarif
```

### Add badge to PR comment

```yaml
- uses: clarvia/scanner/github-action@v1
  id: aeo
  with:
    url: 'api.example.com'

- uses: marocchino/sticky-pull-request-comment@v2
  with:
    message: |
      ## AEO Score: ${{ steps.aeo.outputs.score }}/100
      ![AEO Badge](${{ steps.aeo.outputs.badge-url }})
```

## Dependencies

The action uses only `curl` and `jq`, which are pre-installed on all GitHub-hosted runners. No Python or Node.js required.
