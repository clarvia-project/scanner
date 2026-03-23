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

  // Advance phases
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
          .slice(0, 3)
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

  function handleExampleClick(exampleUrl: string) {
    setUrl(exampleUrl);
    handleScan(exampleUrl);
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
        <div className="max-w-4xl mx-auto flex items-center justify-between">
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

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <div className="max-w-2xl w-full text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
              Is your service ready
              <br />
              for AI agents?
            </h1>
            <p className="text-lg text-muted max-w-lg mx-auto">
              Get your Clarvia Score — the AEO standard for agent
              discoverability and trust.
            </p>
          </div>

          {/* URL Input */}
          <form onSubmit={handleSubmit} className="flex gap-3 max-w-lg mx-auto">
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

          {/* Top Scores */}
          <div className="pt-8 space-y-4">
            <p className="text-xs text-muted uppercase tracking-wider">
              Top Scores
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-lg mx-auto">
              {topScores.map((ex) => (
                <button
                  key={ex.name}
                  onClick={() =>
                    ex.scan_id
                      ? router.push(`/scan/${ex.scan_id}`)
                      : handleExampleClick(ex.url)
                  }
                  disabled={loading}
                  className={`bg-card-bg border ${scoreBorderColor(ex.score)} rounded-lg p-4 text-left hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="text-sm text-muted mb-1">{ex.name}</div>
                  <div
                    className={`text-2xl font-mono font-bold ${scoreColor(ex.score)}`}
                  >
                    {ex.score}
                  </div>
                  <div className="text-xs text-muted mt-1">{ex.rating}</div>
                </button>
              ))}
            </div>
            <Link
              href="/leaderboard"
              className="inline-block text-xs text-accent hover:text-accent-hover transition-colors"
            >
              View full leaderboard &rarr;
            </Link>
          </div>

          {/* MCP Developer CTA */}
          <div className="pt-8">
            <Link
              href="/register"
              className="inline-block text-sm text-accent hover:text-accent-hover transition-colors"
            >
              Are you an MCP developer? Register your service &rarr;
            </Link>
          </div>

          {/* Waitlist */}
          <div className="pt-12 space-y-3">
            <p className="text-xs text-muted uppercase tracking-wider">
              Join the Waitlist
            </p>
            <p className="text-sm text-muted max-w-md mx-auto">
              Get notified when we launch enterprise features: continuous
              monitoring, CI/CD integration, and team dashboards.
            </p>
            {waitlistStatus === "done" ? (
              <p className="text-score-green text-sm font-mono">
                You&apos;re on the list! We&apos;ll be in touch.
              </p>
            ) : (
              <form
                onSubmit={handleWaitlist}
                className="flex gap-2 max-w-sm mx-auto"
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
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border px-6 py-6">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted">
          <span>
            Clarvia — Discovery & Trust standard for the agent economy
          </span>
          <a
            href="https://github.com/clarvia-project"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
