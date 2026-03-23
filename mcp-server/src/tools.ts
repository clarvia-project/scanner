import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  searchServices,
  scanService,
  getServiceDetails,
  listCategories,
  getStats,
  registerService,
} from "./api-client.js";

export function registerTools(server: McpServer): void {
  // 1. search_services
  server.tool(
    "search_services",
    "Search Clarvia-indexed AI services by keyword, category, or minimum score",
    {
      query: z.string().optional().describe("Search keyword"),
      category: z.string().optional().describe("Filter by category"),
      min_score: z.number().min(0).max(100).optional().describe("Minimum Clarvia score (0-100)"),
      limit: z.number().min(1).max(100).optional().describe("Max results to return"),
    },
    async ({ query, category, min_score, limit }) => {
      try {
        const services = await searchServices({ query, category, min_score, limit });
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
}
