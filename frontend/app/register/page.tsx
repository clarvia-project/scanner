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

const SERVICE_TYPES = [
  {
    id: "mcp_server",
    label: "MCP Server",
    description: "Model Context Protocol server for AI agents",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
      </svg>
    ),
  },
  {
    id: "skill",
    label: "Skill",
    description: "Reusable skill file for agent workflows",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
      </svg>
    ),
  },
  {
    id: "cli_tool",
    label: "CLI Tool",
    description: "Command-line tool or utility",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
  },
  {
    id: "api",
    label: "API",
    description: "REST or GraphQL API service",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75L16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
      </svg>
    ),
  },
  {
    id: "general",
    label: "General Service",
    description: "Any other web service or platform",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
  },
];

const COMPATIBLE_AGENTS = ["Claude Code", "ChatGPT", "Cursor", "Windsurf", "Cline", "Other"];

const STEPS = [
  { label: "Service Type", description: "Choose type" },
  { label: "Service Info", description: "Basic details" },
  { label: "Category & Config", description: "Classification" },
  { label: "Verification", description: "Magic link" },
];

type ServiceTypeId = "mcp_server" | "skill" | "cli_tool" | "api" | "general";

export default function RegisterPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [currentStep, setCurrentStep] = useState(0);
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [magicLinkSending, setMagicLinkSending] = useState(false);

  const [form, setForm] = useState({
    service_type: "" as ServiceTypeId | "",
    name: "",
    url: "",
    description: "",
    category: "",
    github_url: "",
    tags: "",
    contact_email: "",
    // MCP Server fields
    mcp_npm_package: "",
    mcp_endpoint_url: "",
    mcp_transport: "stdio",
    mcp_tools: "",
    // Skill fields
    skill_file_url: "",
    skill_compatible_agents: [] as string[],
    // CLI Tool fields
    cli_package_manager: "npm",
    cli_package_name: "",
    cli_binary_name: "",
    cli_usage_example: "",
    // API fields
    api_openapi_url: "",
    api_auth_method: "none",
    api_base_url: "",
  });

  function updateField(field: string, value: string | string[]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function toggleAgent(agent: string) {
    setForm((prev) => {
      const agents = prev.skill_compatible_agents.includes(agent)
        ? prev.skill_compatible_agents.filter((a) => a !== agent)
        : [...prev.skill_compatible_agents, agent];
      return { ...prev, skill_compatible_agents: agents };
    });
  }

  function canAdvance(): boolean {
    if (currentStep === 0) {
      return !!form.service_type;
    }
    if (currentStep === 1) {
      return !!(form.name.trim() && form.url.trim() && form.description.trim());
    }
    if (currentStep === 2) {
      return !!form.category;
    }
    return true;
  }

  function buildTypeConfig(): Record<string, unknown> | null {
    switch (form.service_type) {
      case "mcp_server":
        return {
          npm_package: form.mcp_npm_package.trim() || undefined,
          endpoint_url: form.mcp_endpoint_url.trim() || undefined,
          transport: form.mcp_transport,
          tools: form.mcp_tools.trim()
            ? form.mcp_tools.split(",").map((t) => t.trim()).filter(Boolean)
            : undefined,
        };
      case "skill":
        return {
          file_url: form.skill_file_url.trim() || undefined,
          compatible_agents: form.skill_compatible_agents.length
            ? form.skill_compatible_agents
            : undefined,
        };
      case "cli_tool":
        return {
          package_manager: form.cli_package_manager,
          package_name: form.cli_package_name.trim() || undefined,
          binary_name: form.cli_binary_name.trim() || undefined,
          usage_example: form.cli_usage_example.trim() || undefined,
        };
      case "api":
        return {
          openapi_url: form.api_openapi_url.trim() || undefined,
          auth_method: form.api_auth_method,
          base_url: form.api_base_url.trim() || undefined,
        };
      default:
        return null;
    }
  }

  async function handleSendMagicLink() {
    if (!form.contact_email.trim()) return;
    setMagicLinkSending(true);
    try {
      const res = await fetch(`${API_BASE}/v1/auth/magic-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.contact_email.trim() }),
      });
      if (res.ok) {
        setMagicLinkSent(true);
      }
    } catch {
      // Silently handle — user can still submit without verification
    } finally {
      setMagicLinkSending(false);
    }
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
        service_type: form.service_type || "general",
      };

      const typeConfig = buildTypeConfig();
      if (typeConfig) {
        body.type_config = typeConfig;
      }

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

  const selectClass =
    "w-full bg-card-bg/80 border border-card-border rounded-xl px-5 py-3.5 text-foreground focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all text-sm appearance-none";

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

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-12">
        <div className="text-center space-y-4 mb-12">
          <p className="text-xs font-mono text-accent uppercase tracking-widest">Get started</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            Register Your Service
          </h1>
          <p className="text-muted text-sm md:text-base max-w-lg mx-auto">
            Add your service to the Clarvia registry and get your AEO score.
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
          {/* Step 0: Service Type Selection */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 0 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8">
              <label className="text-xs text-muted uppercase tracking-wider font-medium mb-4 block">
                What are you registering? <span className="text-score-red">*</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {SERVICE_TYPES.map((type) => (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => updateField("service_type", type.id)}
                    className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-200 text-left ${
                      form.service_type === type.id
                        ? "border-accent/50 bg-accent/10 shadow-md shadow-accent/5"
                        : "border-card-border bg-card-bg/40 hover:border-accent/30 hover:bg-card-bg/60"
                    }`}
                  >
                    <div className={`shrink-0 p-2 rounded-lg ${
                      form.service_type === type.id
                        ? "bg-accent/20 text-accent"
                        : "bg-card-border/30 text-muted"
                    }`}>
                      {type.icon}
                    </div>
                    <div className="min-w-0">
                      <div className={`text-sm font-medium ${
                        form.service_type === type.id ? "text-foreground" : "text-muted"
                      }`}>
                        {type.label}
                      </div>
                      <div className="text-xs text-muted/60 mt-0.5">{type.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={() => canAdvance() && setCurrentStep(1)}
              disabled={!canAdvance()}
              className="w-full btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>

          {/* Step 1: Service Info */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 1 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  Service Name <span className="text-score-red">*</span>
                </label>
                <input
                  type="text"
                  name="name"
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
                  name="url"
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
                  name="description"
                  value={form.description}
                  onChange={(e) => updateField("description", e.target.value)}
                  placeholder="Brief description of what your service does and how agents can use it."
                  rows={4}
                  className={`${inputClass} resize-none`}
                  required
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
                className="flex-1 btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          </div>

          {/* Step 2: Category & Type-specific Config */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 2 ? "block" : "hidden"}`}>
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
                  name="github_url"
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
                  name="tags"
                  value={form.tags}
                  onChange={(e) => updateField("tags", e.target.value)}
                  placeholder="e.g. mcp, ai, tools"
                  className={inputClass}
                />
              </div>

              {/* Dynamic type-specific fields */}
              {form.service_type === "mcp_server" && (
                <div className="border-t border-card-border/30 pt-6 space-y-4">
                  <p className="text-xs text-accent uppercase tracking-wider font-medium">MCP Server Configuration</p>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      npm Package Name
                    </label>
                    <input
                      type="text"
                      name="mcp_npm_package"
                      value={form.mcp_npm_package}
                      onChange={(e) => updateField("mcp_npm_package", e.target.value)}
                      placeholder="e.g. @org/mcp-server"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Endpoint URL
                    </label>
                    <input
                      type="url"
                      name="mcp_endpoint_url"
                      value={form.mcp_endpoint_url}
                      onChange={(e) => updateField("mcp_endpoint_url", e.target.value)}
                      placeholder="https://mcp.example.com/sse"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Transport
                    </label>
                    <select
                      value={form.mcp_transport}
                      onChange={(e) => updateField("mcp_transport", e.target.value)}
                      className={selectClass}
                    >
                      <option value="stdio">stdio</option>
                      <option value="sse">SSE (Server-Sent Events)</option>
                      <option value="streamable-http">Streamable HTTP</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Tools <span className="text-muted/50 normal-case">(comma separated)</span>
                    </label>
                    <input
                      type="text"
                      name="mcp_tools"
                      value={form.mcp_tools}
                      onChange={(e) => updateField("mcp_tools", e.target.value)}
                      placeholder="e.g. search, create, update, delete"
                      className={inputClass}
                    />
                  </div>
                </div>
              )}

              {form.service_type === "skill" && (
                <div className="border-t border-card-border/30 pt-6 space-y-4">
                  <p className="text-xs text-accent uppercase tracking-wider font-medium">Skill Configuration</p>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Skill File URL
                    </label>
                    <input
                      type="url"
                      name="skill_file_url"
                      value={form.skill_file_url}
                      onChange={(e) => updateField("skill_file_url", e.target.value)}
                      placeholder="https://example.com/skills/my-skill.md"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Compatible Agents
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {COMPATIBLE_AGENTS.map((agent) => (
                        <button
                          key={agent}
                          type="button"
                          onClick={() => toggleAgent(agent)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border ${
                            form.skill_compatible_agents.includes(agent)
                              ? "bg-accent/15 text-accent border-accent/40"
                              : "bg-card-bg/40 text-muted/70 border-card-border/50 hover:border-accent/20"
                          }`}
                        >
                          {agent}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {form.service_type === "cli_tool" && (
                <div className="border-t border-card-border/30 pt-6 space-y-4">
                  <p className="text-xs text-accent uppercase tracking-wider font-medium">CLI Tool Configuration</p>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-2">
                      <label className="text-xs text-muted uppercase tracking-wider font-medium">
                        Package Manager
                      </label>
                      <select
                        value={form.cli_package_manager}
                        onChange={(e) => updateField("cli_package_manager", e.target.value)}
                        className={selectClass}
                      >
                        <option value="npm">npm</option>
                        <option value="pip">pip</option>
                        <option value="brew">brew</option>
                        <option value="cargo">cargo</option>
                      </select>
                    </div>
                    <div className="col-span-2 space-y-2">
                      <label className="text-xs text-muted uppercase tracking-wider font-medium">
                        Package Name
                      </label>
                      <input
                        type="text"
                        name="cli_package_name"
                        value={form.cli_package_name}
                        onChange={(e) => updateField("cli_package_name", e.target.value)}
                        placeholder="e.g. my-cli-tool"
                        className={inputClass}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Binary Name
                    </label>
                    <input
                      type="text"
                      name="cli_binary_name"
                      value={form.cli_binary_name}
                      onChange={(e) => updateField("cli_binary_name", e.target.value)}
                      placeholder="e.g. mytool"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Usage Example
                    </label>
                    <textarea
                      name="cli_usage_example"
                      value={form.cli_usage_example}
                      onChange={(e) => updateField("cli_usage_example", e.target.value)}
                      placeholder={"$ mytool scan --url https://example.com\n$ mytool report --format json"}
                      rows={3}
                      className={`${inputClass} resize-none font-mono text-xs`}
                    />
                  </div>
                </div>
              )}

              {form.service_type === "api" && (
                <div className="border-t border-card-border/30 pt-6 space-y-4">
                  <p className="text-xs text-accent uppercase tracking-wider font-medium">API Configuration</p>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      OpenAPI Spec URL
                    </label>
                    <input
                      type="url"
                      name="api_openapi_url"
                      value={form.api_openapi_url}
                      onChange={(e) => updateField("api_openapi_url", e.target.value)}
                      placeholder="https://api.example.com/openapi.json"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Authentication Method
                    </label>
                    <select
                      value={form.api_auth_method}
                      onChange={(e) => updateField("api_auth_method", e.target.value)}
                      className={selectClass}
                    >
                      <option value="none">None</option>
                      <option value="api_key">API Key</option>
                      <option value="oauth">OAuth 2.0</option>
                      <option value="bearer">Bearer Token</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted uppercase tracking-wider font-medium">
                      Base URL
                    </label>
                    <input
                      type="url"
                      name="api_base_url"
                      value={form.api_base_url}
                      onChange={(e) => updateField("api_base_url", e.target.value)}
                      placeholder="https://api.example.com/v1"
                      className={inputClass}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="flex-1 glass-card hover:border-accent/30 text-foreground px-6 py-3.5 rounded-xl font-medium text-sm transition-all text-center"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => canAdvance() && setCurrentStep(3)}
                disabled={!canAdvance()}
                className="flex-1 btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          </div>

          {/* Step 3: Verification (Magic Link) */}
          <div className={`space-y-5 transition-all duration-300 ${currentStep === 3 ? "block" : "hidden"}`}>
            <div className="glass-card rounded-2xl p-8 space-y-6">
              <div className="space-y-2">
                <label className="text-xs text-muted uppercase tracking-wider font-medium flex items-center gap-1">
                  Email Address <span className="text-score-red">*</span>
                </label>
                <div className="flex gap-3">
                  <input
                    type="email"
                    name="contact_email"
                    value={form.contact_email}
                    onChange={(e) => {
                      updateField("contact_email", e.target.value);
                      setMagicLinkSent(false);
                    }}
                    placeholder="you@example.com"
                    className={`${inputClass} flex-1`}
                    required
                  />
                  <button
                    type="button"
                    onClick={handleSendMagicLink}
                    disabled={!form.contact_email.trim() || magicLinkSending}
                    className="shrink-0 px-5 py-3.5 rounded-xl text-sm font-medium transition-all border border-accent/40 text-accent hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {magicLinkSending ? (
                      <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                    ) : magicLinkSent ? (
                      "Sent!"
                    ) : (
                      "Send Verification Link"
                    )}
                  </button>
                </div>
                {magicLinkSent ? (
                  <p className="text-xs text-score-green mt-1">
                    Verification link sent! Check your inbox. You can still submit without verifying.
                  </p>
                ) : (
                  <p className="text-xs text-muted/50 mt-1">
                    We&apos;ll send a verification link to confirm ownership. You can also submit and verify later.
                  </p>
                )}
              </div>

              {/* Review summary */}
              <div className="border-t border-card-border/30 pt-5">
                <p className="text-xs text-muted uppercase tracking-wider font-medium mb-3">Review</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Type</span>
                    <span className="font-medium capitalize">
                      {SERVICE_TYPES.find((t) => t.id === form.service_type)?.label || "General"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Name</span>
                    <span className="font-medium">{form.name || "\u2014"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">URL</span>
                    <span className="font-mono text-xs">{form.url || "\u2014"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Category</span>
                    <span>{form.category || "\u2014"}</span>
                  </div>
                  {form.service_type === "mcp_server" && form.mcp_transport && (
                    <div className="flex justify-between">
                      <span className="text-muted">Transport</span>
                      <span className="font-mono text-xs">{form.mcp_transport}</span>
                    </div>
                  )}
                  {form.service_type === "cli_tool" && form.cli_package_name && (
                    <div className="flex justify-between">
                      <span className="text-muted">Install</span>
                      <span className="font-mono text-xs">{form.cli_package_manager} install {form.cli_package_name}</span>
                    </div>
                  )}
                  {form.service_type === "api" && form.api_auth_method !== "none" && (
                    <div className="flex justify-between">
                      <span className="text-muted">Auth</span>
                      <span className="capitalize text-xs">{form.api_auth_method.replace("_", " ")}</span>
                    </div>
                  )}
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
                onClick={() => setCurrentStep(2)}
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
                  !form.category ||
                  !form.contact_email.trim()
                }
                className="flex-1 btn-gradient text-white px-6 py-3.5 rounded-xl font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
            <span className="text-muted/50 cursor-default" title="Coming soon">Terms</span>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
