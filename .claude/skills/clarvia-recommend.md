---
description: Get tool recommendations for a specific use case from Clarvia
---

You have the Clarvia MCP server available. Use it to recommend the best tools for a given use case.

## Instructions

1. Take the use case description from $ARGUMENTS (e.g., "send emails", "database management", "payment processing").

2. Use `search_services` with the use case as query, setting `min_score` to 50 to filter low-quality tools. Request up to 10 results.

3. Use `list_categories` to identify the most relevant category for the use case.

4. If the initial search returns fewer than 3 results, broaden the search by:
   - Removing the min_score filter
   - Trying related keywords from the use case

5. For the top 3 results, use `get_service_details` to get full scoring breakdowns.

6. Present the results in this format:

```
## Tool Recommendations: {use_case}

### Top Picks

#### 1. {tool_name} - Score: {score}/100 ({agent_grade})
- **Type**: {service_type} | **Category**: {category}
- **Why**: {1-line summary of strengths}
- **Install**: `{install_command or URL}`

#### 2. {tool_name} - Score: {score}/100 ({agent_grade})
...

#### 3. {tool_name} - Score: {score}/100 ({agent_grade})
...

### Quick Comparison
| Tool | Score | Grade | Type | Difficulty |
|------|-------|-------|------|------------|
| ...  | ...   | ...   | ...  | ...        |
```

7. If no tools score above 60, mention this explicitly and suggest the user consider building a custom solution or checking back later as the catalog grows.
