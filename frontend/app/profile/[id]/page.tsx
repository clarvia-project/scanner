import { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import ProfileClient from "./ProfileClient";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

interface ProfileData {
  id: string;
  name: string;
  url: string;
  description: string;
  category: string;
  github_url?: string;
  tags?: string[];
  contact_email?: string;
  clarvia_score?: number;
  rating?: string;
  scan_id?: string;
  dimensions?: {
    api_accessibility: { score: number; max: number };
    data_structuring: { score: number; max: number };
    agent_compatibility: { score: number; max: number };
    trust_signals: { score: number; max: number };
  };
  created_at?: string;
}

async function fetchProfile(id: string): Promise<ProfileData | null> {
  try {
    const res = await fetch(`${API_BASE}/v1/profiles/${encodeURIComponent(id)}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const profile = await fetchProfile(id);

  if (!profile) {
    return {
      title: "Profile Not Found | Clarvia",
      description: "This tool profile could not be found on Clarvia.",
    };
  }

  const score = profile.clarvia_score;
  const rating = profile.rating ?? "Unrated";
  const title = `${profile.name} — AEO Score: ${score ?? "Unscored"} | Clarvia`;
  const description =
    score != null
      ? `${profile.name} scores ${score}/100 on Clarvia's AEO scale (${rating}). ${profile.description || "Clarvia measures how easily AI agents can discover and use this tool."}`
      : `${profile.name} on Clarvia — ${profile.description || "Check this tool's AI Engine Optimization readiness score."}`;

  return {
    title,
    description: description.slice(0, 160),
    openGraph: {
      title,
      description: description.slice(0, 200),
      url: `https://clarvia.art/profile/${id}`,
      type: "website",
    },
    twitter: {
      card: "summary",
      title,
      description: description.slice(0, 160),
    },
    alternates: {
      canonical: `https://clarvia.art/profile/${id}`,
    },
  };
}

function buildJsonLd(profile: ProfileData, profileId: string) {
  const score = profile.clarvia_score;
  const profileUrl = `https://clarvia.art/profile/${profileId}`;

  const softwareApp = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: profile.name,
    url: profileUrl,
    description: profile.description || `${profile.name} — AI agent tool indexed by Clarvia`,
    applicationCategory: profile.category === "mcp" ? "DeveloperApplication" : "WebApplication",
    ...(profile.url && { sameAs: profile.url }),
    ...(profile.github_url && {
      codeRepository: profile.github_url,
    }),
    ...(profile.tags?.length && { keywords: profile.tags.join(", ") }),
    ...(score != null && {
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: score,
        bestRating: 100,
        worstRating: 0,
        reviewCount: 1,
        ratingCount: 1,
      },
    }),
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    provider: {
      "@type": "Organization",
      name: "Clarvia",
      url: "https://clarvia.art",
    },
  };

  const faqItems = [
    {
      "@type": "Question",
      name: `What is the AEO score for ${profile.name}?`,
      acceptedAnswer: {
        "@type": "Answer",
        text:
          score != null
            ? `${profile.name} has an AEO (AI Engine Optimization) score of ${score}/100, rated as "${profile.rating ?? "Scored"}". This score measures how easily AI agents can discover, integrate, and use this tool.`
            : `${profile.name} has not yet been scored on Clarvia's AEO scale. Run a scan at clarvia.art to measure its agent readiness.`,
      },
    },
    {
      "@type": "Question",
      name: `What does ${profile.name} do?`,
      acceptedAnswer: {
        "@type": "Answer",
        text: profile.description || `${profile.name} is a tool indexed by Clarvia for AI agent compatibility assessment.`,
      },
    },
  ];

  if (score != null) {
    faqItems.push({
      "@type": "Question",
      name: `How agent-ready is ${profile.name}?`,
      acceptedAnswer: {
        "@type": "Answer",
        text: `Based on Clarvia's 4-dimension scoring (API Accessibility, Data Structuring, Agent Compatibility, Trust Signals), ${profile.name} scores ${score}/100. ${score >= 70 ? "This is a high-quality, agent-ready tool." : score >= 40 ? "This tool has moderate agent compatibility with room for improvement." : "This tool has limited agent compatibility and may need improvements for autonomous agent use."}`,
      },
    });
  }

  const faqPage = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems,
  };

  return [softwareApp, faqPage];
}

export default async function ProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const profile = await fetchProfile(id);

  const jsonLdBlocks = profile ? buildJsonLd(profile, id) : [];

  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
      {/* SSR JSON-LD structured data */}
      {jsonLdBlocks.map((block, i) => (
        <script
          key={i}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(block) }}
        />
      ))}

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-card-border/50 backdrop-blur-xl bg-background/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <Image
                src="/logos/clarvia-icon.svg"
                alt="Clarvia"
                width={32}
                height={32}
                className="rounded-full group-hover:scale-110 transition-transform duration-200"
              />
              <span className="font-semibold text-base tracking-tight text-foreground">
                clarvia
              </span>
            </Link>
            <nav className="hidden sm:flex items-center gap-6">
              <Link href="/tools" className="text-sm text-muted hover:text-foreground transition-colors">Tools</Link>
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/guide" className="text-sm text-muted hover:text-foreground transition-colors">Guide</Link>
              <Link href="/register" className="text-sm text-muted hover:text-foreground transition-colors">Register</Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">Docs</Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {!profile ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-score-red/10 flex items-center justify-center mb-2">
              <svg className="w-8 h-8 text-score-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-score-red font-mono text-sm">Profile not found</p>
            <Link href="/" className="text-accent hover:text-accent-hover text-sm transition-colors">
              Back to home
            </Link>
          </div>
        ) : (
          <ProfileClient initialProfile={profile} profileId={id} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <Image src="/logos/clarvia-icon.svg" alt="Clarvia" width={24} height={24} className="rounded-full" />
            <span>Clarvia — Discovery & Trust standard for the agent economy</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <a href="https://github.com/clarvia-project" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <a href="https://x.com/clarvia_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">@clarvia_ai</a>
            <Link href="/about" className="hover:text-foreground transition-colors">About</Link>
            <span className="text-muted/50 cursor-default" title="Coming soon">Terms</span>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
