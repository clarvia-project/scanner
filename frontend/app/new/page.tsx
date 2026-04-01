import Link from "next/link";
import { Metadata } from "next";
import Nav from "@/app/components/Nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NewTool {
  scan_id?: string;
  tool_id?: string;
  name: string;
  url?: string;
  description?: string;
  clarvia_score: number;
  rating?: string;
  service_type?: string;
  category?: string;
  source?: string;
  added_at?: string;
  created_at?: string;
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchNewTools(): Promise<NewTool[]> {
  try {
    const res = await fetch(`${API_BASE}/v1/tools/new?limit=30`, {
      next: { revalidate: 1800 }, // 30 min cache
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.tools || data.services || data.results || data || [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Recently Added AI Tools & MCP Servers — Clarvia",
  description:
    "Discover the latest AI tools, MCP servers, and APIs added to the Clarvia index. Updated daily with new tools from GitHub, registries, and community submissions.",
  openGraph: {
    title: "Recently Added AI Tools & MCP Servers — Clarvia",
    description:
      "Latest AI tools and MCP servers added to the Clarvia index. Updated daily.",
    url: "https://clarvia.art/new",
    siteName: "Clarvia",
    type: "website",
  },
  alternates: {
    canonical: "https://clarvia.art/new",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreBg(score: number) {
  if (score >= 70) return "bg-emerald-500/15 border-emerald-500/30";
  if (score >= 40) return "bg-amber-500/15 border-amber-500/30";
  return "bg-red-500/15 border-red-500/30";
}

function toolHref(tool: NewTool) {
  const id = tool.tool_id || tool.scan_id || "";
  if (id.startsWith("tool_")) return `/tool/${id}`;
  if (id) return `/scan/${id}`;
  return "#";
}

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  github: { label: "GitHub", color: "bg-gray-500/15 text-gray-400 border-gray-500/25" },
  registry: { label: "Registry", color: "bg-blue-500/15 text-blue-400 border-blue-500/25" },
  submit: { label: "Submit", color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  crawl: { label: "Crawl", color: "bg-purple-500/15 text-purple-400 border-purple-500/25" },
};

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

function formatDate(dateStr?: string) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// JSON-LD
// ---------------------------------------------------------------------------

function NewToolsJsonLd({ tools }: { tools: NewTool[] }) {
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Recently Added AI Tools & MCP Servers",
    description: "Latest AI tools and MCP servers added to the Clarvia index.",
    url: "https://clarvia.art/new",
    numberOfItems: tools.length,
    itemListElement: tools.map((tool, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "SoftwareApplication",
        name: tool.name,
        url: tool.url || `https://clarvia.art${toolHref(tool)}`,
        description: tool.description || `${tool.name} — AEO Score: ${tool.clarvia_score}/100`,
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(itemList) }}
    />
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function NewToolsPage() {
  const tools = await fetchNewTools();

  return (
    <div className="min-h-screen flex flex-col">
      <NewToolsJsonLd tools={tools} />
      <Nav />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs text-muted mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">Home</Link>
          <span>/</span>
          <span className="text-foreground">New Tools</span>
        </nav>

        {/* Hero */}
        <div className="mb-8 space-y-3">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Recently Added</h1>
            <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              LIVE
            </span>
          </div>
          <p className="text-muted max-w-2xl">
            The latest AI tools, MCP servers, and APIs added to the Clarvia index.
            Discovered from GitHub, registries, crawlers, and community submissions.
          </p>
        </div>

        {/* Submit CTA */}
        <div className="glass-card rounded-xl p-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold mb-1">Have a tool to add?</h2>
            <p className="text-xs text-muted/70">
              Submit your AI tool, MCP server, or API to get indexed and scored by Clarvia.
            </p>
          </div>
          <Link
            href="/register"
            className="px-4 py-2 rounded-lg bg-accent text-white text-xs font-semibold hover:bg-accent/90 transition-colors flex-shrink-0"
          >
            Submit Your Tool
          </Link>
        </div>

        {/* Tools list */}
        {tools.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted mb-2">No recently added tools found.</p>
            <p className="text-xs text-muted/50">
              Check back soon — new tools are indexed daily.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tools.map((tool, idx) => {
              const sourceInfo = SOURCE_BADGES[(tool.source || "").toLowerCase()];
              const typeInfo = TYPE_LABELS[tool.service_type || ""] || TYPE_LABELS.general;
              const dateStr = formatDate(tool.added_at || tool.created_at);

              return (
                <Link
                  key={tool.tool_id || tool.scan_id || idx}
                  href={toolHref(tool)}
                  className="glass-card rounded-xl p-5 hover:border-accent/30 transition-all group flex items-start gap-4"
                >
                  {/* Score badge */}
                  <div className="flex-shrink-0">
                    <div className={`w-12 h-12 rounded-lg border flex items-center justify-center ${scoreBg(tool.clarvia_score)}`}>
                      <span className={`text-sm font-bold font-mono ${scoreColor(tool.clarvia_score)}`}>
                        {tool.clarvia_score}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h2 className="text-sm font-semibold group-hover:text-accent transition-colors">
                        {tool.name}
                      </h2>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${typeInfo.color}`}>
                        {typeInfo.label}
                      </span>
                      {sourceInfo && (
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${sourceInfo.color}`}>
                          {sourceInfo.label}
                        </span>
                      )}
                    </div>
                    {tool.description && (
                      <p className="text-xs text-muted/70 line-clamp-2 leading-relaxed mb-2">
                        {tool.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-[10px] text-muted/50">
                      {tool.url && (
                        <span className="font-mono truncate max-w-[200px]">{tool.url}</span>
                      )}
                      {tool.category && (
                        <>
                          <span className="w-1 h-1 rounded-full bg-muted/20" />
                          <span>{tool.category}</span>
                        </>
                      )}
                      {dateStr && (
                        <>
                          <span className="w-1 h-1 rounded-full bg-muted/20" />
                          <span>{dateStr}</span>
                        </>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
