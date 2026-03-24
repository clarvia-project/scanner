"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

import { API_BASE } from "@/lib/api";


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

function scoreColor(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function scoreGlowClass(score: number): string {
  if (score >= 70) return "glow-green";
  if (score >= 40) return "glow-yellow";
  return "glow-red";
}

function scoreBgGradient(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bar-gradient-green";
  if (pct >= 0.4) return "bar-gradient-yellow";
  return "bar-gradient-red";
}

function gradeBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/10 text-score-green border-score-green/20";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/10 text-score-yellow border-score-yellow/20";
    case "Basic":
      return "bg-score-yellow/10 text-score-yellow border-score-yellow/20";
    default:
      return "bg-score-red/10 text-score-red border-score-red/20";
  }
}

function DimensionBar({
  label,
  score,
  max,
}: {
  label: string;
  score: number;
  max: number;
}) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground/80">{label}</span>
        <span className="font-mono text-muted">
          {score}/{max}
        </span>
      </div>
      <div className="h-2.5 bg-card-border/40 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${scoreBgGradient(score, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const params = useParams();
  const profileId = params.id as string;

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [badgeCopied, setBadgeCopied] = useState(false);

  useEffect(() => {
    if (!profileId) return;
    fetchProfile();
  }, [profileId]);

  async function fetchProfile() {
    try {
      const res = await fetch(`${API_BASE}/v1/profiles/${profileId}`);
      if (!res.ok) {
        throw new Error(`Profile not found (${res.status})`);
      }
      const data = await res.json();
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunScan() {
    if (!profile) return;
    setScanning(true);
    setScanError("");

    try {
      const res = await fetch(`${API_BASE}/v1/profiles/${profileId}/scan`, {
        method: "POST",
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Scan failed (${res.status})`);
      }

      await fetchProfile();
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  function handleCopyBadge() {
    const badgeCode = `[![Clarvia Score](${API_BASE}/v1/profiles/${profileId}/badge)](https://clarvia.art/profile/${profileId})`;
    navigator.clipboard.writeText(badgeCode);
    setBadgeCopied(true);
    setTimeout(() => setBadgeCopied(false), 2000);
  }

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
              <Link
                href="/tools"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Tools
              </Link>
              <Link
                href="/leaderboard"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Leaderboard
              </Link>
              <Link
                href="/guide"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Guide
              </Link>
              <Link
                href="/register"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Register
              </Link>
              <Link
                href="/docs"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Docs
              </Link>
            </nav>
          </div>
          <span className="text-xs text-muted/60 font-mono hidden sm:inline">v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {loading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-score-red/10 flex items-center justify-center mb-2">
              <svg className="w-8 h-8 text-score-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-score-red font-mono text-sm">{error}</p>
            <Link
              href="/"
              className="text-accent hover:text-accent-hover text-sm transition-colors"
            >
              Back to home
            </Link>
          </div>
        )}

        {profile && (
          <div className="space-y-8">
            {/* Service Header */}
            <div className="text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
                <span className="text-2xl font-bold text-accent">{profile.name.charAt(0).toUpperCase()}</span>
              </div>
              <h1 className="text-3xl font-bold">{profile.name}</h1>
              <p className="text-sm text-muted font-mono">{profile.url}</p>
              <span className="inline-block px-3 py-1.5 rounded-xl text-[10px] font-mono uppercase tracking-wider bg-accent/10 text-accent border border-accent/20">
                {profile.category}
              </span>
            </div>

            {/* Description */}
            <div className="glass-card rounded-2xl px-7 py-6 space-y-4">
              <p className="text-sm leading-relaxed text-foreground/80">
                {profile.description}
              </p>
              {profile.github_url && (
                <a
                  href={profile.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-xs text-accent hover:text-accent-hover transition-colors"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                  View on GitHub
                </a>
              )}
              {profile.tags && profile.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {profile.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2.5 py-1 rounded-lg text-[10px] font-mono bg-card-border/30 text-muted border border-card-border/50"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Clarvia Score */}
            {profile.clarvia_score != null && (
              <div className="space-y-4">
                <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                  Clarvia Score
                </h2>
                <div className={`glass-card rounded-2xl px-7 py-8 text-center space-y-4 ${scoreGlowClass(profile.clarvia_score)}`}>
                  <span
                    className={`text-6xl font-mono font-bold ${scoreColor(profile.clarvia_score)}`}
                  >
                    {profile.clarvia_score}
                  </span>
                  <span className="text-sm text-muted block font-mono">/ 100</span>
                  {profile.rating && (
                    <span
                      className={`inline-block px-4 py-1.5 rounded-xl border text-xs font-mono uppercase tracking-wider ${gradeBadgeClass(profile.rating)}`}
                    >
                      {profile.rating}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Dimension Bars */}
            {profile.dimensions && (
              <div className="space-y-4">
                <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                  Dimensions
                </h2>
                <div className="glass-card rounded-2xl px-7 py-6 space-y-5">
                  <DimensionBar
                    label="API Accessibility"
                    score={profile.dimensions.api_accessibility.score}
                    max={profile.dimensions.api_accessibility.max}
                  />
                  <DimensionBar
                    label="Data Structuring"
                    score={profile.dimensions.data_structuring.score}
                    max={profile.dimensions.data_structuring.max}
                  />
                  <DimensionBar
                    label="Agent Compatibility"
                    score={profile.dimensions.agent_compatibility.score}
                    max={profile.dimensions.agent_compatibility.max}
                  />
                  <DimensionBar
                    label="Trust Signals"
                    score={profile.dimensions.trust_signals.score}
                    max={profile.dimensions.trust_signals.max}
                  />
                </div>
              </div>
            )}

            {/* Run Scan */}
            <div className="space-y-4">
              <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                Scan
              </h2>
              <div className="glass-card rounded-2xl px-7 py-6 space-y-4">
                <p className="text-sm text-muted">
                  {profile.clarvia_score != null
                    ? "Run a new scan to update your Clarvia Score."
                    : "Run your first scan to get a Clarvia Score."}
                </p>
                <button
                  onClick={handleRunScan}
                  disabled={scanning}
                  className="btn-gradient text-white px-6 py-3 rounded-xl text-sm font-medium"
                >
                  {scanning ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Scanning...
                    </span>
                  ) : (
                    "Run Scan"
                  )}
                </button>
                {scanError && (
                  <p className="text-score-red text-xs font-mono">
                    {scanError}
                  </p>
                )}
              </div>
            </div>

            {/* Badge Code */}
            <div className="space-y-4">
              <h2 className="text-xs font-mono text-accent uppercase tracking-widest">
                Badge
              </h2>
              <div className="glass-card rounded-2xl px-7 py-6 space-y-4">
                <p className="text-sm text-muted">
                  Add a Clarvia Score badge to your README or website.
                </p>

                {/* Badge Preview */}
                <div className="flex justify-center py-3">
                  <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-card-bg border border-card-border">
                    <Image
                      src="/logos/clarvia-icon.svg"
                      alt="Clarvia"
                      width={20}
                      height={20}
                      className="rounded-full"
                    />
                    <span className="text-xs font-mono text-muted">Clarvia Score:</span>
                    <span className={`text-xs font-mono font-bold ${profile.clarvia_score != null ? scoreColor(profile.clarvia_score) : "text-muted"}`}>
                      {profile.clarvia_score ?? "—"}
                    </span>
                  </div>
                </div>

                <div className="bg-background/50 border border-card-border/50 rounded-xl p-4 overflow-x-auto">
                  <code className="text-xs text-foreground/60 font-mono whitespace-pre break-all">
                    {`[![Clarvia Score](${API_BASE}/v1/profiles/${profileId}/badge)](https://clarvia.art/profile/${profileId})`}
                  </code>
                </div>
                <button
                  onClick={handleCopyBadge}
                  className="inline-flex items-center gap-2 glass-card hover:border-accent/30 text-foreground px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                >
                  {badgeCopied ? (
                    <>
                      <svg className="w-4 h-4 text-score-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Copied!
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                      </svg>
                      Copy Badge Code
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Metadata */}
            {profile.created_at && (
              <div className="text-center text-xs text-muted/40 font-mono pb-6">
                <p>
                  Registered{" "}
                  {new Date(profile.created_at).toLocaleString("en-US", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>
              </div>
            )}
          </div>
        )}
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
            <span className="text-muted/50 cursor-default" title="Coming soon">Terms</span>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
