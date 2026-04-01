import Link from "next/link";
import Image from "next/image";
import { Metadata } from "next";
import CategoryClient, { CategoryData } from "./CategoryClient";
import Nav from "@/app/components/Nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// ---------------------------------------------------------------------------
// Category metadata (static, used when API is unavailable)
// ---------------------------------------------------------------------------

const CATEGORY_META: Record<
  string,
  { label: string; description: string }
> = {
  database: {
    label: "Database",
    description:
      "MCP servers and APIs for SQL, NoSQL, and vector databases. Connect AI agents to PostgreSQL, MySQL, MongoDB, Redis, Supabase, Pinecone, and more.",
  },
  security: {
    label: "Security & Compliance",
    description:
      "Security scanning, vulnerability assessment, and compliance tools for AI agents. Includes secret detection, SAST, and audit logging.",
  },
  ai: {
    label: "AI & Machine Learning",
    description:
      "LLM APIs, embedding models, image generation, and ML inference tools. Connect agents to OpenAI, Anthropic, Hugging Face, and specialized AI services.",
  },
  developer_tools: {
    label: "Developer Tools",
    description:
      "Code execution, version control, CI/CD, and development workflow tools. GitHub, GitLab, Docker, Kubernetes integrations for autonomous coding agents.",
  },
  communication: {
    label: "Communication",
    description:
      "Slack, Discord, email, and messaging platform integrations. Enable AI agents to send notifications, monitor channels, and automate communication workflows.",
  },
  data: {
    label: "Data & Analytics",
    description:
      "Data pipeline, analytics, and visualization tools for AI agents. Integrate with dbt, Airflow, Metabase, and more.",
  },
  cloud: {
    label: "Cloud & Infrastructure",
    description:
      "AWS, GCP, Azure, and cloud-native infrastructure tools. Manage deployments, serverless functions, and cloud resources via AI agents.",
  },
  productivity: {
    label: "Productivity",
    description:
      "Task management, calendar, note-taking, and workflow tools. Connect AI agents to Notion, Linear, Jira, Google Workspace, and more.",
  },
  search: {
    label: "Search",
    description:
      "Web search, semantic search, and RAG pipeline tools. Enable agents to browse the web, query knowledge bases, and retrieve context.",
  },
  monitoring: {
    label: "Monitoring & Observability",
    description:
      "Error tracking, performance monitoring, and logging tools. Datadog, Sentry, Grafana integrations for agent-driven ops workflows.",
  },
  testing: {
    label: "Testing & QA",
    description:
      "Automated testing, browser automation, and QA tools for AI agents. Playwright, Selenium, and test framework integrations.",
  },
  payments: {
    label: "Payments & Finance",
    description:
      "Payment processing, billing, and financial data APIs. Stripe, PayPal, and fintech integrations for autonomous agent workflows.",
  },
  automation: {
    label: "Automation & Workflow",
    description:
      "Workflow automation, RPA, and business process tools. n8n, Zapier, and Make.com integrations for agentic automation.",
  },
  storage: {
    label: "Storage & Files",
    description:
      "Object storage, file systems, and document management tools. S3, GCS, and cloud storage integrations for AI agents.",
  },
  analytics: {
    label: "Analytics",
    description:
      "Product analytics, business intelligence, and reporting tools. Mixpanel, Amplitude, and analytics platform integrations.",
  },
  cms: {
    label: "CMS & Content",
    description:
      "Content management, headless CMS, and publishing tools. WordPress, Contentful, and Sanity integrations for content agents.",
  },
  design: {
    label: "Design & Creative",
    description:
      "Design tools, image editing, and creative AI services. Figma, Canva, and image generation integrations for creative agents.",
  },
  documentation: {
    label: "Documentation",
    description:
      "API documentation, knowledge base, and technical writing tools. Integrate AI agents with Confluence, GitBook, and Notion.",
  },
  blockchain: {
    label: "Blockchain & Web3",
    description:
      "Smart contracts, DeFi protocols, and blockchain data tools. Ethereum, Solana, and Web3 integrations for autonomous agents.",
  },
  media: {
    label: "Media & Entertainment",
    description:
      "Audio, video, and media processing tools. Spotify, YouTube, and media platform integrations for AI agents.",
  },
};

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchCategoryData(slug: string): Promise<CategoryData | null> {
  try {
    const res = await fetch(
      `${API_BASE}/v1/categories/${slug}?source=all&limit=50`,
      { next: { revalidate: 3600 } }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Metadata generation (SSR)
// ---------------------------------------------------------------------------

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const data = await fetchCategoryData(slug);
  const meta = CATEGORY_META[slug];
  const label = data?.label || meta?.label || slug.replace(/_/g, " ");
  const total = data?.total ?? 0;
  const avgScore = data?.avg_score ?? 0;

  const title = `Best ${label} MCP Servers & AI Tools — Ranked by AEO Score | Clarvia`;
  const description = total
    ? `Compare ${total.toLocaleString()} ${label.toLowerCase()} tools ranked by AEO score. Average score: ${avgScore}/100. Find the best ${label.toLowerCase()} tools for AI agents.`
    : (meta?.description ?? `Browse ${label} tools for AI agents on Clarvia.`);

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `https://clarvia.art/categories/${slug}`,
      siteName: "Clarvia",
      type: "website",
    },
    alternates: {
      canonical: `https://clarvia.art/categories/${slug}`,
    },
  };
}

// ---------------------------------------------------------------------------
// FAQ generation
// ---------------------------------------------------------------------------

function generateFAQs(
  label: string,
  total: number,
  avgScore: number
): { question: string; answer: string }[] {
  return [
    {
      question: `What are the best ${label} tools for AI agents?`,
      answer: `Clarvia indexes and ranks ${total.toLocaleString()} ${label.toLowerCase()} tools by AEO (AI Engine Optimization) score. The AEO score measures how easily AI agents can discover and use each tool, considering API accessibility, data structuring, agent compatibility, and trust signals. Browse the ranked list above to find the best options.`,
    },
    {
      question: `What is the AEO score for ${label} tools?`,
      answer: `The average AEO score across ${label.toLowerCase()} tools is ${avgScore.toFixed(1)} out of 100. AEO scores measure agent-readiness across four dimensions: API Accessibility, Data Structuring, Agent Compatibility, and Trust Signals. Higher scores indicate tools that AI agents can more easily discover and integrate with.`,
    },
    {
      question: `How are ${label} tools ranked on Clarvia?`,
      answer: `Tools are ranked by their Clarvia AEO Score, which is computed by scanning each tool's API surface, documentation, error handling, and protocol support. The score is broken down into four weighted dimensions. Tools with higher scores appear first, making it easy to find the most agent-friendly options.`,
    },
    {
      question: `Can AI agents automatically use these ${label} tools?`,
      answer: `Tools with high AEO scores (70+) are generally well-suited for AI agent integration. Many listed tools support the Model Context Protocol (MCP), have structured API documentation, and provide clear error handling — all factors that make autonomous agent usage reliable.`,
    },
  ];
}

// ---------------------------------------------------------------------------
// JSON-LD structured data (SSR — visible to AI crawlers)
// ---------------------------------------------------------------------------

function CategoryJsonLd({
  data,
  slug,
  faqs,
}: {
  data: CategoryData;
  slug: string;
  faqs: { question: string; answer: string }[];
}) {
  const collectionLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `Best ${data.label} Tools for AI Agents`,
    description: data.description,
    url: `https://clarvia.art/categories/${slug}`,
    numberOfItems: data.total,
    provider: {
      "@type": "Organization",
      name: "Clarvia",
      url: "https://clarvia.art",
    },
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: Math.min(data.tools.length, 10),
      itemListElement: data.tools.slice(0, 10).map((tool, i) => ({
        "@type": "ListItem",
        position: i + 1,
        item: {
          "@type": "SoftwareApplication",
          name: tool.name,
          url: tool.url,
          applicationCategory: data.label,
          description:
            tool.description ||
            `${tool.name} — AEO Score: ${tool.clarvia_score}/100`,
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: tool.clarvia_score,
            bestRating: 100,
            worstRating: 0,
            ratingCount: 1,
          },
        },
      })),
    },
  };

  const faqLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(collectionLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqLd) }}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Score color helper
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

// ---------------------------------------------------------------------------
// Page (Server Component)
// ---------------------------------------------------------------------------

export default async function CategoryDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const data = await fetchCategoryData(slug);

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-mesh flex items-center justify-center">
        <div className="glass-card rounded-2xl p-12 text-center max-w-md">
          <h1 className="text-2xl font-bold mb-4">Category Not Found</h1>
          <p className="text-muted mb-6">
            The category &ldquo;{slug}&rdquo; does not exist or could not be
            loaded.
          </p>
          <Link
            href="/categories"
            className="btn-gradient px-6 py-3 rounded-lg text-sm font-medium inline-block"
          >
            Browse All Categories
          </Link>
        </div>
      </div>
    );
  }

  const faqs = generateFAQs(data.label, data.total, data.avg_score);

  return (
    <div className="min-h-screen bg-gradient-mesh">
      {/* JSON-LD structured data — server-rendered for AI crawlers */}
      <CategoryJsonLd data={data} slug={slug} faqs={faqs} />

      <Nav />

      {/* Breadcrumbs */}
      <div className="max-w-7xl mx-auto px-6 pt-6">
        <nav className="text-sm text-muted flex items-center gap-2">
          <Link href="/" className="hover:text-foreground transition-colors">
            Home
          </Link>
          <span>/</span>
          <Link
            href="/categories"
            className="hover:text-foreground transition-colors"
          >
            Categories
          </Link>
          <span>/</span>
          <span className="text-foreground">{data.label}</span>
        </nav>
      </div>

      {/* Hero Section — fully server-rendered */}
      <section className="max-w-7xl mx-auto px-6 pt-8 pb-6">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
          Best {data.label} MCP Servers &amp; AI Tools{" "}
          <span className="text-muted font-normal text-lg sm:text-xl">
            — Ranked by AEO Score
          </span>
        </h1>
        <p className="text-muted text-lg leading-relaxed mb-8 max-w-3xl">
          {data.description}
        </p>

        {/* Stats */}
        <div className="flex flex-wrap gap-4 mb-8">
          <div className="glass-card rounded-xl px-5 py-3">
            <div className="text-2xl font-bold text-accent">
              {data.total.toLocaleString()}
            </div>
            <div className="text-xs text-muted">Total Tools</div>
          </div>
          <div className="glass-card rounded-xl px-5 py-3">
            <div
              className={`text-2xl font-bold ${scoreColor(data.avg_score)}`}
            >
              {data.avg_score}
            </div>
            <div className="text-xs text-muted">Avg AEO Score</div>
          </div>
          <div className="glass-card rounded-xl px-5 py-3">
            <div className="text-2xl font-bold text-score-green">
              {data.max_score}
            </div>
            <div className="text-xs text-muted">Top Score</div>
          </div>
        </div>

        {/* Top 10 tools — server-rendered for crawlers */}
        <div className="space-y-2 mb-4">
          <p className="text-xs text-muted font-mono mb-3">
            Top {Math.min(data.tools.length, 10)} tools by AEO score:
          </p>
          {data.tools.slice(0, 10).map((tool, i) => (
            <Link
              key={tool.scan_id}
              href={`/tool/${tool.scan_id}`}
              className="glass-card rounded-xl p-3 flex items-center gap-3 hover:border-accent/30 transition-all"
            >
              <span className="text-xs font-mono text-muted/60 w-6 text-center flex-shrink-0">
                #{i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <span className="font-semibold text-sm">{tool.name}</span>
                {tool.description && (
                  <p className="text-xs text-muted truncate">
                    {tool.description}
                  </p>
                )}
              </div>
              <div
                className={`text-lg font-bold font-mono flex-shrink-0 ${scoreColor(tool.clarvia_score)}`}
              >
                {tool.clarvia_score}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Interactive section (client component handles filtering + pagination) */}
      <CategoryClient initialData={data} slug={slug} faqs={faqs} />
    </div>
  );
}
