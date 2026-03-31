import type { Metadata } from "next";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ ids?: string }>;
}): Promise<Metadata> {
  const params = await searchParams;
  const ids = params?.ids || "";

  const ogUrl = ids
    ? `/api/og?type=compare&ids=${encodeURIComponent(ids)}`
    : "/og-image.png";

  return {
    title: "Compare Tools — Clarvia AEO Scanner",
    description:
      "Side-by-side AEO score comparison of agent tools. Compare MCP servers, APIs, CLIs, and Skills.",
    openGraph: {
      title: "Tool Comparison — Clarvia",
      description: "Compare AEO scores side by side",
      images: [{ url: ogUrl, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Tool Comparison — Clarvia",
      images: [ogUrl],
    },
  };
}

const compareJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Clarvia Tool Comparison",
  description:
    "Side-by-side AEO score comparison for AI agent tools — MCP servers, APIs, CLIs, and Skills. Compare discoverability, documentation quality, error handling, and agent compatibility scores.",
  url: "https://clarvia.art/compare",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  creator: { "@type": "Organization", name: "Clarvia", url: "https://clarvia.art" },
};

const compareFaqLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "How do I compare MCP servers on Clarvia?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Search for any two MCP servers on Clarvia and click Compare. The side-by-side view shows AEO score, dimension breakdown, and which tool is better suited for AI agent integration.",
      },
    },
    {
      "@type": "Question",
      name: "What does the AEO comparison score measure?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Clarvia compares tools across four AEO dimensions: API Accessibility (openapi spec, auth clarity), Data Structuring (output format, schema), Agent Compatibility (MCP support, tool calling), and Trust Signals (versioning, security, uptime). Total score is 0–100.",
      },
    },
  ],
};

export default function CompareLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(compareJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(compareFaqLd) }}
      />
      {children}
    </>
  );
}
