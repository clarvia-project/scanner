import type { Metadata } from "next";
import { API_BASE } from "@/lib/api";
const SITE_URL = "https://clarvia.art";

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: LayoutProps): Promise<Metadata> {
  const { id } = await params;

  // Try to fetch scan data for dynamic meta
  let title = "Scan Result — Clarvia AEO Scanner";
  let description = "See how this service scores on AI agent readiness.";
  let serviceName = "";
  let score: number | null = null;

  try {
    const res = await fetch(`${API_BASE}/api/scan/${id}`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      serviceName = data.service_name || "";
      score = data.clarvia_score;
    }
  } catch {
    // Fallback: try prebuilt scans
    try {
      const fallback = await fetch(`${SITE_URL}/data/prebuilt-scans.json`);
      if (fallback.ok) {
        const scans = await fallback.json();
        const match = scans.find((s: { scan_id: string }) => s.scan_id === id);
        if (match) {
          serviceName = match.service_name || "";
          score = match.clarvia_score;
        }
      }
    } catch {
      // silent fallback
    }
  }

  if (serviceName && score !== null) {
    title = `${serviceName} scored ${score}/100 — Clarvia AEO Scanner`;
    description = `${serviceName} has a Clarvia Score of ${score}/100 for AI agent readiness. See the full breakdown.`;
  }

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: `${SITE_URL}/scan/${id}`,
      siteName: "Clarvia",
      type: "website",
    },
    twitter: {
      card: "summary",
      title,
      description,
    },
  };
}

export default function ScanLayout({ children }: { children: React.ReactNode }) {
  return children;
}
