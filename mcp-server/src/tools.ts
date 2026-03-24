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
} from "./api-client.js";

export function registerTools(server: McpServer): void {
  // 1. search_services
  server.tool(
    "search_services",
    "Search Clarvia-indexed AI services by keyword, category, or minimum score",
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
    "Scan a URL to evaluate it with Clarvia's scoring system",
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
    "Get detailed evaluation results for a specific service by scan ID",
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
    "List all Clarvia service categories with service counts",
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
    "Get overall Clarvia statistics: total services, average score, distribution",
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
    "Register a new service for Clarvia evaluation",
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
    "Check if a service is safe for agent tool-use. Returns pass/fail with agent grade (AGENT_NATIVE/FRIENDLY/POSSIBLE/HOSTILE). Use before calling any external API.",
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
    "Check multiple service URLs at once. Returns pass/fail + agent grade for each. Use for comparing services or pre-filtering tool candidates.",
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
    "Find alternative services with high agent-readiness scores in a given category. Use when a service fails the gate check.",
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
    "Run a real-time accessibility probe on a service. Checks reachability, response time, OpenAPI spec, MCP support, and agents.json presence.",
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
    "Report the outcome of using a service (success/failure/partial). Helps build reliability data for agent tool selection.",
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
}
