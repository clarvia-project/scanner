"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const EXAMPLE_SCORES = [
  { name: "Stripe", url: "stripe.com", score: 47, rating: "Basic" },
  { name: "GitHub", url: "github.com", score: 53, rating: "Basic" },
  { name: "Notion", url: "notion.so", score: 62, rating: "Good" },
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

export default function LandingPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleScan(targetUrl?: string) {
    const scanUrl = targetUrl || url.trim();
    if (!scanUrl) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch("http://localhost:8000/api/scan", {
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

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <span className="font-mono text-sm tracking-widest text-muted uppercase">
            Clarvia
          </span>
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
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Scanning...
                </span>
              ) : (
                "Scan"
              )}
            </button>
          </form>

          {error && (
            <p className="text-score-red text-sm font-mono">{error}</p>
          )}

          {/* Example Scores */}
          <div className="pt-8 space-y-4">
            <p className="text-xs text-muted uppercase tracking-wider">
              Example Scores
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-lg mx-auto">
              {EXAMPLE_SCORES.map((ex) => (
                <button
                  key={ex.name}
                  onClick={() => handleExampleClick(ex.url)}
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
            href="https://github.com"
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
