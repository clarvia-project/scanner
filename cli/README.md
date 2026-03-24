# Clarvia AEO Scanner CLI

Check your API's readiness for AI agents with the Clarvia AEO (AI Engine Optimization) Scanner.

## Installation

```bash
pip install clarvia-cli
```

Or install from source:

```bash
git clone https://github.com/clarvia/scanner.git
cd scanner/cli
pip install .
```

## Usage

### Scan a URL

```bash
clarvia scan stripe.com
```

### Output formats

```bash
# Human-readable (default)
clarvia scan stripe.com --format text

# JSON
clarvia scan stripe.com --format json

# SARIF (for GitHub Code Scanning)
clarvia scan stripe.com --format sarif > results.sarif
```

### CI/CD integration

Fail the build if the AEO score drops below a threshold:

```bash
clarvia scan api.example.com --fail-under 60
```

### Get a badge URL

```bash
clarvia badge stripe.com
# Output: https://clarvia.art/api/badge/stripe.com
```

### Options

```
Usage: clarvia scan <url> [options]

Options:
  --api-url URL             API base URL (default: https://clarvia.art)
  --format json|text|sarif  Output format (default: text)
  --fail-under N            Exit with code 1 if score < N
  --auth-header KEY:VALUE   Add auth header to scan request
  --timeout N               Timeout in seconds (default: 60)
  --verbose                 Show detailed dimension sub-factor scores
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | Score below `--fail-under` threshold |
| 2    | Scan error (network, API, etc.) |

## Example output

```
Clarvia AEO Scanner v1.0.0

Scanning: https://stripe.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Clarvia Score: 61/100 (Moderate)

  API Accessibility:       23/25 ██████████████████████░░
  Data Structuring:        17/25 ████████████████░░░░░░░░
  Agent Compatibility:      4/25 ███░░░░░░░░░░░░░░░░░░░░░
  Trust Signals:           17/25 ████████████████░░░░░░░░

Top Recommendations:
  1. Publish an MCP server
  2. Add .well-known/ai-plugin.json
  3. Improve error response structure

Badge: https://clarvia.art/api/badge/stripe
```

## GitHub Action

See [github-action/](../github-action/) for the companion GitHub Action.
