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

export default function CompareLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
