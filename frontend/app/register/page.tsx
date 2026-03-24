"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";

const CATEGORIES = [
  "AI/LLM",
  "Developer Tools",
  "Payments",
  "Communication",
  "Data",
  "Productivity",
  "Blockchain",
  "MCP",
];

const STEPS = [
  { label: "Service Info", description: "Basic details" },
  { label: "Category & Links", description: "Classification" },
  { label: "Contact", description: "Optional details" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [currentStep, setCurrentStep] = useState(0);

  const [form, setForm] = useState({
    name: "",
    url: "",
    description: "",
    category: "",
    github_url: "",
    tags: "",
    contact_email: "",
  });

  function updateField(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function canAdvance(): boolean {
    if (currentStep === 0) {
      return !!(form.name.trim() && form.url.trim() && form.description.trim());
    }
    if (currentStep === 1) {
      return !!form.category;
    }
    return true;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const body: Record<string, unknown> = {
        name: form.name.trim(),
        url: form.url.trim(),
        description: form.description.trim(),
        category: form.category,
      };

      if (form.github_url.trim()) {
        body.github_url = form.github_url.trim();
      }
      if (form.tags.trim()) {
        body.tags = form.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
      }
      if (form.contact_email.trim()) {
        body.contact_email = form.contact_email.trim();
      }

      const res = await fetch(`${API_BASE}/v1/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Registration failed (${res.status})`);
      }

      const data = await res.json();
      const profileId = data.profile_id || data.id;
      router.push(`/profile/${profileId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-card-bg/80 border border-card-border rounded-xl px-5 py-3.5 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all text-sm";

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
              <Link href="/register" className="text-sm text-foreground font-medium">
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

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-12">
        <div className="text-center space-y-4 mb-12">
          <p className="text-xs font-mono text-accent uppercase tracking-widest">Get started</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            Register Your Service
          </h1>
          <p className="text-muted text-sm md:text-base max-w-lg mx-auto">
            Add your MCP service to the Clarvia directory and get your AEO score.
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-10">
          {STEPS.map((step, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => idx <= currentStep && setCurrentStep(idx)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                  idx === currentStep
                    ? "btn-gradient text-white shadow-md shadow-accent/10"
                    : idx < currentStep
                      ? "bg-score-green/10 text-score-green border border-score-green/20 cursor-pointer"
                      : "bg-card-bg/60 text-muted border border-card-border cursor-default"
                }`}
              >
                <span className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold ${
                  idx < currentStep ? "bg-score-green/20" : idx === currentStep ? "bg-white/20" : "bg-card-border/50"
                }`}>
                  {idx < currentStep ? (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
              </button>
              {idx < STEPS.length - 1 && (
                <div className={`w-8 h-px ${idx < currentStep ? "bg-score-green/30" : "bg-card-border"}`} />
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Step 1: Service Info */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 0 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  Service Name <span className="text-score-red">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => updateField("name", e.target.value)}
                  placeholder="e.g. My MCP Service"
                  className={inputClass}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  URL <span className="text-score-red">*</span>
                </label>
                <input
                  type="url"
                  value={form.url}
                  onChange={(e) => updateField("url", e.target.value)}
                  placeholder="https://api.example.com"
                  className={inputClass}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  Description <span className="text-score-red">*</span>
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => updateField("description", e.target.value)}
                  placeholder="Brief description of what your service does and how agents can use it."
                  rows={4}
                  className={`${inputClass} resize-none`}
                  required
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => canAdvance() && setCurrentStep(1)}
              disabled={!canAdvance()}
              className="w-full btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm"
            >
              Continue
            </button>
          </div>

          {/* Step 2: Category & Links */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 1 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  Category <span className="text-score-red">*</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => updateField("category", cat)}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 border text-center ${
                        form.category === cat
                          ? "btn-gradient text-white border-transparent"
                          : "bg-card-bg/60 text-muted border-card-border hover:border-accent/30"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium">
                  GitHub URL <span className="text-muted/50 normal-case">(optional)</span>
                </label>
                <input
                  type="url"
                  value={form.github_url}
                  onChange={(e) => updateField("github_url", e.target.value)}
                  placeholder="https://github.com/your-org/your-repo"
                  className={inputClass}
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium">
                  Tags <span className="text-muted/50 normal-case">(optional, comma separated)</span>
                </label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={(e) => updateField("tags", e.target.value)}
                  placeholder="e.g. mcp, ai, tools"
                  className={inputClass}
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setCurrentStep(0)}
                className="flex-1 glass-card hover:border-accent/30 text-foreground px-6 py-3.5 rounded-xl font-medium text-sm transition-all text-center"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => canAdvance() && setCurrentStep(2)}
                disabled={!canAdvance()}
                className="flex-1 btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm"
              >
                Continue
              </button>
            </div>
          </div>

          {/* Step 3: Contact */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 2 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium">
                  Contact Email <span className="text-muted/50 normal-case">(optional)</span>
                </label>
                <input
                  type="email"
                  value={form.contact_email}
                  onChange={(e) => updateField("contact_email", e.target.value)}
                  placeholder="you@example.com"
                  className={inputClass}
                />
                <p className="text-xs text-muted/50 mt-1">
                  We&apos;ll notify you when your service is scanned or when important updates are available.
                </p>
              </div>

              {/* Review summary */}
              <div className="border-t border-card-border/30 pt-5">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-3">Review</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Name</span>
                    <span className="font-medium">{form.name || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">URL</span>
                    <span className="font-mono text-xs">{form.url || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Category</span>
                    <span>{form.category || "—"}</span>
                  </div>
                </div>
              </div>
            </div>

            {error && (
              <div className="glass-card rounded-xl p-4 border-score-red/20 bg-score-red/5">
                <p className="text-score-red text-sm font-mono">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="flex-1 glass-card hover:border-accent/30 text-foreground px-6 py-3.5 rounded-xl font-medium text-sm transition-all text-center"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={
                  submitting ||
                  !form.name.trim() ||
                  !form.url.trim() ||
                  !form.description.trim() ||
                  !form.category
                }
                className="flex-1 btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm"
              >
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Registering...
                  </span>
                ) : (
                  "Register Service"
                )}
              </button>
            </div>
          </div>
        </form>
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
