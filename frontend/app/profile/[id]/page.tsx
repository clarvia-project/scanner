"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

function scoreBgClass(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bg-score-green";
  if (pct >= 0.4) return "bg-score-yellow";
  return "bg-score-red";
}

function gradeBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/15 text-score-green border-score-green/30";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/15 text-score-yellow border-score-yellow/30";
    case "Basic":
      return "bg-score-yellow/15 text-score-yellow border-score-yellow/30";
    default:
      return "bg-score-red/15 text-score-red border-score-red/30";
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
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground/80">{label}</span>
        <span className="font-mono text-muted">
          {score}/{max}
        </span>
      </div>
      <div className="h-2 bg-card-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${scoreBgClass(score, max)}`}
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

      // Refresh profile to get updated score
      await fetchProfile();
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  function handleCopyBadge() {
    const badgeCode = `[![Clarvia Score](https://clarvia-api.onrender.com/v1/profiles/${profileId}/badge)](https://clarvia.art/profile/${profileId})`;
    navigator.clipboard.writeText(badgeCode);
    setBadgeCopied(true);
    setTimeout(() => setBadgeCopied(false), 2000);
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="font-mono text-sm tracking-widest text-muted uppercase hover:text-foreground transition-colors"
            >
              Clarvia
            </Link>
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

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10">
        {loading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
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
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold">{profile.name}</h1>
              <p className="text-sm text-muted font-mono">{profile.url}</p>
              <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider bg-accent/15 text-accent border border-accent/30">
                {profile.category}
              </span>
            </div>

            {/* Description */}
            <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4">
              <p className="text-sm leading-relaxed text-foreground/80">
                {profile.description}
              </p>
              {profile.github_url && (
                <a
                  href={profile.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-3 text-xs text-accent hover:text-accent-hover transition-colors"
                >
                  View on GitHub &rarr;
                </a>
              )}
              {profile.tags && profile.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {profile.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-card-border/50 text-muted"
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
                <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                  Clarvia Score
                </h2>
                <div className="bg-card-bg border border-card-border rounded-lg px-5 py-6 text-center space-y-3">
                  <span
                    className={`text-5xl font-mono font-bold ${scoreColor(profile.clarvia_score)}`}
                  >
                    {profile.clarvia_score}
                  </span>
                  <span className="text-sm text-muted block">/ 100</span>
                  {profile.rating && (
                    <span
                      className={`inline-block px-3 py-1 rounded-full border text-xs font-mono uppercase tracking-wider ${gradeBadgeClass(profile.rating)}`}
                    >
                      {profile.rating}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Dimension Bars */}
            {profile.dimensions && (
              <div className="space-y-3">
                <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                  Dimensions
                </h2>
                <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4 space-y-4">
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
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                Scan
              </h2>
              <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4 space-y-3">
                <p className="text-sm text-muted">
                  {profile.clarvia_score != null
                    ? "Run a new scan to update your Clarvia Score."
                    : "Run your first scan to get a Clarvia Score."}
                </p>
                <button
                  onClick={handleRunScan}
                  disabled={scanning}
                  className="bg-accent hover:bg-accent-hover disabled:opacity-60 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
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
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
                Badge
              </h2>
              <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4 space-y-3">
                <p className="text-sm text-muted">
                  Add a Clarvia Score badge to your README or website.
                </p>
                <div className="bg-background border border-card-border rounded-lg p-3 overflow-x-auto">
                  <code className="text-xs text-foreground/70 font-mono whitespace-pre break-all">
                    {`[![Clarvia Score](https://clarvia-api.onrender.com/v1/profiles/${profileId}/badge)](https://clarvia.art/profile/${profileId})`}
                  </code>
                </div>
                <button
                  onClick={handleCopyBadge}
                  className="bg-card-bg border border-card-border hover:border-accent/50 text-foreground px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  {badgeCopied ? "Copied!" : "Copy Badge Code"}
                </button>
              </div>
            </div>

            {/* Metadata */}
            {profile.created_at && (
              <div className="text-center text-xs text-muted/50 font-mono pb-6">
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
