import Link from "next/link";
import Image from "next/image";

interface Category {
  name: string;
  count: number;
}

const CATEGORY_META: Record<
  string,
  { label: string; description: string; icon: string; color: string }
> = {
  database: {
    label: "Database",
    description:
      "MCP servers and APIs for SQL, NoSQL, and vector databases. Connect AI agents to PostgreSQL, MySQL, MongoDB, Redis, Supabase, Pinecone, and more.",
    icon: "M4 7v10c0 2 3.6 4 8 4s8-2 8-4V7M4 7c0 2 3.6 4 8 4s8-2 8-4M4 7c0-2 3.6-4 8-4s8 2 8 4M4 12c0 2 3.6 4 8 4s8-2 8-4",
    color: "from-blue-500/20 to-blue-600/5 border-blue-500/20",
  },
  security: {
    label: "Security & Compliance",
    description:
      "Security scanning, vulnerability assessment, and compliance tools for AI agents. Includes secret detection, SAST, and audit logging.",
    icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    color: "from-red-500/20 to-red-600/5 border-red-500/20",
  },
  ai: {
    label: "AI & Machine Learning",
    description:
      "LLM APIs, embedding models, image generation, and ML inference tools. Connect agents to OpenAI, Anthropic, Hugging Face, and specialized AI services.",
    icon: "M12 2a4 4 0 0 0-4 4c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2 4 4 0 0 0-4-4zM9 10H7a5 5 0 0 0-5 5 3 3 0 0 0 3 3h2m8-8h2a5 5 0 0 1 5 5 3 3 0 0 1-3 3h-2M9 18h6",
    color: "from-purple-500/20 to-purple-600/5 border-purple-500/20",
  },
  developer_tools: {
    label: "Developer Tools",
    description:
      "Code execution, version control, CI/CD, and development workflow tools. GitHub, GitLab, Docker, Kubernetes integrations for autonomous coding agents.",
    icon: "M16 18l6-6-6-6M8 6l-6 6 6 6",
    color: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/20",
  },
  communication: {
    label: "Communication",
    description:
      "Slack, Discord, email, and messaging platform integrations. Enable AI agents to send notifications, monitor channels, and automate communication workflows.",
    icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
    color: "from-green-500/20 to-green-600/5 border-green-500/20",
  },
  data: {
    label: "Data & Analytics Pipelines",
    description:
      "ETL pipelines, data transformation, and analytics infrastructure. Connect agents to BigQuery, Snowflake, dbt, Airflow, and data warehouse tools.",
    icon: "M18 20V10M12 20V4M6 20v-6",
    color: "from-amber-500/20 to-amber-600/5 border-amber-500/20",
  },
  productivity: {
    label: "Productivity & Workflow",
    description:
      "Task management, calendar, notes, and productivity tools. Notion, Linear, Jira, Google Workspace integrations for AI workflow automation.",
    icon: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
    color: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20",
  },
  blockchain: {
    label: "Blockchain & Web3",
    description:
      "DeFi protocols, NFT platforms, smart contract interaction, and blockchain data tools. Ethereum, Solana, and multi-chain integrations for Web3 agents.",
    icon: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
    color: "from-indigo-500/20 to-indigo-600/5 border-indigo-500/20",
  },
  payments: {
    label: "Payment & Finance",
    description:
      "Stripe, PayPal, and financial data APIs for AI agents. Process payments, query transaction history, and automate financial workflows.",
    icon: "M2 10h20M2 14h20M6 18h2M12 18h6M4 6h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
    color: "from-yellow-500/20 to-yellow-600/5 border-yellow-500/20",
  },
  mcp: {
    label: "MCP Servers",
    description:
      "Model Context Protocol servers — the standard for connecting AI agents to external tools and data sources. Browse all MCP-native integrations.",
    icon: "M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83",
    color: "from-violet-500/20 to-violet-600/5 border-violet-500/20",
  },
  search: {
    label: "Search & Retrieval",
    description:
      "Web search, semantic search, and document retrieval tools. Exa, Tavily, Brave Search, and RAG infrastructure for knowledge-grounded agents.",
    icon: "M11 17.25a6.25 6.25 0 1 1 0-12.5 6.25 6.25 0 0 1 0 12.5zM16 16l4.5 4.5",
    color: "from-orange-500/20 to-orange-600/5 border-orange-500/20",
  },
  storage: {
    label: "File & Object Storage",
    description:
      "S3, R2, Google Cloud Storage, and file management tools. Give AI agents the ability to read, write, and manage files across storage platforms.",
    icon: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
    color: "from-teal-500/20 to-teal-600/5 border-teal-500/20",
  },
  cms: {
    label: "CMS & Content",
    description:
      "Headless CMS, content management, and publishing platform integrations. WordPress, Contentful, Sanity, and Ghost for content-aware agents.",
    icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
    color: "from-pink-500/20 to-pink-600/5 border-pink-500/20",
  },
  testing: {
    label: "Testing & QA",
    description:
      "Automated testing, browser automation, and QA tools. Playwright, Puppeteer, and test infrastructure for agents that validate software quality.",
    icon: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
    color: "from-lime-500/20 to-lime-600/5 border-lime-500/20",
  },
  monitoring: {
    label: "Monitoring & Observability",
    description:
      "Application monitoring, error tracking, and observability platforms. Datadog, Grafana, Sentry, and alerting tools for autonomous operations agents.",
    icon: "M22 12h-4l-3 9L9 3l-3 9H2",
    color: "from-rose-500/20 to-rose-600/5 border-rose-500/20",
  },
  cloud: {
    label: "Cloud Infrastructure",
    description:
      "AWS, GCP, Azure, and cloud-native tools. Provision resources, manage deployments, and query cloud infrastructure with AI agents.",
    icon: "M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z",
    color: "from-sky-500/20 to-sky-600/5 border-sky-500/20",
  },
  automation: {
    label: "Automation & Integration",
    description:
      "Workflow automation, Zapier alternatives, and integration platforms. n8n, Make, and iPaaS tools for building autonomous multi-step agent workflows.",
    icon: "M12 2v4M6.34 6.34l-2.12-2.12M2 12h4m-.34 5.66l-2.12 2.12M12 18v4m5.66-2.34l2.12 2.12M18 12h4m-2.34-5.66l2.12-2.12",
    color: "from-fuchsia-500/20 to-fuchsia-600/5 border-fuchsia-500/20",
  },
  media: {
    label: "Media & Social",
    description:
      "Social media APIs, video platforms, and media processing tools. Twitter/X, YouTube, Instagram integrations for social-aware AI agents.",
    icon: "M23 7l-7 5 7 5V7zM14 5H3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2z",
    color: "from-red-400/20 to-red-500/5 border-red-400/20",
  },
  analytics: {
    label: "Analytics & BI",
    description:
      "Business intelligence, data visualization, and analytics APIs. Google Analytics, Mixpanel, and BI platform integrations for data-driven agents.",
    icon: "M21 21H4.6c-.56 0-.84 0-1.05-.11a1 1 0 0 1-.44-.44C3 20.24 3 19.96 3 19.4V3m4 14l4-8 4 4 6-10",
    color: "from-amber-400/20 to-amber-500/5 border-amber-400/20",
  },
  ecommerce: {
    label: "E-commerce",
    description:
      "Shopify, WooCommerce, and e-commerce platform integrations. Product catalogs, order management, and inventory tools for commerce agents.",
    icon: "M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4zM3 6h18M16 10a4 4 0 0 1-8 0",
    color: "from-emerald-400/20 to-emerald-500/5 border-emerald-400/20",
  },
  education: {
    label: "Education & Learning",
    description:
      "Learning management, course platforms, and educational content APIs. Tools for AI tutoring agents and knowledge delivery systems.",
    icon: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z",
    color: "from-blue-400/20 to-blue-500/5 border-blue-400/20",
  },
  healthcare: {
    label: "Healthcare",
    description:
      "Medical data, FHIR APIs, and healthcare platform integrations. Clinical decision support and health data tools for medical AI agents.",
    icon: "M22 12h-4l-3 9L9 3l-3 9H2",
    color: "from-green-400/20 to-green-500/5 border-green-400/20",
  },
  design: {
    label: "Design & UI",
    description:
      "Figma, design system, and UI component APIs. Design token access, asset export, and visual design tools for AI-powered design workflows.",
    icon: "M12 19l7-7 3 3-7 7-3-3zM18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5zM2 2l7.586 7.586M11 13a2 2 0 1 1-4 0 2 2 0 0 1 4 0z",
    color: "from-pink-400/20 to-pink-500/5 border-pink-400/20",
  },
  documentation: {
    label: "Documentation",
    description:
      "API documentation, knowledge base, and technical writing tools. Give agents access to docs, wikis, and structured technical content.",
    icon: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
    color: "from-slate-400/20 to-slate-500/5 border-slate-400/20",
  },
  cli: {
    label: "CLI Tools",
    description:
      "Command-line interface tools and terminal utilities. Shell scripts, CLI wrappers, and system tools for agents that operate in terminal environments.",
    icon: "M4 17l6-6-6-6M12 19h8",
    color: "from-gray-400/20 to-gray-500/5 border-gray-400/20",
  },
  skills: {
    label: "Skills & Plugins",
    description:
      "Claude Code skills, AI assistant plugins, and extensible agent capabilities. Custom tools that extend agent functionality in specific domains.",
    icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    color: "from-yellow-400/20 to-yellow-500/5 border-yellow-400/20",
  },
  open_data: {
    label: "Open Data",
    description:
      "Public datasets, government data, and open data APIs. Give AI agents access to census data, scientific datasets, and public information sources.",
    icon: "M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.66 0 3-4.03 3-9s-1.34-9-3-9m0 18c-1.66 0-3-4.03-3-9s1.34-9 3-9",
    color: "from-cyan-400/20 to-cyan-500/5 border-cyan-400/20",
  },
  other: {
    label: "Other",
    description:
      "Miscellaneous AI agent tools, niche integrations, and emerging categories. Discover tools that don't fit standard categories but may be exactly what your agent needs.",
    icon: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
    color: "from-gray-400/20 to-gray-500/5 border-gray-400/20",
  },
};

const CATEGORY_ORDER = [
  "ai",
  "developer_tools",
  "mcp",
  "cli",
  "database",
  "cloud",
  "automation",
  "communication",
  "data",
  "productivity",
  "search",
  "monitoring",
  "testing",
  "security",
  "analytics",
  "storage",
  "cms",
  "design",
  "documentation",
  "payments",
  "blockchain",
  "media",
  "ecommerce",
  "education",
  "healthcare",
  "skills",
  "open_data",
  "other",
];

async function getCategories(): Promise<{
  categories: Category[];
  total: number;
}> {
  try {
    const res = await fetch(
      "https://clarvia-api.onrender.com/v1/categories?source=all",
      {
        next: { revalidate: 3600 },
      }
    );
    if (!res.ok) throw new Error("API error");
    const data = await res.json();
    const categories: Category[] = data.categories || [];
    const total = categories.reduce((s, c) => s + c.count, 0);
    return { categories, total };
  } catch {
    return { categories: [], total: 42809 };
  }
}

function CategoryIcon({ path }: { path: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <path d={path} />
    </svg>
  );
}

export default async function CategoriesPage() {
  const { categories, total } = await getCategories();

  const countMap = Object.fromEntries(categories.map((c) => [c.name, c.count]));

  const orderedCategories = CATEGORY_ORDER.map((slug) => ({
    slug,
    ...(CATEGORY_META[slug] || {
      label: slug,
      description: `${slug} tools for AI agents, ranked by AEO score.`,
      icon: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
      color: "from-gray-500/20 to-gray-600/5 border-gray-500/20",
    }),
    count: countMap[slug] || 0,
  })).filter((c) => c.count > 0);

  const categoryCount = orderedCategories.length;

  // JSON-LD structured data for this page
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "AI Agent Tool Categories — Clarvia",
    description: `Browse ${total.toLocaleString()}+ AI agent tools across ${categoryCount} categories, ranked by AEO (AI Engine Optimization) score.`,
    url: "https://clarvia.art/categories",
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: categoryCount,
      itemListElement: orderedCategories.slice(0, 10).map((cat, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: cat.label,
        description: cat.description,
        url: `https://clarvia.art/categories/${cat.slug}`,
      })),
    },
  };

  return (
    <div className="min-h-screen bg-gradient-mesh">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Navigation */}
      <nav className="border-b border-card-border/50 backdrop-blur-md bg-background/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={30}
              height={30}
              className="transition-transform group-hover:scale-110"
            />
            <span className="text-lg font-semibold tracking-tight">
              Clarvia
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/tools"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Tools
            </Link>
            <Link
              href="/leaderboard"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Leaderboard
            </Link>
            <Link
              href="/guide"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Guide
            </Link>
            <Link
              href="/register"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Register
            </Link>
            <Link
              href="/trending"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Trending
            </Link>
            <Link
              href="/compare"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Compare
            </Link>
            <Link
              href="/docs"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Docs
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 pt-16 pb-12">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
              <span className="text-gradient">AI Agent Tool Categories</span>
            </h1>
            <p className="text-lg text-muted leading-relaxed mb-6">
              Browse {total.toLocaleString()} tools across {categoryCount}{" "}
              categories, ranked by AEO (AI Engine Optimization) score. Find the
              best tools for your AI agent workflows.
            </p>
            <p className="text-sm text-muted/70">
              Every tool is scored 0–100 on agent readiness: API accessibility,
              structured data, MCP compatibility, and trust signals.
            </p>
          </div>
        </div>
      </section>

      {/* Category Grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {orderedCategories.map((cat) => (
            <Link
              key={cat.slug}
              href={`/categories/${cat.slug}`}
              className={`glass-card rounded-xl p-6 bg-gradient-to-br ${cat.color} hover:scale-[1.02] transition-all duration-200 group`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="text-accent opacity-80 group-hover:opacity-100 transition-opacity">
                    <CategoryIcon path={cat.icon} />
                  </div>
                  <h2 className="text-lg font-semibold group-hover:text-accent transition-colors">
                    {cat.label}
                  </h2>
                </div>
                <span className="text-xs font-mono text-muted bg-card-border/30 px-2 py-1 rounded">
                  {cat.count.toLocaleString()}
                </span>
              </div>
              <p className="text-sm text-muted line-clamp-2">
                {cat.description}
              </p>
              <div className="mt-4 flex items-center gap-1 text-xs text-accent opacity-0 group-hover:opacity-100 transition-opacity">
                View tools
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* SEO content block for AI crawlers */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="glass-card rounded-xl p-8 border border-card-border/30">
          <h2 className="text-xl font-semibold mb-4">
            About AI Agent Tool Categories
          </h2>
          <div className="prose prose-sm prose-invert max-w-none text-muted space-y-3">
            <p>
              Clarvia categorizes {total.toLocaleString()} AI agent tools across{" "}
              {categoryCount} functional categories, each ranked by AEO (AI
              Engine Optimization) score. The AEO score measures how easily
              autonomous AI agents can discover and use each tool — covering API
              documentation quality, structured data, MCP compatibility, and
              trust signals.
            </p>
            <p>
              <strong className="text-foreground">
                Developer Tools ({countMap["developer_tools"]?.toLocaleString()}{" "}
                tools)
              </strong>{" "}
              is the largest category, containing GitHub integrations, code
              execution environments, CI/CD pipelines, and IDE plugins.{" "}
              <strong className="text-foreground">
                MCP Servers ({countMap["mcp"]?.toLocaleString()} tools)
              </strong>{" "}
              lists tools built natively on the Model Context Protocol standard.{" "}
              <strong className="text-foreground">
                AI & Machine Learning ({countMap["ai"]?.toLocaleString()} tools)
              </strong>{" "}
              covers LLM APIs, embedding services, and inference platforms.
            </p>
            <p>
              Each category page shows the top tools by AEO score, average score
              for the category, and breakdown by service type (MCP server, API,
              CLI, or skill). Use these rankings to find the most agent-ready
              tool for any integration task.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-card-border/30 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted">
            Clarvia indexes and scores AI agent tools using the AEO standard.
          </p>
          <div className="flex items-center gap-6">
            <Link
              href="/about"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              About
            </Link>
            <Link
              href="/methodology"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Methodology
            </Link>
            <Link
              href="/scan"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Scan Your Tool
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
