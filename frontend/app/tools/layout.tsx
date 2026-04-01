import { Suspense } from "react";
import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface Tool {
  name: string;
  scan_id?: string;
  url?: string;
  description?: string;
  clarvia_score?: number;
  score?: number;
  category?: string;
  service_type?: string;
}

async function fetchTopTools(): Promise<Tool[]> {
  try {
    const res = await fetch(`${API_BASE}/v1/leaderboard?limit=10`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      return data.leaderboard ?? [];
    }
  } catch {
    /* ignore */
  }
  return [];
}

export const metadata: Metadata = {
  title: "AI Agent Tool Directory — 27,843+ Tools Scored | Clarvia",
  description:
    "Browse and search 27,843+ AI agent tools including MCP servers, APIs, CLI tools, and skills. Every tool scored for agent readiness with the Clarvia AEO standard.",
  keywords: [
    "MCP server directory",
    "AI agent tools",
    "AEO score",
    "MCP servers list",
    "AI Engine Optimization",
    "agent-ready tools",
    "tool discovery",
    "Clarvia",
  ],
  openGraph: {
    title: "AI Agent Tool Directory | Clarvia",
    description:
      "Search 27,843+ MCP servers, APIs, CLI tools, and skills scored for agent readiness.",
    url: "https://clarvia.art/tools",
    siteName: "Clarvia",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AI Agent Tool Directory | Clarvia",
    description: "27,843+ MCP servers and AI tools scored for agent readiness.",
  },
  alternates: {
    canonical: "https://clarvia.art/tools",
  },
};

export default async function ToolsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const tools = await fetchTopTools();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "AI Agent Tool Directory — Clarvia",
    description:
      "The largest ranked directory of MCP servers, APIs, CLI tools, and agent skills. 27,843+ tools scored by Clarvia AEO standard.",
    url: "https://clarvia.art/tools",
    publisher: {
      "@type": "Organization",
      name: "Clarvia",
      url: "https://clarvia.art",
    },
    mainEntity: {
      "@type": "ItemList",
      name: "Top-Rated AI Agent Tools",
      description: "Highest-scoring MCP servers and AI tools in the Clarvia directory.",
      numberOfItems: 27843,
      itemListOrder: "https://schema.org/ItemListOrderDescending",
      itemListElement: tools.map((tool, idx) => ({
        "@type": "ListItem",
        position: idx + 1,
        item: {
          "@type": "SoftwareApplication",
          name: tool.name,
          description:
            tool.description ??
            `${tool.name} — AEO score ${tool.clarvia_score ?? tool.score ?? "N/A"}/100`,
          url: tool.scan_id
            ? `https://clarvia.art/tool/${tool.scan_id}`
            : tool.url ?? "#",
          applicationCategory: "DeveloperApplication",
        },
      })),
    },
  };

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "How many AI agent tools does Clarvia index?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Clarvia indexes 27,843+ AI agent tools including MCP servers, REST APIs, CLI tools, and agent skills. Each tool is scored on a 0-100 AEO (AI Engine Optimization) scale measuring agent readiness.",
        },
      },
      {
        "@type": "Question",
        name: "What types of tools are in the Clarvia directory?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "The directory includes MCP (Model Context Protocol) servers, REST APIs, CLI tools, and agent skills. Categories include developer tools, databases, AI/ML, communication, productivity, blockchain, payments, and more.",
        },
      },
      {
        "@type": "Question",
        name: "How do I find the best MCP server for my use case?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Use Clarvia's search to describe what you want to accomplish — the intent-based recommendation engine returns ranked tool suggestions. You can also filter by category, service type, or minimum AEO score.",
        },
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <Suspense>{children}</Suspense>
    </>
  );
}
