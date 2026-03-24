#!/usr/bin/env bash
# Clarvia AEO Scanner — GitHub Action wrapper
# Dependencies: curl, jq (both pre-installed on GitHub runners)
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCAN_URL="${SCAN_URL:?URL is required}"
API_URL="${API_URL:-https://clarvia.art}"
FAIL_UNDER="${FAIL_UNDER:-0}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-text}"

API_ENDPOINT="${API_URL}/api/scan"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
bar() {
  local score=$1 max=$2 width=24
  local filled=$(( score * width / max ))
  local empty=$(( width - filled ))
  printf '%0.s█' $(seq 1 "$filled" 2>/dev/null) || true
  printf '%0.s░' $(seq 1 "$empty" 2>/dev/null) || true
}

rating_label() {
  case "$1" in
    excellent) echo "Excellent" ;;
    strong)    echo "Strong" ;;
    moderate)  echo "Moderate" ;;
    weak)      echo "Weak" ;;
    *)         echo "$1" ;;
  esac
}

# ---------------------------------------------------------------------------
# Run scan
# ---------------------------------------------------------------------------
echo "🦉 Clarvia AEO Scanner"
echo ""
echo "Scanning: ${SCAN_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "${API_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "User-Agent: clarvia-github-action/1.0.0" \
  -d "{\"url\": \"${SCAN_URL}\"}" \
  --max-time 120 \
  2>&1) || {
    echo "::error::Failed to connect to Clarvia API at ${API_URL}"
    exit 2
  }

HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')
HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -1)

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
  ERROR_MSG=$(echo "$HTTP_BODY" | jq -r '.detail // .error.message // "Unknown error"' 2>/dev/null || echo "$HTTP_BODY")
  echo "::error::Scan failed (HTTP ${HTTP_CODE}): ${ERROR_MSG}"
  exit 2
fi

# Validate JSON
if ! echo "$HTTP_BODY" | jq empty 2>/dev/null; then
  echo "::error::Invalid JSON response from API"
  exit 2
fi

# ---------------------------------------------------------------------------
# Parse results
# ---------------------------------------------------------------------------
SCORE=$(echo "$HTTP_BODY" | jq -r '.clarvia_score')
RATING=$(echo "$HTTP_BODY" | jq -r '.rating')
SCAN_ID=$(echo "$HTTP_BODY" | jq -r '.scan_id')
SERVICE_NAME=$(echo "$HTTP_BODY" | jq -r '.service_name')
BADGE_URL="${API_URL}/api/badge/${SERVICE_NAME}"

# Set GitHub Action outputs
{
  echo "score=${SCORE}"
  echo "rating=${RATING}"
  echo "scan_id=${SCAN_ID}"
  echo "badge_url=${BADGE_URL}"
} >> "${GITHUB_OUTPUT:-/dev/null}"

# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
if [[ "$OUTPUT_FORMAT" == "json" ]]; then
  echo "$HTTP_BODY" | jq .

elif [[ "$OUTPUT_FORMAT" == "sarif" ]]; then
  # Generate SARIF 2.1.0
  SARIF=$(echo "$HTTP_BODY" | jq --arg version "1.0.0" '{
    "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
    "version": "2.1.0",
    "runs": [{
      "tool": {
        "driver": {
          "name": "Clarvia AEO Scanner",
          "version": $version,
          "informationUri": "https://clarvia.art",
          "rules": [.top_recommendations | to_entries[] | {
            "id": ("clarvia/recommendation-" + ((.key + 1) | tostring)),
            "shortDescription": {"text": .value},
            "helpUri": "https://clarvia.art",
            "properties": {"tags": ["aeo", "api-readiness"]}
          }]
        }
      },
      "results": [.top_recommendations | to_entries[] | {
        "ruleId": ("clarvia/recommendation-" + ((.key + 1) | tostring)),
        "level": (if .rating == "weak" then "error" elif .rating == "moderate" then "warning" else "note" end),
        "message": {"text": .value},
        "locations": [{
          "physicalLocation": {
            "artifactLocation": {"uri": .url}
          }
        }]
      }],
      "invocations": [{
        "executionSuccessful": true,
        "properties": {
          "url": .url,
          "clarvia_score": .clarvia_score,
          "rating": .rating,
          "scan_id": .scan_id
        }
      }]
    }]
  }')

  SARIF_FILE="clarvia-results.sarif"
  echo "$SARIF" > "$SARIF_FILE"
  echo "SARIF results written to ${SARIF_FILE}"
  echo ""
  echo "$SARIF" | jq .

else
  # Text format (default)
  RATING_LABEL=$(rating_label "$RATING")
  echo "Clarvia Score: ${SCORE}/100 (${RATING_LABEL})"
  echo ""

  # Dimension scores
  for DIM in api_accessibility data_structuring agent_compatibility trust_signals; do
    DIM_SCORE=$(echo "$HTTP_BODY" | jq -r ".dimensions.${DIM}.score // 0")
    DIM_MAX=$(echo "$HTTP_BODY" | jq -r ".dimensions.${DIM}.max // 25")

    case "$DIM" in
      api_accessibility)  DIM_LABEL="API Accessibility" ;;
      data_structuring)   DIM_LABEL="Data Structuring" ;;
      agent_compatibility) DIM_LABEL="Agent Compatibility" ;;
      trust_signals)      DIM_LABEL="Trust Signals" ;;
      *)                  DIM_LABEL="$DIM" ;;
    esac

    BAR=$(bar "$DIM_SCORE" "$DIM_MAX")
    printf "  %-24s %2d/%d %s\n" "${DIM_LABEL}:" "$DIM_SCORE" "$DIM_MAX" "$BAR"
  done

  # Onchain bonus (if applicable)
  OB_APPLICABLE=$(echo "$HTTP_BODY" | jq -r '.onchain_bonus.applicable // false')
  if [[ "$OB_APPLICABLE" == "true" ]]; then
    OB_SCORE=$(echo "$HTTP_BODY" | jq -r '.onchain_bonus.score // 0')
    OB_MAX=$(echo "$HTTP_BODY" | jq -r '.onchain_bonus.max // 25')
    BAR=$(bar "$OB_SCORE" "$OB_MAX")
    printf "  %-24s %2d/%d %s\n" "Onchain Bonus:" "$OB_SCORE" "$OB_MAX" "$BAR"
  fi

  echo ""

  # Recommendations
  REC_COUNT=$(echo "$HTTP_BODY" | jq '.top_recommendations | length')
  if [[ "$REC_COUNT" -gt 0 ]]; then
    echo "Top Recommendations:"
    for i in $(seq 0 $(( REC_COUNT - 1 ))); do
      REC=$(echo "$HTTP_BODY" | jq -r ".top_recommendations[$i]")
      echo "  $(( i + 1 )). ${REC}"
    done
    echo ""
  fi

  echo "Badge: ${BADGE_URL}"
fi

# ---------------------------------------------------------------------------
# Job summary (GitHub Actions)
# ---------------------------------------------------------------------------
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## 🦉 Clarvia AEO Scan Results"
    echo ""
    echo "| Property | Value |"
    echo "|----------|-------|"
    echo "| URL | \`${SCAN_URL}\` |"
    echo "| Score | **${SCORE}/100** |"
    echo "| Rating | $(rating_label "$RATING") |"
    echo "| Scan ID | \`${SCAN_ID}\` |"
    echo ""
    echo "### Dimensions"
    echo ""
    echo "| Dimension | Score |"
    echo "|-----------|-------|"
    for DIM in api_accessibility data_structuring agent_compatibility trust_signals; do
      DIM_SCORE=$(echo "$HTTP_BODY" | jq -r ".dimensions.${DIM}.score // 0")
      DIM_MAX=$(echo "$HTTP_BODY" | jq -r ".dimensions.${DIM}.max // 25")
      case "$DIM" in
        api_accessibility)   DIM_LABEL="API Accessibility" ;;
        data_structuring)    DIM_LABEL="Data Structuring" ;;
        agent_compatibility) DIM_LABEL="Agent Compatibility" ;;
        trust_signals)       DIM_LABEL="Trust Signals" ;;
      esac
      echo "| ${DIM_LABEL} | ${DIM_SCORE}/${DIM_MAX} |"
    done
    echo ""
    echo "[![AEO Score](${BADGE_URL})](https://clarvia.art)"
  } >> "$GITHUB_STEP_SUMMARY"
fi

# ---------------------------------------------------------------------------
# Threshold check
# ---------------------------------------------------------------------------
if [[ "$FAIL_UNDER" -gt 0 && "$SCORE" -lt "$FAIL_UNDER" ]]; then
  echo ""
  echo "::error::AEO score ${SCORE} is below threshold ${FAIL_UNDER}"
  exit 1
fi

echo ""
echo "✓ Scan complete"
