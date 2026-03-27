---
description: Scan a tool or MCP server for its Clarvia AEO score
---

You have the Clarvia MCP server available. Use it to perform an AEO (Agent Engine Optimization) audit.

## Instructions

1. Take the URL or tool name from $ARGUMENTS.

2. If a URL is provided, use the `scan_service` tool with the URL to run a full AEO audit.

3. If a tool name (not a URL) is provided, first use `search_services` with the name as query to find it, then use `get_service_details` with the returned `scan_id` to get the full breakdown.

4. Present the results in this format:

```
## AEO Scan: {service_name}

**Score**: {clarvia_score}/100 | **Grade**: {agent_grade} | **Rating**: {rating}

### Dimension Breakdown
| Dimension            | Score | Max |
|----------------------|-------|-----|
| API Accessibility    | X     | 25  |
| Data Structuring     | X     | 25  |
| Agent Compatibility  | X     | 25  |
| Trust Signals        | X     | 25  |

### Top Recommendations
{list each recommendation as a bullet point}
```

5. If the grade is below AGENT_FRIENDLY, automatically run `clarvia_find_alternatives` with the tool's category and present 3 better-scored alternatives.
