import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  searchServices,
  scanService,
  getServiceDetails,
  listCategories,
  getStats,
  registerService,
  gateCheck,
  batchCheck,
  findAlternatives,
  probeService,
  submitFeedback,
  registerSetup,
  compareSetup,
  recommendForSetup,
} from "./api-client.js";

export function registerTools(server: McpServer): void {
  // 1. search_services
  server.tool(
    "search_services",
    "Search 12,800+ AI agent tools (MCP servers, APIs, CLIs) by keyword, category, or score. Use when you need to find the best tool for a specific task, compare alternatives, or check agent readiness. Returns Clarvia AEO scores (0-100) indicating how easily AI agents can discover and use each service.",
    {
      query: z.string().optional().describe("Search keyword"),
      category: z.string().optional().describe("Filter by category"),
      service_type: z.enum(["mcp_server", "skill", "cli_tool", "api", "general"]).optional().describe("Filter by service type"),
      min_score: z.number().min(0).max(100).optional().describe("Minimum Clarvia score (0-100)"),
      limit: z.number().min(1).max(100).optional().describe("Max results to return"),
    },
    async ({ query, category, service_type, min_score, limit }) => {
      try {
        const services = await searchServices({ query, category, service_type, min_score, limit });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(services, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 2. scan_service
  server.tool(
    "scan_service",
    "Run a full AEO audit on any URL — evaluates agent discoverability, API quality, documentation, and MCP readiness. Use when you need to score a website or API for AI agent compatibility, or when building an agent and want to verify a tool meets quality standards. Returns a Clarvia score (0-100) with detailed breakdown.",
    {
      url: z.string().url().describe("URL to scan"),
    },
    async ({ url }) => {
      try {
        const result = await scanService(url);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 3. get_service_details
  server.tool(
    "get_service_details",
    "Get the full AEO evaluation report for a previously scanned service. Use when you need detailed scoring breakdown (documentation, API design, error handling, auth, MCP support) or want to understand why a tool scored high or low. Requires a scan_id from search_services or scan_service results.",
    {
      scan_id: z.string().describe("Scan ID from a previous scan or search result"),
    },
    async ({ scan_id }) => {
      try {
        const details = await getServiceDetails(scan_id);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(details, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 4. list_categories
  server.tool(
    "list_categories",
    "List all tool categories in the Clarvia directory with service counts per category. Use when you need to browse available categories before searching, discover what types of AI tools exist, or build a category-based navigation for agent tool selection.",
    {},
    async () => {
      try {
        const categories = await listCategories();
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(categories, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 5. get_stats
  server.tool(
    "get_stats",
    "Get aggregate statistics for the Clarvia tool directory — total indexed services, average AEO score, score distribution, and category breakdown. Use when you need an overview of the AI tool ecosystem quality, want to benchmark a tool against the average, or report on agent-readiness trends.",
    {},
    async () => {
      try {
        const stats = await getStats();
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(stats, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 6. register_service
  server.tool(
    "register_service",
    "Submit a new AI tool, MCP server, API, or CLI for Clarvia indexing and AEO scoring. Use when you want to register your service in the directory, get an agent-readiness evaluation, or make your tool discoverable by AI agents. The service will be queued for automated scanning.",
    {
      name: z.string().describe("Service name"),
      url: z.string().url().describe("Service URL"),
      description: z.string().describe("Brief description of the service"),
      category: z.string().describe("Service category"),
      github_url: z.string().url().optional().describe("GitHub repository URL"),
    },
    async ({ name, url, description, category, github_url }) => {
      try {
        const result = await registerService({ name, url, description, category, github_url });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // --- v2 Agent-first tools ---

  // 7. clarvia_gate_check — pass/fail boolean for agent tool-use decisions
  server.tool(
    "clarvia_gate_check",
    "Quick pass/fail safety check for agent tool-use decisions. Returns an agent grade (AGENT_NATIVE / AGENT_FRIENDLY / AGENT_POSSIBLE / AGENT_HOSTILE) with a boolean pass result. Use before calling any external API or MCP server to verify it meets your minimum quality threshold. Essential for autonomous agent workflows that need to validate tools at runtime.",
    {
      url: z.string().url().describe("Service URL to check"),
      min_rating: z
        .enum(["AGENT_NATIVE", "AGENT_FRIENDLY", "AGENT_POSSIBLE", "AGENT_HOSTILE"])
        .optional()
        .describe("Minimum acceptable grade (default: AGENT_FRIENDLY)"),
    },
    async ({ url, min_rating }) => {
      try {
        const result = await gateCheck(url, min_rating || "AGENT_FRIENDLY");
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 8. clarvia_batch_check — check multiple URLs at once
  server.tool(
    "clarvia_batch_check",
    "Batch-check up to 10 service URLs in a single call — returns pass/fail and agent grade for each. Use when comparing multiple tool candidates side-by-side, pre-filtering a list of APIs before integration, or building an agent that selects the best tool from several options. More efficient than calling gate_check repeatedly.",
    {
      urls: z.array(z.string().url()).min(1).max(10).describe("List of service URLs (max 10)"),
    },
    async ({ urls }) => {
      try {
        const result = await batchCheck(urls);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 9. clarvia_find_alternatives — find better-rated services in a category
  server.tool(
    "clarvia_find_alternatives",
    "Find higher-rated alternative tools in a given category, ranked by agent-readiness score. Use when a service fails the gate check and you need a replacement, when comparing options in a category (payment, AI, crypto, SaaS), or when an agent needs to fall back to a better-scored tool automatically.",
    {
      category: z.string().describe("Service category (e.g. 'payment', 'ai', 'crypto', 'saas')"),
      min_score: z.number().min(0).max(100).optional().describe("Minimum score (default: 70)"),
      limit: z.number().min(1).max(20).optional().describe("Max results (default: 10)"),
    },
    async ({ category, min_score, limit }) => {
      try {
        const result = await findAlternatives(category, min_score || 70, limit || 10);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 10. clarvia_probe — real-time accessibility probe
  server.tool(
    "clarvia_probe",
    "Run a live accessibility probe on a service URL right now — checks HTTP reachability, response latency, OpenAPI/Swagger spec presence, MCP server-card availability, and agents.json discovery endpoint. Use when you need real-time health status (not cached scores), want to verify a service is online before calling it, or are debugging connectivity issues with an agent tool.",
    {
      url: z.string().url().describe("Service URL to probe"),
    },
    async ({ url }) => {
      try {
        const result = await probeService(url);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 11. clarvia_submit_feedback — report service usage outcome
  server.tool(
    "clarvia_submit_feedback",
    "Report the outcome after using a tool (success / failure / partial) to contribute to Clarvia's reliability dataset. Use after every agent tool invocation to help build community-driven quality signals. Accepts optional latency and error details. Improves future agent tool selection accuracy for all users.",
    {
      profile_id: z.string().describe("Profile ID of the service used"),
      outcome: z.enum(["success", "failure", "partial"]).describe("Usage outcome"),
      agent_id: z.string().optional().describe("Your agent identifier"),
      error_message: z.string().optional().describe("Error details if failed"),
      latency_ms: z.number().optional().describe("Response latency in ms"),
    },
    async ({ profile_id, outcome, agent_id, error_message, latency_ms }) => {
      try {
        const result = await submitFeedback({ profile_id, outcome, agent_id, error_message, latency_ms });
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // --- Setup comparison tools ---

  // 12. register_my_setup — register agent's tool list
  server.tool(
    "register_my_setup",
    "Register your current tool setup (MCP servers, CLIs, APIs, Skills) with Clarvia to get AEO scores and category rankings for each tool. Use when you want to benchmark your agent's toolchain, track setup quality over time, or prepare for comparison and upgrade recommendations. Returns a setup_id for use with compare_my_setup and recommend_upgrades.",
    {
      tools: z.array(z.string()).min(1).max(50).describe("List of tool names you currently use (e.g. ['dune-mcp', 'notion-mcp', 'telegram-bot'])"),
      setup_id: z.string().optional().describe("Custom setup ID (auto-generated hash if omitted)"),
    },
    async ({ tools, setup_id }) => {
      try {
        const result = await registerSetup(tools, setup_id);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 13. compare_my_setup — compare setup vs alternatives
  server.tool(
    "compare_my_setup",
    "Compare your registered tool setup against higher-scored alternatives in each category. Shows the best available upgrades for each tool and the category average score. Use after register_my_setup to identify weak spots in your toolchain and find better-rated replacements. Requires a setup_id from register_my_setup.",
    {
      setup_id: z.string().describe("Setup ID from register_my_setup"),
    },
    async ({ setup_id }) => {
      try {
        const result = await compareSetup(setup_id);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );

  // 14. recommend_upgrades — get personalized tool recommendations
  server.tool(
    "recommend_upgrades",
    "Get personalized tool recommendations based on your registered setup. Suggests high-scoring tools you don't have yet — both within your existing categories and in complementary adjacent categories. Uses 'users with X also use Y' heuristics. Requires a setup_id from register_my_setup.",
    {
      setup_id: z.string().describe("Setup ID from register_my_setup"),
      limit: z.number().min(1).max(50).optional().describe("Max recommendations to return (default: 10)"),
    },
    async ({ setup_id, limit }) => {
      try {
        const result = await recommendForSetup(setup_id, limit || 10);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (err) {
        return {
          content: [{ type: "text" as const, text: `Error: ${(err as Error).message}` }],
          isError: true,
        };
      }
    },
  );
}
