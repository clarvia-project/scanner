import Link from "next/link";
import { Metadata } from "next";
import Nav from "@/app/components/Nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// ---------------------------------------------------------------------------
// Category mapping
// ---------------------------------------------------------------------------

const CATEGORIES: { slug: string; name: string }[] = [
  { slug: "ai", name: "AI & Machine Learning" },
  { slug: "developer_tools", name: "Developer Tools" },
  { slug: "mcp", name: "MCP Servers" },
  { slug: "database", name: "Database" },
  { slug: "communication", name: "Communication" },
  { slug: "data", name: "Data & Analytics" },
  { slug: "productivity", name: "Productivity" },
  { slug: "blockchain", name: "Blockchain & Web3" },
  { slug: "search", name: "Search" },
  { slug: "storage", name: "Storage" },
  { slug: "security", name: "Security" },
  { slug: "monitoring", name: "Monitoring" },
  { slug: "automation", name: "Automation" },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ToolPreview {
  scan_id?: string;
  tool_id?: string;
  name: string;
  clarvia_score: number;
  description?: string;
}

interface CategoryData {
  slug: string;
  name: string;
  count: number;
  avgScore: number;
  topTools: ToolPreview[];
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchCategorySummaries(): Promise<CategoryData[]> {
  const results: CategoryData[] = [];

  // Fetch top 3 per category in parallel
  const fetches = CATEGORIES.map(async ({ slug, name }) => {
    try {
      const res = await fetch(
        `${API_BASE}/v1/services?category=${encodeURIComponent(slug)}&sort=score_desc&limit=3&fields=standard`,
        { next: { revalidate: 3600 } }
      );
      if (!res.ok) return { slug, name, count: 0, avgScore: 0, topTools: [] };
      const data = await res.json();
      const tools: ToolPreview[] = data.services || data.tools || data.results || data || [];
      const total = data.total || data.count || tools.length;
      const avg =
        tools.length > 0
          ? Math.round(tools.reduce((s: number, t: ToolPreview) => s + (t.clarvia_score || 0), 0) / tools.length)
          : 0;
      return { slug, name, count: total, avgScore: avg, topTools: tools.slice(0, 3) };
    } catch {
      return { slug, name, count: 0, avgScore: 0, topTools: [] };
    }
  });

  const settled = await Promise.all(fetches);
  results.push(...settled);

  // Sort: categories with the most tools first
  results.sort((a, b) => b.count - a.count);

  return results;
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: "Best AI Tools for Agents by Category (2026) — Clarvia Rankings",
  description:
    "Browse the best AI tools, MCP servers, and APIs organized by category. Each category ranked by Clarvia AEO score for agent readiness.",
  openGraph: {
    title: "Best AI Tools for Agents by Category (2026) — Clarvia Rankings",
    description:
      "Browse the best AI tools organized by category. Ranked by AEO score for agent readiness.",
    url: "https://clarvia.art/best",
    siteName: "Clarvia",
    type: "website",
  },
  alternates: {
    canonical: "https://clarvia.art/best",
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

function toolHref(tool: ToolPreview) {
  const id = tool.tool_id || tool.scan_id || "";
  if (id.startsWith("tool_")) return `/tool/${id}`;
  if (id) return `/scan/${id}`;
  return "#";
}

// ---------------------------------------------------------------------------
// JSON-LD
// ---------------------------------------------------------------------------

function BestIndexJsonLd({ categories }: { categories: CategoryData[] }) {
  const itemList = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Best AI Tools for Agents by Category",
    description:
      "Browse the best AI tools, MCP servers, and APIs organized by category, ranked by Clarvia AEO score.",
    url: "https://clarvia.art/best",
    hasPart: categories.map((cat) => ({
      "@type": "ItemList",
      name: `Best ${cat.name} Tools`,
      url: `https://clarvia.art/best/${cat.slug}`,
      numberOfItems: cat.count,
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

export default async function BestIndexPage() {
  const categories = await fetchCategorySummaries();

  return (
    <div className="min-h-screen flex flex-col">
      <BestIndexJsonLd categories={categories} />
      <Nav />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs text-muted mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">Home</Link>
          <span>/</span>
          <span className="text-foreground">Best Tools</span>
        </nav>

        {/* Hero */}
        <div className="mb-8 space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">Best Tools by Category</h1>
          <p className="text-muted max-w-2xl">
            Browse the top AI tools, MCP servers, and APIs organized by category. Each tool ranked by
            Clarvia AEO score for agent readiness.
          </p>
        </div>

        {/* Category grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.slug}
              href={`/best/${cat.slug}`}
              className="glass-card rounded-xl p-5 hover:border-accent/30 transition-all group"
            >
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold group-hover:text-accent transition-colors">
                  {cat.name}
                </h2>
                <div className="flex items-center gap-3 text-[10px] text-muted font-mono">
                  {cat.count > 0 && <span>{cat.count} tools</span>}
                  {cat.avgScore > 0 && (
                    <span className={scoreColor(cat.avgScore)}>avg {cat.avgScore}</span>
                  )}
                </div>
              </div>

              {/* Top 3 preview */}
              {cat.topTools.length > 0 ? (
                <div className="space-y-2">
                  {cat.topTools.map((tool, i) => (
                    <div key={tool.tool_id || tool.scan_id || i} className="flex items-center gap-2">
                      <span className="text-[10px] text-muted/30 font-mono w-4 text-right">
                        {i + 1}
                      </span>
                      <span className="text-xs truncate flex-1">{tool.name}</span>
                      <span className={`text-[10px] font-mono font-bold ${scoreColor(tool.clarvia_score)}`}>
                        {tool.clarvia_score}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-muted/40">No tools ranked yet</p>
              )}

              <div className="mt-3 text-[10px] text-muted/40 group-hover:text-accent/60 transition-colors">
                View all {cat.name.toLowerCase()} tools &rarr;
              </div>
            </Link>
          ))}
        </div>
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
