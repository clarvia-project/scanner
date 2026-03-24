import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Clarvia AEO Scanner",
  description:
    "Choose the right plan for your AEO needs. Free scans, Pro reports, or Team collaboration.",
};

const TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    description: "Get started with basic AEO insights",
    highlight: false,
    features: [
      { text: "3 scans per month", coming: false },
      { text: "Top 3 recommendations", coming: false },
      { text: "Score badge", coming: false },
      { text: "AEO guide access", coming: false },
    ],
    cta: "Start Scanning",
    ctaHref: "/",
    ctaStyle: "border border-card-border hover:border-accent/40 text-foreground",
  },
  {
    name: "Indie",
    price: "$9",
    period: "/month",
    description: "Solo developers & indie hackers",
    highlight: false,
    features: [
      { text: "50 scans per month", coming: false },
      { text: "Basic monitoring (weekly)", coming: false },
      { text: "AEO badge for README", coming: false },
      { text: "Email support", coming: false },
      { text: "Score history (30 days)", coming: false },
    ],
    cta: "Get Indie",
    ctaHref: "#",
    ctaStyle: "border border-card-border hover:border-accent/40 text-foreground",
  },
  {
    name: "Starter",
    price: "$19",
    period: "/month",
    description: "Essential reports for growing projects",
    highlight: false,
    features: [
      { text: "100 scans per month", coming: false },
      { text: "Full report (evidence unblurred)", coming: false },
      { text: "Scan history (30 days)", coming: false },
      { text: "Email support", coming: false },
      { text: "API access (30 req/hr)", coming: false },
    ],
    cta: "Get Starter",
    ctaHref: "#",
    ctaStyle: "border border-card-border hover:border-accent/40 text-foreground",
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "Full reports and unlimited scanning",
    highlight: true,
    features: [
      { text: "Unlimited scans", coming: false },
      { text: "Full report with all 15 recommendations", coming: false },
      { text: "Competitive benchmarks", coming: false },
      { text: "Code examples (stack-specific)", coming: false },
      { text: "Scan history tracking", coming: false },
      { text: "API access (100 req/hr)", coming: false },
    ],
    cta: "Get Pro",
    ctaHref: "#",
    ctaStyle: "btn-gradient text-white",
  },
  {
    name: "Team",
    price: "$149",
    period: "/month",
    description: "Collaborate with your engineering team",
    highlight: false,
    features: [
      { text: "Everything in Pro", coming: false },
      { text: "5 team seats", coming: false },
      { text: "API access (500 req/hr)", coming: false },
      { text: "Priority support", coming: false },
      { text: "Custom scoring weights", coming: true },
      { text: "CI/CD integration", coming: false },
    ],
    cta: "Contact Us",
    ctaHref: "mailto:hello@clarvia.art",
    ctaStyle: "border border-card-border hover:border-accent/40 text-foreground",
  },
] as const;

export default function PricingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
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
              <Link href="/leaderboard" className="text-sm text-muted hover:text-foreground transition-colors">
                Leaderboard
              </Link>
              <Link href="/guide" className="text-sm text-muted hover:text-foreground transition-colors">
                Guide
              </Link>
              <Link href="/pricing" className="text-sm text-foreground font-medium transition-colors">
                Pricing
              </Link>
              <Link href="/register" className="text-sm text-muted hover:text-foreground transition-colors">
                Register
              </Link>
              <Link href="/docs" className="text-sm text-muted hover:text-foreground transition-colors">
                Docs
              </Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-16">
        {/* Hero */}
        <div className="text-center space-y-4 mb-16">
          <h1 className="text-3xl sm:text-4xl font-bold">
            Simple, transparent pricing
          </h1>
          <p className="text-muted text-sm max-w-lg mx-auto">
            Start scanning for free. Upgrade when you need full reports,
            competitive benchmarks, and team collaboration.
          </p>
        </div>

        {/* Tiers */}
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 items-start">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`glass-card rounded-2xl p-6 sm:p-8 flex flex-col relative transition-all duration-300 ${
                tier.highlight
                  ? "border-accent/40 shadow-[0_0_30px_-8px_rgba(99,102,241,0.15)]"
                  : ""
              }`}
            >
              {tier.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-white text-xs font-medium px-3 py-1 rounded-full">
                  Recommended
                </span>
              )}

              {/* Plan name + price */}
              <div className="mb-6">
                <h2 className="text-lg font-semibold mb-1">{tier.name}</h2>
                <p className="text-xs text-muted mb-4">{tier.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold font-mono">{tier.price}</span>
                  {tier.period && (
                    <span className="text-sm text-muted">{tier.period}</span>
                  )}
                </div>
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li key={feature.text} className="flex items-start gap-3 text-sm">
                    <svg
                      className={`w-4 h-4 shrink-0 mt-0.5 ${
                        feature.coming ? "text-muted/60" : "text-score-green"
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    <span className={feature.coming ? "text-muted/60" : ""}>
                      {feature.text}
                      {feature.coming && (
                        <span className="ml-2 text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-card-border/40 text-muted/60">
                          Coming soon
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              {tier.ctaHref.startsWith("mailto:") ? (
                <a
                  href={tier.ctaHref}
                  className={`block w-full px-5 py-3 rounded-xl text-sm font-medium text-center transition-all ${tier.ctaStyle}`}
                >
                  {tier.cta}
                </a>
              ) : (
                <Link
                  href={tier.ctaHref}
                  className={`block w-full px-5 py-3 rounded-xl text-sm font-medium text-center transition-all ${tier.ctaStyle}`}
                >
                  {tier.cta}
                </Link>
              )}
            </div>
          ))}
        </div>

        {/* FAQ / Note */}
        <div className="text-center mt-16 space-y-2">
          <p className="text-xs text-muted/60">
            All plans include HTTPS-only scanning. No credit card required for Free tier.
          </p>
          <p className="text-xs text-muted/60">
            Questions? Reach us at{" "}
            <a href="mailto:hello@clarvia.art" className="text-accent hover:underline">
              hello@clarvia.art
            </a>
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border/50 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <div className="flex items-center gap-3">
            <Image
              src="/logos/clarvia-icon.svg"
              alt="Clarvia"
              width={24}
              height={24}
              className="rounded-full"
            />
            <span>Clarvia — Discovery & Trust standard for the agent economy</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
            <a href="https://github.com/clarvia-project" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <a href="https://x.com/clarvia_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">@clarvia_ai</a>
            <Link href="/about" className="hover:text-foreground transition-colors">About</Link>
            <Link href="#" className="hover:text-foreground transition-colors" title="Coming soon">Terms</Link>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
