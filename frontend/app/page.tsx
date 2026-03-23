"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TopScore {
  name: string;
  url: string;
  score: number;
  rating: string;
  scan_id: string;
}

const FALLBACK_SCORES: TopScore[] = [
  { name: "Replicate", url: "replicate.com", score: 80, rating: "Strong", scan_id: "" },
  { name: "Helius", url: "helius.dev", score: 72, rating: "Moderate", scan_id: "" },
  { name: "Hugging Face", url: "huggingface.co", score: 70, rating: "Moderate", scan_id: "" },
  { name: "Resend", url: "resend.com", score: 65, rating: "Moderate", scan_id: "" },
  { name: "Google AI", url: "ai.google.dev", score: 64, rating: "Moderate", scan_id: "" },
];

const SCAN_PHASES = [
  "Discovering endpoints...",
  "Checking MCP registries...",
  "Analyzing API documentation...",
  "Probing error structures...",
  "Testing agent compatibility...",
  "Evaluating trust signals...",
  "Calculating Clarvia Score...",
];

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreBorderColor(score: number) {
  if (score >= 70) return "border-score-green/30";
  if (score >= 40) return "border-score-yellow/30";
  return "border-score-red/30";
}

function ScanningOverlay({ url }: { url: string }) {
  const [phase, setPhase] = useState(0);

  if (typeof window !== "undefined") {
    setTimeout(() => {
      if (phase < SCAN_PHASES.length - 1) {
        setPhase((p) => Math.min(p + 1, SCAN_PHASES.length - 1));
      }
    }, 1800);
  }

  const progress = ((phase + 1) / SCAN_PHASES.length) * 100;

  return (
    <div className="fixed inset-0 bg-background/95 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="w-full max-w-md px-6 space-y-6">
        <div className="text-center space-y-2">
          <p className="text-sm text-muted font-mono">Scanning</p>
          <p className="text-lg font-medium truncate">{url}</p>
        </div>

        <div className="h-1.5 bg-card-border rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="space-y-1.5">
          {SCAN_PHASES.map((label, i) => (
            <p
              key={i}
              className={`text-xs font-mono transition-all duration-300 ${
                i === phase
                  ? "text-foreground"
                  : i < phase
                    ? "text-score-green/60"
                    : "text-muted/20"
              }`}
            >
              {i < phase ? "[done]" : i === phase ? "[....]" : "[    ]"} {label}
            </p>
          ))}
        </div>

        <div className="flex justify-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    </div>
  );
}

/* ── Step icons for "How it works" ── */
function IconUrl() {
  return (
    <svg className="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 010 5.656l-2.828 2.828a4 4 0 01-5.657-5.656l1.415-1.415M10.172 13.828a4 4 0 010-5.656l2.828-2.828a4 4 0 015.657 5.656l-1.415 1.415" />
    </svg>
  );
}
function IconScore() {
  return (
    <svg className="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
    </svg>
  );
}
function IconRocket() {
  return (
    <svg className="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.84 2.58m0 0a6 6 0 01-7.38-5.84h4.8" />
    </svg>
  );
}

/* ── Dimension icons for "What we measure" ── */
function IconApi() {
  return (
    <svg className="w-6 h-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 18.364a9 9 0 1012.728 0M12 2v4m0 12v2" />
    </svg>
  );
}
function IconData() {
  return (
    <svg className="w-6 h-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  );
}
function IconAgent() {
  return (
    <svg className="w-6 h-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 14.5M14.25 3.104c.251.023.501.05.75.082M19.8 14.5l-2.234 2.234a2.25 2.25 0 01-1.591.659H8.025a2.25 2.25 0 01-1.591-.659L4.2 14.5m15.6 0l.4.4a2.25 2.25 0 010 3.182l-.9.9a2.25 2.25 0 01-3.182 0l-.4-.4m-7.518 0l-.4.4a2.25 2.25 0 000 3.182l.9.9a2.25 2.25 0 003.182 0l.4-.4" />
    </svg>
  );
}
function IconTrust() {
  return (
    <svg className="w-6 h-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

export default function LandingPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [scanningUrl, setScanningUrl] = useState("");
  const [error, setError] = useState("");
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistStatus, setWaitlistStatus] = useState<
    "idle" | "sending" | "done" | "error"
  >("idle");
  const [topScores, setTopScores] = useState<TopScore[]>(FALLBACK_SCORES);
  const router = useRouter();

  useEffect(() => {
    fetch("/data/prebuilt-scans.json")
      .then((res) => res.json())
      .then((json: { service_name: string; url: string; clarvia_score: number; rating: string; scan_id: string }[]) => {
        const sorted = [...json]
          .sort((a, b) => b.clarvia_score - a.clarvia_score)
          .slice(0, 5)
          .map((s) => ({
            name: s.service_name,
            url: s.url.replace(/^https?:\/\//, ""),
            score: s.clarvia_score,
            rating: s.rating,
            scan_id: s.scan_id,
          }));
        setTopScores(sorted);
      })
      .catch(() => {});
  }, []);

  async function handleScan(targetUrl?: string) {
    const scanUrl = targetUrl || url.trim();
    if (!scanUrl) return;

    setLoading(true);
    setScanningUrl(scanUrl);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: scanUrl }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Scan failed (${res.status})`);
      }

      const data = await res.json();
      router.push(`/scan/${data.scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
      setLoading(false);
      setScanningUrl("");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    handleScan();
  }

  async function handleWaitlist(e: React.FormEvent) {
    e.preventDefault();
    if (!waitlistEmail.trim()) return;

    setWaitlistStatus("sending");
    try {
      const res = await fetch(`${API_BASE}/api/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: waitlistEmail.trim() }),
      });
      if (res.ok) {
        setWaitlistStatus("done");
        setWaitlistEmail("");
      } else {
        setWaitlistStatus("error");
      }
    } catch {
      setWaitlistStatus("error");
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      {loading && <ScanningOverlay url={scanningUrl} />}

      {/* Header */}
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-mono text-sm tracking-widest text-muted uppercase">
              Clarvia
            </span>
            <Link
              href="/leaderboard"
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              Leaderboard
            </Link>
            <Link
              href="/register"
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              Register
            </Link>
          </div>
          <span className="text-xs text-muted">AEO Scanner v1.0</span>
        </div>
      </header>

      <main className="flex-1">
        {/* ─── Hero ─── */}
        <section className="flex flex-col items-center px-6 pt-24 pb-16">
          <div className="max-w-2xl w-full text-center space-y-6">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
              Is your service ready
              <br />
              for AI agents?
            </h1>
            <p className="text-lg text-muted max-w-xl mx-auto leading-relaxed">
              SEO made you visible to search engines.
              <br className="hidden sm:block" />
              We make you visible to AI agents.
            </p>

            {/* URL Input */}
            <form onSubmit={handleSubmit} className="flex gap-3 max-w-lg mx-auto pt-2">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter a URL (e.g. stripe.com)"
                className="flex-1 bg-card-bg border border-card-border rounded-lg px-4 py-3 text-foreground placeholder:text-muted/50 focus:outline-none focus:border-accent transition-colors font-mono text-sm"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors text-sm whitespace-nowrap"
              >
                Scan
              </button>
            </form>

            {error && (
              <p className="text-score-red text-sm font-mono">{error}</p>
            )}

            <p className="text-xs text-muted">
              Get your Clarvia Score — the AEO standard for agent discoverability and trust.
            </p>
          </div>
        </section>

        {/* ─── How It Works ─── */}
        <section className="px-6 py-20 border-t border-card-border">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-12">How it works</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  icon: <IconUrl />,
                  step: "1",
                  title: "Enter your URL",
                  desc: "Paste any website or API endpoint to start the analysis.",
                },
                {
                  icon: <IconScore />,
                  step: "2",
                  title: "Get your AEO Score",
                  desc: "We probe your service across 4 dimensions agents care about.",
                },
                {
                  icon: <IconRocket />,
                  step: "3",
                  title: "Improve & get discovered",
                  desc: "Follow actionable recommendations and climb the leaderboard.",
                },
              ].map((item) => (
                <div key={item.step} className="text-center space-y-3">
                  <div className="flex justify-center">
                    <div className="w-14 h-14 rounded-full bg-accent/10 flex items-center justify-center">
                      {item.icon}
                    </div>
                  </div>
                  <div className="text-xs font-mono text-accent">Step {item.step}</div>
                  <h3 className="text-lg font-semibold">{item.title}</h3>
                  <p className="text-sm text-muted leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── What We Measure ─── */}
        <section className="px-6 py-20 border-t border-card-border">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-4">What we measure</h2>
            <p className="text-sm text-muted text-center mb-12 max-w-lg mx-auto">
              Every service is evaluated across four dimensions that determine how well AI agents can discover, understand, and trust it.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {[
                {
                  icon: <IconApi />,
                  title: "API Accessibility",
                  desc: "Can agents reach your service?",
                  detail: "Endpoint availability, response speed, authentication documentation.",
                },
                {
                  icon: <IconData />,
                  title: "Data Structuring",
                  desc: "Can agents understand your responses?",
                  detail: "OpenAPI specs, JSON-LD, schema.org markup, structured error responses.",
                },
                {
                  icon: <IconAgent />,
                  title: "Agent Compatibility",
                  desc: "Are you listed where agents look?",
                  detail: "MCP registry presence, plugin manifests, tool descriptions.",
                },
                {
                  icon: <IconTrust />,
                  title: "Trust Signals",
                  desc: "Can agents trust your reliability?",
                  detail: "Uptime signals, HTTPS, security headers, rate limit documentation.",
                },
              ].map((dim) => (
                <div
                  key={dim.title}
                  className="bg-card-bg border border-card-border rounded-xl p-6 space-y-3 hover:border-accent/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {dim.icon}
                    <h3 className="font-semibold">{dim.title}</h3>
                  </div>
                  <p className="text-sm text-accent font-medium">{dim.desc}</p>
                  <p className="text-xs text-muted leading-relaxed">{dim.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── Leaderboard Preview ─── */}
        <section className="px-6 py-20 border-t border-card-border">
          <div className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-4">Leaderboard</h2>
            <p className="text-sm text-muted text-center mb-8">
              Services ranked by agent-readiness. Where does yours stand?
            </p>
            <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
              <div className="grid grid-cols-[auto_1fr_auto_auto] gap-4 px-5 py-3 border-b border-card-border text-xs text-muted font-mono uppercase">
                <span>#</span>
                <span>Service</span>
                <span>Score</span>
                <span>Rating</span>
              </div>
              {topScores.map((item, i) => (
                <button
                  key={item.name}
                  onClick={() =>
                    item.scan_id
                      ? router.push(`/scan/${item.scan_id}`)
                      : handleScan(item.url)
                  }
                  disabled={loading}
                  className="w-full grid grid-cols-[auto_1fr_auto_auto] gap-4 px-5 py-3.5 text-left hover:bg-card-border/30 transition-colors disabled:opacity-50 border-b border-card-border/50 last:border-b-0"
                >
                  <span className="text-sm text-muted font-mono w-6">{i + 1}</span>
                  <span className="text-sm font-medium truncate">{item.name}</span>
                  <span className={`text-sm font-mono font-bold ${scoreColor(item.score)}`}>
                    {item.score}
                  </span>
                  <span className="text-xs text-muted">{item.rating}</span>
                </button>
              ))}
            </div>
            <div className="text-center mt-6">
              <Link
                href="/leaderboard"
                className="text-sm text-accent hover:text-accent-hover transition-colors font-medium"
              >
                View full leaderboard &rarr;
              </Link>
            </div>
          </div>
        </section>

        {/* ─── For Developers CTA ─── */}
        <section className="px-6 py-20 border-t border-card-border">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <h2 className="text-2xl font-bold">For Developers</h2>
            <div className="flex flex-wrap justify-center gap-3 text-sm text-muted">
              <span className="bg-card-bg border border-card-border rounded-lg px-4 py-2">Register your MCP server or API</span>
              <span className="text-accent">&rarr;</span>
              <span className="bg-card-bg border border-card-border rounded-lg px-4 py-2">Get scored</span>
              <span className="text-accent">&rarr;</span>
              <span className="bg-card-bg border border-card-border rounded-lg px-4 py-2">Add badge to README</span>
              <span className="text-accent">&rarr;</span>
              <span className="bg-card-bg border border-card-border rounded-lg px-4 py-2">Get discovered by agents</span>
            </div>
            <div className="pt-2">
              <Link
                href="/register"
                className="inline-block bg-accent hover:bg-accent-hover text-white px-8 py-3 rounded-lg font-medium transition-colors text-sm"
              >
                Register now &rarr;
              </Link>
            </div>
          </div>
        </section>

        {/* ─── Waitlist ─── */}
        <section className="px-6 py-20 border-t border-card-border">
          <div className="max-w-lg mx-auto text-center space-y-4">
            <h2 className="text-2xl font-bold">Stay in the loop</h2>
            <p className="text-sm text-muted">
              Get notified when we launch enterprise features: continuous
              monitoring, CI/CD integration, and team dashboards.
            </p>
            {waitlistStatus === "done" ? (
              <p className="text-score-green text-sm font-mono pt-2">
                You&apos;re on the list! We&apos;ll be in touch.
              </p>
            ) : (
              <form
                onSubmit={handleWaitlist}
                className="flex gap-2 max-w-sm mx-auto pt-2"
              >
                <input
                  type="email"
                  value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 bg-card-bg border border-card-border rounded-lg px-4 py-2.5 text-foreground placeholder:text-muted/50 focus:outline-none focus:border-accent transition-colors text-sm"
                  required
                />
                <button
                  type="submit"
                  disabled={waitlistStatus === "sending"}
                  className="bg-card-bg border border-card-border hover:border-accent/50 text-foreground px-4 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap disabled:opacity-50"
                >
                  {waitlistStatus === "sending" ? "..." : "Notify me"}
                </button>
              </form>
            )}
            {waitlistStatus === "error" && (
              <p className="text-score-red text-xs font-mono">
                Something went wrong. Try again.
              </p>
            )}
          </div>
        </section>

        {/* ─── Disclaimer ─── */}
        <section className="px-6 py-10 border-t border-card-border">
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-xs text-muted/60 leading-relaxed">
              Clarvia Score does not measure a company&apos;s size or quality.
              It measures how easily AI agents can discover and use this service.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border px-6 py-8">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <span>Built for the agent economy</span>
          <div className="flex items-center gap-6">
            <a
              href="https://x.com/clarvia_ai"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              @clarvia_ai
            </a>
            <a
              href="https://github.com/clarvia-project"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
