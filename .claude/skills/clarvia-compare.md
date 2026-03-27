---
description: Compare two tools head-to-head using Clarvia AEO scores
---

You have the Clarvia MCP server available. Use it to compare two tools side-by-side.

## Instructions

1. Parse $ARGUMENTS to extract two tool identifiers (URLs or names), separated by "vs", "and", a comma, or whitespace.

2. For each tool:
   - If it is a URL, use `scan_service` to get its AEO score.
   - If it is a name, use `search_services` to find it, then `get_service_details` for the full breakdown.

3. If both tools are found, also use `clarvia_batch_check` with both URLs for a direct comparison.

4. Present the results in this format:

```
## Head-to-Head: {tool_A} vs {tool_B}

| Dimension            | {tool_A} | {tool_B} | Winner |
|----------------------|----------|----------|--------|
| Overall Score        | X/100    | X/100    | {name} |
| API Accessibility    | X/25     | X/25     | {name} |
| Data Structuring     | X/25     | X/25     | {name} |
| Agent Compatibility  | X/25     | X/25     | {name} |
| Trust Signals        | X/25     | X/25     | {name} |

**Agent Grade**: {tool_A} = {grade_A} | {tool_B} = {grade_B}

### Verdict
{1-2 sentence summary of which tool is better for agent use and why}
```

5. If one tool scores significantly lower (>15 points difference), suggest it as the weaker option and recommend the stronger one.
