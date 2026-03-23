"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export default function RegisterPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

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
    "w-full bg-card-bg border border-card-border rounded-lg px-4 py-3 text-foreground placeholder:text-muted/50 focus:outline-none focus:border-accent transition-colors text-sm";

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
              className="text-xs text-foreground font-medium hover:text-accent transition-colors"
            >
              Register
            </Link>
          </div>
          <span className="text-xs text-muted">AEO Scanner v1.0</span>
        </div>
      </header>

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-10">
        <div className="text-center space-y-3 mb-10">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
            Register Your Service
          </h1>
          <p className="text-muted text-sm md:text-base max-w-lg mx-auto">
            Add your MCP service to the Clarvia directory and get your AEO
            score.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Service Name */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
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

          {/* URL */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
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

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
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

          {/* Category */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
              Category <span className="text-score-red">*</span>
            </label>
            <select
              value={form.category}
              onChange={(e) => updateField("category", e.target.value)}
              className={`${inputClass} appearance-none cursor-pointer`}
              required
            >
              <option value="" disabled>
                Select a category
              </option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* GitHub URL */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
              GitHub URL{" "}
              <span className="text-muted/50 normal-case">(optional)</span>
            </label>
            <input
              type="url"
              value={form.github_url}
              onChange={(e) => updateField("github_url", e.target.value)}
              placeholder="https://github.com/your-org/your-repo"
              className={inputClass}
            />
          </div>

          {/* Tags */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
              Tags{" "}
              <span className="text-muted/50 normal-case">
                (optional, comma separated)
              </span>
            </label>
            <input
              type="text"
              value={form.tags}
              onChange={(e) => updateField("tags", e.target.value)}
              placeholder="e.g. mcp, ai, tools"
              className={inputClass}
            />
          </div>

          {/* Contact Email */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted uppercase tracking-wider font-medium">
              Contact Email{" "}
              <span className="text-muted/50 normal-case">(optional)</span>
            </label>
            <input
              type="email"
              value={form.contact_email}
              onChange={(e) => updateField("contact_email", e.target.value)}
              placeholder="you@example.com"
              className={inputClass}
            />
          </div>

          {error && (
            <p className="text-score-red text-sm font-mono">{error}</p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={
              submitting ||
              !form.name.trim() ||
              !form.url.trim() ||
              !form.description.trim() ||
              !form.category
            }
            className="w-full bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors text-sm"
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
        </form>
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
