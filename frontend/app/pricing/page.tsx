"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import Nav from "@/app/components/Nav";

const FREE_FEATURES = [
  "Search 27,000+ AI agent tools",
  "Basic AEO scores (0-100)",
  "Category browsing & filtering",
  "Embeddable score badges",
  "3 scans per month",
  "Community support",
];

const PRO_FEATURES = [
  "Everything in Free",
  "Unlimited API calls",
  "Semantic search (AI-powered)",
  "Full evidence endpoint",
  "90-day score trend history",
  "Batch gate check (100 URLs)",
  "Live probing data (uptime, latency)",
  "Popularity & adoption metrics",
  "Priority email support",
];

const ENTERPRISE_FEATURES = [
  "Everything in Pro",
  "Webhook notifications (score changes, outages)",
  "Custom scoring weights API",
  "SLA guarantee (99.5% uptime)",
  "Dedicated support channel",
  "Custom integrations",
];

function WaitlistForm({ plan }: { plan: string }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch(`${API_BASE}/v1/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, plan }),
      });
      const data = await res.json();
      if (res.ok) {
        setStatus("success");
        setMessage(data.message || "You're on the list!");
      } else {
        setStatus("error");
        setMessage(data.detail || "Something went wrong");
      }
    } catch {
      setStatus("error");
      setMessage("Network error — please try again");
    }
  };

  if (status === "success") {
    return (
      <div className="text-center py-4">
        <div className="text-2xl mb-2">&#10003;</div>
        <p className="text-sm text-foreground">{message}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-4">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="your@email.com"
        required
        className="px-4 py-2.5 rounded-lg bg-background border border-card-border text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-primary"
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="px-4 py-2.5 rounded-lg bg-primary text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {status === "loading" ? "Joining..." : `Join ${plan.charAt(0).toUpperCase() + plan.slice(1)} Waitlist`}
      </button>
      {status === "error" && <p className="text-xs text-red-400">{message}</p>}
    </form>
  );
}

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Nav />
      <main className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-muted text-lg max-w-2xl mx-auto">
            Start free. Upgrade when your agents need more power.
            Pro and Enterprise are coming soon — join the waitlist for early access.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Free */}
          <div className="rounded-2xl border border-card-border bg-card p-8">
            <h2 className="text-xl font-semibold mb-1">Free</h2>
            <div className="text-3xl font-bold mb-1">$0</div>
            <p className="text-sm text-muted mb-6">Forever free for individuals</p>
            <a
              href="/docs"
              className="block w-full text-center px-4 py-2.5 rounded-lg border border-card-border text-sm font-medium hover:bg-card-border/20 transition-colors mb-6"
            >
              Get Started
            </a>
            <ul className="space-y-3">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <span className="text-green-400 mt-0.5">&#10003;</span>
                  <span className="text-muted">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Pro */}
          <div className="rounded-2xl border-2 border-primary bg-card p-8 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-primary text-white text-xs font-medium rounded-full">
              Coming Soon
            </div>
            <h2 className="text-xl font-semibold mb-1">Pro</h2>
            <div className="text-3xl font-bold mb-1">$49<span className="text-lg font-normal text-muted">/mo</span></div>
            <p className="text-sm text-muted mb-6">For teams building with agents</p>
            <WaitlistForm plan="pro" />
            <ul className="space-y-3 mt-6">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <span className="text-primary mt-0.5">&#10003;</span>
                  <span className="text-muted">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Enterprise */}
          <div className="rounded-2xl border border-card-border bg-card p-8">
            <h2 className="text-xl font-semibold mb-1">Enterprise</h2>
            <div className="text-3xl font-bold mb-1">$299<span className="text-lg font-normal text-muted">/mo</span></div>
            <p className="text-sm text-muted mb-6">For organizations at scale</p>
            <WaitlistForm plan="enterprise" />
            <ul className="space-y-3 mt-6">
              {ENTERPRISE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <span className="text-green-400 mt-0.5">&#10003;</span>
                  <span className="text-muted">{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-24 max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">Frequently asked questions</h2>
          <div className="space-y-8">
            <div>
              <h3 className="font-semibold mb-2">When will Pro launch?</h3>
              <p className="text-sm text-muted">We&apos;re targeting Q2 2026. Waitlist members get early access and a founding member discount.</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Is the Free tier really free forever?</h3>
              <p className="text-sm text-muted">Yes. Search, basic scores, badges, and 3 monthly scans will always be free. We believe every agent deserves good tool discovery.</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">What&apos;s the difference between keyword and semantic search?</h3>
              <p className="text-sm text-muted">Keyword search matches exact terms. Semantic search (Pro) understands intent — searching &quot;file upload tool&quot; finds S3, Supabase Storage, and Cloudflare R2 even if they don&apos;t mention &quot;file upload&quot; literally.</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Can I use the API without a key?</h3>
              <p className="text-sm text-muted">Yes, the Free tier works without an API key (rate-limited by IP). Pro and Enterprise use API keys for higher limits and premium features.</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Do you offer discounts for startups?</h3>
              <p className="text-sm text-muted">Yes! Early-stage startups building agent-first products can apply for 50% off Pro. Email us after joining the waitlist.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
