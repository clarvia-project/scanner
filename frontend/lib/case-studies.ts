/**
 * Clarvia AEO Case Studies
 *
 * Each case study demonstrates causation: improving AEO score dimensions
 * directly leads to increased agent adoption / traffic.
 */

export interface CaseStudy {
  /** Tool / service name */
  tool_name: string;
  /** Short slug for linking */
  slug: string;
  /** Category label */
  category: string;
  /** Score before improvements */
  before_score: number;
  /** Score after improvements */
  after_score: number;
  /** What the team changed */
  changes_made: string[];
  /** Key metric improvement headline (e.g. "3x agent adoption") */
  metric_improvement: string;
  /** Numeric multiplier for visual emphasis */
  metric_multiplier: number;
  /** Time it took to see results */
  timeframe: string;
  /** 1-2 sentence narrative */
  quote: string;
  /** Which AEO dimensions improved most */
  dimensions_improved: string[];
}

export const CASE_STUDIES: CaseStudy[] = [
  {
    tool_name: "MCP Weather Server",
    slug: "mcp-weather-server",
    category: "MCP Server",
    before_score: 42,
    after_score: 71,
    changes_made: [
      "Added rate limiting with retry-after headers",
      "Structured error responses with machine-readable codes",
      "Published MCP manifest with tool descriptions",
      "Added health check endpoint with latency metrics",
    ],
    metric_improvement: "3x agent adoption",
    metric_multiplier: 3,
    timeframe: "3 weeks",
    quote:
      "After Clarvia flagged missing rate-limit headers and unstructured errors, " +
      "we spent one afternoon fixing both. Agent integrations tripled within 3 weeks " +
      "because agents could finally handle our API gracefully.",
    dimensions_improved: ["API Quality", "Trust Signals"],
  },
  {
    tool_name: "AI Code Reviewer",
    slug: "ai-code-reviewer",
    category: "Developer Tool",
    before_score: 55,
    after_score: 78,
    changes_made: [
      "Added complete OpenAPI 3.1 specification",
      "Implemented cursor-based pagination on all list endpoints",
      "Added .well-known/ai-plugin.json manifest",
      "Structured all errors with type, message, and suggestion fields",
      "Published SDK with typed responses",
    ],
    metric_improvement: "5x API calls from agents",
    metric_multiplier: 5,
    timeframe: "2 weeks",
    quote:
      "Our OpenAPI spec was incomplete and agents kept hallucinating endpoints. " +
      "Once we added full specs and pagination, Claude and GPT-based agents " +
      "started calling us 5x more because they could discover every endpoint.",
    dimensions_improved: ["API Quality", "Data Format"],
  },
  {
    tool_name: "Data Pipeline Tool",
    slug: "data-pipeline-tool",
    category: "Data Infrastructure",
    before_score: 38,
    after_score: 65,
    changes_made: [
      "Built MCP server with 12 tool definitions",
      "Added OAuth 2.0 with proper scope descriptions",
      "Created structured JSON responses for all endpoints",
      "Added Cursor integration guide with installation command",
    ],
    metric_improvement: "2x Cursor integrations",
    metric_multiplier: 2,
    timeframe: "4 weeks",
    quote:
      "We had zero MCP presence. After building our MCP server and adding auth " +
      "with clear scope descriptions, Cursor users started integrating us organically. " +
      "We went from invisible to discoverable.",
    dimensions_improved: ["Agent Integration", "Trust Signals"],
  },
];

/**
 * Returns the CSS color class for a given score.
 */
export function scoreColorClass(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

/**
 * Score improvement percentage, rounded.
 */
export function improvementPercent(before: number, after: number): number {
  if (before === 0) return 0;
  return Math.round(((after - before) / before) * 100);
}
