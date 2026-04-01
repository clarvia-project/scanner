import Link from "next/link";
import { Metadata } from "next";
import Nav from "@/app/components/Nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// ---------------------------------------------------------------------------
// Category mapping
// ---------------------------------------------------------------------------

const CATEGORY_MAP: Record<string, string> = {
  ai: "AI & Machine Learning",
  developer_tools: "Developer Tools",
  mcp: "MCP Servers",
  database: "Database",
  communication: "Communication",
  data: "Data & Analytics",
  productivity: "Productivity",
  blockchain: "Blockchain & Web3",
  search: "Search",
  storage: "Storage",
  security: "Security",
  monitoring: "Monitoring",
  automation: "Automation",
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  ai: "Top-ranked AI and machine learning tools for autonomous agents. Compare models, inference APIs, and ML platforms by AEO score.",
  developer_tools: "Best developer tools ranked by agent readiness. IDEs, linters, formatters, and dev platforms scored for AI compatibility.",
  mcp: "Top MCP (Model Context Protocol) servers ranked by Clarvia AEO score. Find the best MCP servers for Claude, GPT, and other AI agents.",
  database: "Best database tools for AI agents. Compare vector DBs, SQL engines, and data stores by agent compatibility score.",
  communication: "Top communication tools scored for AI agent integration. Messaging, email, and notification APIs ranked by AEO.",
  data: "Best data and analytics tools for agents. ETL pipelines, visualization platforms, and analytics APIs ranked by score.",
  productivity: "Top productivity tools ranked for AI agent use. Task management, calendars, and workflow tools scored by AEO.",
  blockchain: "Best blockchain and Web3 tools for AI agents. DEX APIs, wallet tools, and on-chain data platforms ranked by score.",
  search: "Top search tools and APIs for AI agents. Full-text, semantic, and web search engines ranked by agent readiness.",
  storage: "Best storage tools for AI agents. Cloud storage, file management, and CDN services ranked by AEO score.",
  security: "Top security tools ranked for agent integration. Auth providers, vulnerability scanners, and security APIs scored.",
  monitoring: "Best monitoring tools for AI agents. APM, logging, and alerting platforms ranked by agent compatibility.",
  automation: "Top automation tools for AI agents. Workflow engines, schedulers, and integration platforms ranked by AEO score.",
};

// ---------------------------------------------------------------------------
// FAQ generation
// ---------------------------------------------------------------------------

function generateFAQ(category: string, displayName: string) {
  return [
    {
      question: `What are the best ${displayName.toLowerCase()} tools for AI agents?`,
      answer: `Clarvia ranks ${displayName.toLowerCase()} tools by AEO (AI Engine Optimization) score, measuring agent readiness across API accessibility, data structuring, agent compatibility, and trust signals. The top tools are listed on this page, updated regularly.`,
    },
    {
      question: `How is the AEO score calculated for ${displayName.toLowerCase()} tools?`,
      answer: `The Clarvia AEO score (0-100) evaluates four dimensions: API Accessibility (endpoint design, documentation), Data Structuring (response formats, schemas), Agent Compatibility (MCP support, tool definitions), and Trust Signals (uptime, security, community adoption).`,
    },
    {
      question: `How often are the ${displayName.toLowerCase()} rankings updated?`,
      answer: `Rankings are refreshed regularly as Clarvia continuously scans and re-evaluates tools across the ecosystem. New tools are added as they are discovered or submitted.`,
    },
  ];
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ToolEntry {
  scan_id?: string;
  tool_id?: string;
  name: string;
  url?: string;
  description?: string;
  clarvia_score: number;
  rating?: string;
  service_type?: string;
  category?: string;
  install_command?: string;
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchCategoryTools(category: string): Promise<ToolEntry[]> {
  try {
    const res = await fetch(
      `${API_BASE}/v1/services?category=${encodeURIComponent(category)}&sort=score_desc&limit=20&fields=standard`,
      { next: { revalidate: 3600 } }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.services || data.tools || data.results || data || [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

type PageProps = { params: Promise<{ category: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { category } = await params;
  const displayName = CATEGORY_MAP[category] || category;
  const description =
    CATEGORY_DESCRIPTIONS[category] ||
    `Best ${displayName} tools for AI agents, ranked by Clarvia AEO score.`;

  return {
    title: `Best ${displayName} Tools for Agents (2026) — Clarvia Rankings`,
    description,
    openGraph: {
      title: `Best ${displayName} Tools for Agents (2026) — Clarvia Rankings`,
      description,
      url: `https://clarvia.art/best/${category}`,
      siteName: "Clarvia",
      type: "website",
    },
    alternates: {
      canonical: `https://clarvia.art/best/${category}`,
    },
  };
}

export function generateStaticParams() {
  return Object.keys(CATEGORY_MAP).map((category) => ({ category }));
}

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

function toolHref(tool: ToolEntry) {
  const id = tool.tool_id || tool.scan_id || "";
  if (id.startsWith("tool_")) return `/tool/${id}`;
  if (id) return `/scan/${id}`;
  return "#";
}

// ---------------------------------------------------------------------------
// JSON-LD
// ---------------------------------------------------------------------------

function CategoryJsonLd({
  category,
  displayName,
  tools,
}: {
  category: string;
  displayName: string;
  tools: ToolEntry[];
}) {
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `Best ${displayName} Tools for AI Agents (2026)`,
    description: CATEGORY_DESCRIPTIONS[category] || `Top ${displayName} tools ranked by AEO score.`,
    url: `https://clarvia.art/best/${category}`,
    numberOfItems: tools.length,
    itemListElement: tools.map((tool, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "SoftwareApplication",
        name: tool.name,
        url: tool.url || `https://clarvia.art${toolHref(tool)}`,
        applicationCategory: displayName,
        description: tool.description || `${tool.name} — AEO Score: ${tool.clarvia_score}/100`,
        aggregateRating: {
          "@type": "AggregateRating",
          ratingValue: tool.clarvia_score,
          bestRating: 100,
          worstRating: 0,
          ratingCount: 1,
        },
      },
    })),
  };

  const faqItems = generateFAQ(category, displayName);
  const faqLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: f.answer,
      },
    })),
  };

  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: "https://clarvia.art" },
      { "@type": "ListItem", position: 2, name: "Best Tools", item: "https://clarvia.art/best" },
      { "@type": "ListItem", position: 3, name: displayName, item: `https://clarvia.art/best/${category}` },
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(itemList) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function BestCategoryPage({ params }: PageProps) {
  const { category } = await params;
  const displayName = CATEGORY_MAP[category] || category;
  const tools = await fetchCategoryTools(category);
  const faqItems = generateFAQ(category, displayName);

  return (
    <div className="min-h-screen flex flex-col">
      <CategoryJsonLd category={category} displayName={displayName} tools={tools} />
      <Nav />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs text-muted mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">Home</Link>
          <span>/</span>
          <Link href="/best" className="hover:text-foreground transition-colors">Best Tools</Link>
          <span>/</span>
          <span className="text-foreground">{displayName}</span>
        </nav>

        {/* Hero */}
        <div className="mb-8 space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">
            Best {displayName} Tools for Agents
          </h1>
          <p className="text-muted max-w-2xl">
            {CATEGORY_DESCRIPTIONS[category] ||
              `Top ${displayName} tools ranked by Clarvia AEO score for AI agent compatibility.`}
          </p>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="font-mono">{tools.length} tools ranked</span>
            <span className="w-1 h-1 rounded-full bg-muted/30" />
            <span>Updated 2026</span>
          </div>
        </div>

        {/* Tools list */}
        {tools.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted">No tools found for this category yet.</p>
            <Link href="/best" className="text-accent text-sm mt-2 inline-block hover:underline">
              Browse all categories
            </Link>
          </div>
        ) : (
          <div className="space-y-3 mb-12">
            {tools.map((tool, idx) => (
              <Link
                key={tool.tool_id || tool.scan_id || idx}
                href={toolHref(tool)}
                className="glass-card rounded-xl p-5 hover:border-accent/30 transition-all group flex items-start gap-4"
              >
                {/* Rank */}
                <div className="flex-shrink-0 w-8 text-right">
                  <span className="text-lg font-bold text-muted/30 font-mono">
                    {idx + 1}
                  </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-sm font-semibold group-hover:text-accent transition-colors truncate">
                      {tool.name}
                    </h2>
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${scoreBg(tool.clarvia_score)} ${scoreColor(tool.clarvia_score)}`}>
                      {tool.clarvia_score}
                    </span>
                    {tool.rating && (
                      <span className="text-[10px] text-muted font-mono hidden sm:inline">
                        {tool.rating}
                      </span>
                    )}
                  </div>
                  {tool.description && (
                    <p className="text-xs text-muted/70 line-clamp-2 leading-relaxed mb-2">
                      {tool.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-[10px] text-muted/50">
                    {tool.url && <span className="font-mono truncate max-w-[200px]">{tool.url}</span>}
                    {tool.install_command && (
                      <code className="bg-card-border/20 px-1.5 py-0.5 rounded font-mono">
                        {tool.install_command}
                      </code>
                    )}
                  </div>
                </div>

                {/* Compare link */}
                <div className="flex-shrink-0 hidden sm:block">
                  <span className="text-[10px] text-muted/40 group-hover:text-accent/60 transition-colors">
                    Compare &rarr;
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* FAQ Section */}
        <section className="mb-12">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {faqItems.map((faq, i) => (
              <div key={i} className="glass-card rounded-xl p-5">
                <h3 className="text-sm font-semibold mb-2">{faq.question}</h3>
                <p className="text-xs text-muted/70 leading-relaxed">{faq.answer}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Other categories */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Other Categories
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(CATEGORY_MAP)
              .filter(([slug]) => slug !== category)
              .map(([slug, name]) => (
                <Link
                  key={slug}
                  href={`/best/${slug}`}
                  className="text-xs px-3 py-1.5 rounded-full border border-card-border/50 text-muted hover:text-foreground hover:border-accent/30 transition-all"
                >
                  {name}
                </Link>
              ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-card-border/30 py-6 text-center text-xs text-muted/50">
        Clarvia — The AEO Standard for Agent Discoverability
      </footer>
    </div>
  );
}
