import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Clarvia",
  description:
    "Clarvia pricing plans. Free scanning, tool search, and AEO badges. Pro and Enterprise tiers for high-volume API access and CI/CD integration.",
  openGraph: {
    title: "Clarvia Pricing",
    description:
      "Free AEO scanning and tool discovery. Pro plans for teams and CI/CD.",
    url: "https://clarvia.art/pricing",
  },
  alternates: {
    canonical: "https://clarvia.art/pricing",
  },
};

export default function PricingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
