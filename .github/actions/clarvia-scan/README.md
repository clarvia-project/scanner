# Clarvia AEO Scan Action

Scan your API or tool for AI agent compatibility in your CI/CD pipeline.

## Usage

```yaml
- uses: clarvia/scan-action@v1
  with:
    url: https://api.example.com
    fail-under: 70
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | — | URL to scan |
| `fail-under` | No | `0` | Minimum score (fails if below) |
| `format` | No | `text` | Output: text, json, sarif |

## Outputs

| Output | Description |
|--------|-------------|
| `score` | Clarvia score (0-100) |
| `rating` | Rating (Strong/Moderate/Basic/Low) |
| `scan-id` | Scan ID for reference |
