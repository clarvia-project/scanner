"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";

// ----- Types -----

interface SubFactor {
  score: number;
  max: number;
  label: string;
  evidence?: Record<string, unknown>;
}

interface Dimension {
  score: number;
  max: number;
  sub_factors?: Record<string, SubFactor>;
}

interface ScanEntry {
  scan_id: string;
  profile_id?: string;
  url: string;
  service_name: string;
  service_type?: string;
  clarvia_score: number;
  rating: string;
  scanned_at: string;
  dimensions: {
    api_accessibility: Dimension;
    data_structuring: Dimension;
    agent_compatibility: Dimension;
    trust_signals: Dimension;
  };
}

// ----- Service type constants -----

const SERVICE_TYPE_TABS = [
  { id: "all", label: "All" },
  { id: "mcp_server", label: "MCP" },
  { id: "skill", label: "Skill" },
  { id: "cli_tool", label: "CLI" },
  { id: "api", label: "API" },
];

const TYPE_BADGE_STYLES: Record<string, string> = {
  mcp_server: "bg-purple-500/15 text-purple-400 border-purple-500/25",
  skill: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  cli_tool: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  api: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  general: "bg-gray-500/15 text-gray-400 border-gray-500/25",
};

const TYPE_LABELS: Record<string, string> = {
  mcp_server: "MCP",
  skill: "Skill",
  cli_tool: "CLI",
  api: "API",
  general: "General",
};

// ----- Sort types -----

type SortKey = "score" | "name" | "api" | "data" | "agent" | "trust";
type SortDir = "asc" | "desc";

// ----- Category mapping -----

const CATEGORY_MAP: Record<string, string[]> = {
  "AI/LLM": [
    "openai", "anthropic", "google ai", "mistral", "cohere",
    "replicate", "hugging face", "together ai", "groq", "perplexity",
  ],
  "Developer Tools": [
    "github", "gitlab", "vercel", "netlify", "supabase",
    "firebase", "aws", "cloudflare", "railway", "render",
  ],
  Payments: ["stripe", "paypal", "squareup", "plaid", "coinbase", "circle"],
  Communication: ["slack", "discord", "twilio", "sendgrid", "resend"],
  Data: ["snowflake", "databricks", "mixpanel", "amplitude", "segment"],
  Productivity: ["notion", "linear", "atlassian", "asana", "figma", "canva"],
  MCP: ["mcp", "smithery", "glama"],
};

// Blockchain subcategories
const BLOCKCHAIN_SUBCATEGORIES: Record<string, string[]> = {
  "Node Providers": ["alchemy", "infura", "quicknode"],
  Indexers: ["the graph", "goldsky", "helius"],
  Analytics: ["dune", "flipside"],
  "Full-stack": ["moralis"],
  "L1 / Networks": ["solana", "ethereum"],
};

// Flattened list of all blockchain service names for top-level matching
const ALL_BLOCKCHAIN_NAMES = Object.values(BLOCKCHAIN_SUBCATEGORIES).flat();

const CATEGORIES = ["All", ...Object.keys(CATEGORY_MAP), "Blockchain"];

function getCategory(serviceName: string): string {
  const lower = serviceName.toLowerCase();
  // Check blockchain first (subcategories)
  if (ALL_BLOCKCHAIN_NAMES.some((n) => lower.includes(n))) return "Blockchain";
  for (const [cat, names] of Object.entries(CATEGORY_MAP)) {
    if (names.some((n) => lower.includes(n))) return cat;
  }
  return "Other";
}

function getBlockchainSubcategory(serviceName: string): string | null {
  const lower = serviceName.toLowerCase();
  for (const [sub, names] of Object.entries(BLOCKCHAIN_SUBCATEGORIES)) {
    if (names.some((n) => lower.includes(n))) return sub;
  }
  return null;
}

// ----- Sub-factor filter definitions -----

interface SubFactorFilter {
  id: string;
  label: string;
  test: (entry: ScanEntry) => boolean;
}

const SUB_FACTOR_FILTERS: SubFactorFilter[] = [
  {
    id: "mcp",
    label: "Has MCP Support",
    test: (e) => (e.dimensions?.agent_compatibility?.sub_factors?.mcp_server_exists?.score ?? 0) > 0,
  },
  {
    id: "openapi",
    label: "Has OpenAPI Spec",
    test: (e) => (e.dimensions?.data_structuring?.sub_factors?.schema_definition?.score ?? 0) > 5,
  },
  {
    id: "errors",
    label: "Good Error Handling",
    test: (e) => (e.dimensions?.data_structuring?.sub_factors?.error_structure?.score ?? 0) > 5,
  },
  {
    id: "fast",
    label: "Fast Response",
    test: (e) => (e.dimensions?.api_accessibility?.sub_factors?.response_speed?.score ?? 0) >= 7,
  },
];

// ----- Helpers -----

function scoreColor(score: number): string {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function dimScoreColor(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "text-score-green";
  if (pct >= 0.4) return "text-score-yellow";
  return "text-score-red";
}

function ratingBadgeClass(rating: string): string {
  switch (rating) {
    case "Exceptional":
    case "Strong":
      return "bg-score-green/10 text-score-green border border-score-green/20";
    case "Moderate":
    case "Good":
      return "bg-score-yellow/10 text-score-yellow border border-score-yellow/20";
    case "Basic":
      return "bg-score-yellow/10 text-score-yellow border border-score-yellow/20";
    default:
      return "bg-score-red/10 text-score-red border border-score-red/20";
  }
}

function dimBarGradient(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bar-gradient-green";
  if (pct >= 0.4) return "bar-gradient-yellow";
  return "bar-gradient-red";
}

function dimValue(entry: ScanEntry, key: SortKey): number {
  const d = entry.dimensions;
  switch (key) {
    case "api": return d?.api_accessibility?.score ?? 0;
    case "data": return d?.data_structuring?.score ?? 0;
    case "agent": return d?.agent_compatibility?.score ?? 0;
    case "trust": return d?.trust_signals?.score ?? 0;
    case "score": return entry.clarvia_score;
    default: return 0;
  }
}

// ----- Components -----

function DimMiniBar({
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
    <div className="flex items-center gap-2 min-w-0">
      <span className="text-[10px] text-muted w-10 shrink-0 text-right font-mono">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-card-border/50 rounded-full overflow-hidden min-w-[40px]">
        <div
          className={`h-full rounded-full ${dimBarGradient(score, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-muted font-mono w-8 shrink-0">
        {score}/{max}
      </span>
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-gold text-[11px] font-bold">1</span>;
  }
  if (rank === 2) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-silver text-[11px] font-bold">2</span>;
  }
  if (rank === 3) {
    return <span className="inline-flex items-center justify-center w-7 h-7 rounded-full badge-bronze text-[11px] font-bold">3</span>;
  }
  return <span className="text-sm text-muted font-mono">{rank}</span>;
}

function SortArrow({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-muted/30 ml-1">&#x25B4;</span>;
  return (
    <span className="text-accent ml-1">
      {dir === "asc" ? "\u25B4" : "\u25BE"}
    </span>
  );
}

// ----- Compare bar chart -----

function CompareBarChart({
  items,
  dimKey,
  label,
}: {
  items: ScanEntry[];
  dimKey: keyof ScanEntry["dimensions"];
  label: string;
}) {
  const max = items[0]?.dimensions[dimKey].max ?? 25;
  const scores = items.map((it) => it.dimensions[dimKey].score);
  const best = Math.max(...scores);

  return (
    <div className="space-y-2">
      <div className="text-xs font-mono text-muted uppercase tracking-wider">{label}</div>
      {items.map((it, i) => {
        const s = it.dimensions[dimKey].score;
        const pct = max > 0 ? (s / max) * 100 : 0;
        const isWinner = s === best && scores.filter((x) => x === best).length === 1;
        return (
          <div key={it.scan_id} className="flex items-center gap-3">
            <span className="text-xs text-foreground w-28 truncate shrink-0">{it.service_name}</span>
            <div className="flex-1 h-5 bg-card-border/30 rounded overflow-hidden relative">
              <div
                className={`h-full rounded ${isWinner ? "bg-accent" : "bg-accent/40"} transition-all`}
                style={{ width: `${pct}%` }}
              />
              <span className="absolute inset-0 flex items-center justify-end pr-2 text-[10px] font-mono text-foreground/70">
                {s}/{max}
              </span>
            </div>
            {isWinner && (
              <span className="text-[10px] font-mono text-accent shrink-0">WIN</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ----- Compare Modal -----

function CompareModal({
  items,
  onClose,
}: {
  items: ScanEntry[];
  onClose: () => void;
}) {
  const dims: { key: keyof ScanEntry["dimensions"]; label: string }[] = [
    { key: "api_accessibility", label: "API Accessibility" },
    { key: "data_structuring", label: "Data Structuring" },
    { key: "agent_compatibility", label: "Agent Compatibility" },
    { key: "trust_signals", label: "Trust Signals" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative glass-card rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold">Compare Services</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-foreground transition-colors text-lg leading-none"
          >
            &#x2715;
          </button>
        </div>

        {/* Overall scores */}
        <div className="flex gap-4 mb-8">
          {items.map((it) => (
            <div key={it.scan_id} className="flex-1 bg-card-bg/60 border border-card-border rounded-xl p-4 text-center">
              <div className="text-sm font-medium truncate mb-1">{it.service_name}</div>
              <div className={`text-2xl font-mono font-bold ${scoreColor(it.clarvia_score)}`}>
                {it.clarvia_score}
              </div>
              <div className={`text-[10px] font-mono uppercase mt-1 ${ratingBadgeClass(it.rating)} inline-block px-2 py-0.5 rounded`}>
                {it.rating}
              </div>
            </div>
          ))}
        </div>

        {/* Dimension comparisons */}
        <div className="space-y-6">
          {dims.map((d) => (
            <CompareBarChart key={d.key} items={items} dimKey={d.key} label={d.label} />
          ))}
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={onClose}
            className="text-sm text-muted hover:text-foreground transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ----- Main Page -----

export default function LeaderboardPage() {
  const [data, setData] = useState<ScanEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [activeSubFilters, setActiveSubFilters] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showCompare, setShowCompare] = useState(false);
  const [blockchainSubs, setBlockchainSubs] = useState<Set<string>>(new Set());
  const [serviceTypeFilter, setServiceTypeFilter] = useState("all");
  const [typeFilteredData, setTypeFilteredData] = useState<ScanEntry[] | null>(null);
  const [typeLoading, setTypeLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    fetch("/data/prebuilt-scans.json")
      .then((res) => res.json())
      .then((json: ScanEntry[]) => {
        setData(json);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Fetch type-filtered data from API
  useEffect(() => {
    if (serviceTypeFilter === "all") {
      setTypeFilteredData(null);
      return;
    }
    setTypeLoading(true);
    fetch(`${API_BASE}/v1/services?service_type=${serviceTypeFilter}`)
      .then((res) => (res.ok ? res.json() : []))
      .then((json: ScanEntry[]) => setTypeFilteredData(json))
      .catch(() => setTypeFilteredData([]))
      .finally(() => setTypeLoading(false));
  }, [serviceTypeFilter]);

  const toggleSubFilter = useCallback((id: string) => {
    setActiveSubFilters((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelected = useCallback((scanId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(scanId)) {
        next.delete(scanId);
      } else {
        if (next.size >= 3) return prev; // max 3
        next.add(scanId);
      }
      return next;
    });
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "desc" ? "asc" : "desc"));
        return key;
      }
      setSortDir(key === "name" ? "asc" : "desc");
      return key;
    });
  }, []);

  const handleRowClick = useCallback(async (item: ScanEntry) => {
    if (item.scan_id) {
      router.push(`/scan/${item.scan_id}`);
      return;
    }
    // No scan_id — trigger a live scan of the service URL
    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: item.url }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.scan_id) {
          router.push(`/scan/${data.scan_id}`);
          return;
        }
      }
      // Fallback: navigate to home scanner with URL prefilled
      router.push(`/?url=${encodeURIComponent(item.url)}`);
    } catch {
      router.push(`/?url=${encodeURIComponent(item.url)}`);
    }
  }, [router]);

  const filtered = useMemo(() => {
    let list = typeFilteredData ?? data;

    // Category filter
    if (category !== "All") {
      list = list.filter((item) => getCategory(item.service_name) === category);
    }

    // Blockchain subcategory filter
    if (category === "Blockchain" && blockchainSubs.size > 0) {
      list = list.filter((item) => {
        const sub = getBlockchainSubcategory(item.service_name);
        return sub !== null && blockchainSubs.has(sub);
      });
    }

    // Search filter
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (item) =>
          item.service_name.toLowerCase().includes(q) ||
          item.url.toLowerCase().includes(q),
      );
    }

    // Sub-factor filters
    for (const fId of activeSubFilters) {
      const filterDef = SUB_FACTOR_FILTERS.find((f) => f.id === fId);
      if (filterDef) {
        list = list.filter(filterDef.test);
      }
    }

    // Sorting
    list = [...list].sort((a, b) => {
      if (sortKey === "name") {
        const cmp = a.service_name.localeCompare(b.service_name);
        return sortDir === "asc" ? cmp : -cmp;
      }
      const aVal = sortKey === "score" ? a.clarvia_score : dimValue(a, sortKey);
      const bVal = sortKey === "score" ? b.clarvia_score : dimValue(b, sortKey);
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

    return list;
  }, [data, typeFilteredData, category, search, activeSubFilters, sortKey, sortDir, blockchainSubs]);

  const compareItems = useMemo(
    () => data.filter((d) => selected.has(d.scan_id)),
    [data, selected],
  );

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
                href="/trending"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Trending
              </Link>
              <Link
                href="/compare"
                className="text-sm text-muted hover:text-foreground transition-colors"
              >
                Compare
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

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
        {/* Title */}
        <div className="text-center space-y-4 mb-12">
          <p className="text-xs font-mono text-accent uppercase tracking-widest">Rankings</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            AEO Leaderboard
          </h1>
          <p className="text-muted text-sm md:text-base max-w-xl mx-auto">
            How agent-ready is your favorite service?
          </p>
        </div>

        {/* Search */}
        <div className="mb-8 max-w-md mx-auto">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search services..."
              className="w-full bg-card-bg/80 border border-card-border rounded-xl pl-11 pr-4 py-3 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all font-mono text-sm"
            />
          </div>
        </div>

        {/* Service type tabs */}
        <div className="flex justify-center gap-1 mb-6">
          {SERVICE_TYPE_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setServiceTypeFilter(tab.id)}
              className={`px-5 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                serviceTypeFilter === tab.id
                  ? "bg-accent text-white shadow-md shadow-accent/15"
                  : "text-muted hover:text-foreground hover:bg-card-bg/60"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-4">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => {
                setCategory(cat);
                if (cat !== "Blockchain") setBlockchainSubs(new Set());
              }}
              className={`px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 border ${
                category === cat
                  ? "btn-gradient text-white border-transparent shadow-md shadow-accent/10"
                  : "bg-card-bg/60 text-muted border-card-border hover:border-accent/30 hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Blockchain subcategory filters */}
        {category === "Blockchain" && (
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            {Object.keys(BLOCKCHAIN_SUBCATEGORIES).map((sub) => {
              const active = blockchainSubs.has(sub);
              return (
                <button
                  key={sub}
                  onClick={() => {
                    setBlockchainSubs((prev) => {
                      const next = new Set(prev);
                      if (next.has(sub)) next.delete(sub);
                      else next.add(sub);
                      return next;
                    });
                  }}
                  className={`px-3 py-1.5 rounded-full text-[11px] font-mono transition-all duration-200 border ${
                    active
                      ? "bg-accent/15 text-accent border-accent/40 shadow-sm shadow-accent/10"
                      : "bg-card-bg/40 text-muted/70 border-card-border/50 hover:border-accent/20 hover:text-muted"
                  }`}
                >
                  <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${active ? "bg-accent" : "bg-muted/30"}`} />
                  {sub}
                </button>
              );
            })}
          </div>
        )}

        {/* Sub-factor pill filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {SUB_FACTOR_FILTERS.map((f) => {
            const active = activeSubFilters.has(f.id);
            return (
              <button
                key={f.id}
                onClick={() => toggleSubFilter(f.id)}
                className={`px-3 py-1.5 rounded-full text-[11px] font-mono transition-all duration-200 border ${
                  active
                    ? "bg-accent/15 text-accent border-accent/40 shadow-sm shadow-accent/10"
                    : "bg-card-bg/40 text-muted/70 border-card-border/50 hover:border-accent/20 hover:text-muted"
                }`}
              >
                <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${active ? "bg-accent" : "bg-muted/30"}`} />
                {f.label}
              </button>
            );
          })}
        </div>

        {/* Compare bar */}
        {selected.size >= 2 && (
          <div className="flex items-center justify-center mb-6">
            <button
              onClick={() => setShowCompare(true)}
              className="btn-gradient text-white px-6 py-2.5 rounded-xl text-sm font-medium shadow-md shadow-accent/10 transition-all hover:shadow-lg hover:shadow-accent/20"
            >
              Compare Selected ({selected.size})
            </button>
            <button
              onClick={() => setSelected(new Set())}
              className="ml-3 text-xs text-muted hover:text-foreground transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        {(loading || typeLoading) ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-muted text-sm mb-4">No services found.</p>
            <button
              onClick={() => { setCategory("All"); setSearch(""); setActiveSubFilters(new Set()); }}
              className="text-accent text-sm hover:text-accent-hover transition-colors"
            >
              Clear filters
            </button>
          </div>
        ) : (
          /* Table */
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" role="table" aria-label="AEO Leaderboard rankings">
                <thead>
                  <tr className="border-b border-card-border/50 text-left text-xs text-muted uppercase tracking-wider">
                    {/* Compare checkbox header */}
                    <th className="px-3 py-4 w-8">
                      <span className="sr-only">Compare</span>
                    </th>
                    <th className="px-3 py-4 w-10">#</th>
                    <th
                      className="px-4 py-4 cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort("name")}
                    >
                      <span className="inline-flex items-center">
                        Service
                        <SortArrow active={sortKey === "name"} dir={sortDir} />
                      </span>
                    </th>
                    <th
                      className="px-4 py-4 text-center w-20 cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => handleSort("score")}
                    >
                      <span className="inline-flex items-center justify-center">
                        Score
                        <SortArrow active={sortKey === "score"} dir={sortDir} />
                      </span>
                    </th>
                    <th className="px-4 py-4 text-center w-28">Rating</th>
                    {/* Dimension score columns */}
                    <th
                      className="px-2 py-4 text-center w-14 cursor-pointer select-none hover:text-foreground transition-colors hidden md:table-cell"
                      onClick={() => handleSort("api")}
                      title="API Accessibility"
                    >
                      <span className="inline-flex items-center justify-center">
                        API
                        <SortArrow active={sortKey === "api"} dir={sortDir} />
                      </span>
                    </th>
                    <th
                      className="px-2 py-4 text-center w-14 cursor-pointer select-none hover:text-foreground transition-colors hidden md:table-cell"
                      onClick={() => handleSort("data")}
                      title="Data Structuring"
                    >
                      <span className="inline-flex items-center justify-center">
                        Data
                        <SortArrow active={sortKey === "data"} dir={sortDir} />
                      </span>
                    </th>
                    <th
                      className="px-2 py-4 text-center w-14 cursor-pointer select-none hover:text-foreground transition-colors hidden md:table-cell"
                      onClick={() => handleSort("agent")}
                      title="Agent Compatibility"
                    >
                      <span className="inline-flex items-center justify-center">
                        Agent
                        <SortArrow active={sortKey === "agent"} dir={sortDir} />
                      </span>
                    </th>
                    <th
                      className="px-2 py-4 text-center w-14 cursor-pointer select-none hover:text-foreground transition-colors hidden md:table-cell"
                      onClick={() => handleSort("trust")}
                      title="Trust Signals"
                    >
                      <span className="inline-flex items-center justify-center">
                        Trust
                        <SortArrow active={sortKey === "trust"} dir={sortDir} />
                      </span>
                    </th>
                    <th className="px-4 py-4 hidden lg:table-cell min-w-[280px]">
                      Dimensions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item, idx) => {
                    const isSelected = selected.has(item.scan_id);
                    return (
                      <tr
                        key={item.scan_id}
                        className={`border-b border-card-border/30 cursor-pointer transition-all duration-200 group ${
                          isSelected ? "bg-accent/5 border-accent/20" :
                          idx === 0 ? "rank-gold-row hover:bg-yellow-500/5" :
                          idx === 1 ? "rank-silver-row hover:bg-gray-400/5" :
                          idx === 2 ? "rank-bronze-row hover:bg-orange-500/5" :
                          "hover:bg-card-border/10"
                        }`}
                      >
                        {/* Compare checkbox */}
                        <td className="px-3 py-4" onClick={(e) => e.stopPropagation()}>
                          <label className="flex items-center justify-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelected(item.scan_id)}
                              disabled={!isSelected && selected.size >= 3}
                              className="w-3.5 h-3.5 rounded border-card-border bg-card-bg/60 text-accent focus:ring-accent/30 focus:ring-offset-0 cursor-pointer disabled:opacity-30 accent-[var(--accent)]"
                            />
                          </label>
                        </td>

                        {/* Rank */}
                        <td className="px-3 py-4" onClick={() => handleRowClick(item)}>
                          <RankBadge rank={idx + 1} />
                        </td>

                        {/* Service name + URL + type badge */}
                        <td className="px-4 py-4" onClick={() => item.profile_id ? router.push(`/service/${item.profile_id}`) : handleRowClick(item)}>
                          <div className="flex items-center gap-2">
                            <span className="font-medium group-hover:text-accent transition-colors">
                              {item.service_name}
                            </span>
                            {item.service_type && item.service_type !== "general" && (
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider border ${TYPE_BADGE_STYLES[item.service_type] || TYPE_BADGE_STYLES.general}`}>
                                {TYPE_LABELS[item.service_type] || item.service_type}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-muted font-mono truncate max-w-[200px]">
                            {item.url.replace(/^https?:\/\//, "")}
                          </div>
                        </td>

                        {/* Score */}
                        <td className="px-4 py-4 text-center" onClick={() => handleRowClick(item)}>
                          <span
                            className={`font-mono font-bold text-lg ${scoreColor(item.clarvia_score)}`}
                            aria-label={`Score: ${item.clarvia_score} out of 100`}
                          >
                            {item.clarvia_score}
                          </span>
                        </td>

                        {/* Rating badge */}
                        <td className="px-4 py-4 text-center" onClick={() => handleRowClick(item)}>
                          <span
                            className={`inline-block px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase tracking-wider ${ratingBadgeClass(item.rating)}`}
                          >
                            {item.rating}
                          </span>
                        </td>

                        {/* Dimension score mini columns */}
                        <td
                          className="px-2 py-4 text-center hidden md:table-cell"
                          onClick={() => handleRowClick(item)}
                        >
                          <span className={`font-mono text-xs font-semibold ${dimScoreColor(item.dimensions?.api_accessibility?.score ?? 0, item.dimensions?.api_accessibility?.max ?? 30)}`} aria-label={`API: ${item.dimensions?.api_accessibility?.score ?? 0} out of ${item.dimensions?.api_accessibility?.max ?? 30}`}>
                            {item.dimensions?.api_accessibility?.score ?? 0}
                          </span>
                        </td>
                        <td
                          className="px-2 py-4 text-center hidden md:table-cell"
                          onClick={() => handleRowClick(item)}
                        >
                          <span className={`font-mono text-xs font-semibold ${dimScoreColor(item.dimensions?.data_structuring?.score ?? 0, item.dimensions?.data_structuring?.max ?? 25)}`} aria-label={`Data: ${item.dimensions?.data_structuring?.score ?? 0} out of ${item.dimensions?.data_structuring?.max ?? 25}`}>
                            {item.dimensions?.data_structuring?.score ?? 0}
                          </span>
                        </td>
                        <td
                          className="px-2 py-4 text-center hidden md:table-cell"
                          onClick={() => handleRowClick(item)}
                        >
                          <span className={`font-mono text-xs font-semibold ${dimScoreColor(item.dimensions?.agent_compatibility?.score ?? 0, item.dimensions?.agent_compatibility?.max ?? 25)}`} aria-label={`Agent: ${item.dimensions?.agent_compatibility?.score ?? 0} out of ${item.dimensions?.agent_compatibility?.max ?? 25}`}>
                            {item.dimensions?.agent_compatibility?.score ?? 0}
                          </span>
                        </td>
                        <td
                          className="px-2 py-4 text-center hidden md:table-cell"
                          onClick={() => handleRowClick(item)}
                        >
                          <span className={`font-mono text-xs font-semibold ${dimScoreColor(item.dimensions?.trust_signals?.score ?? 0, item.dimensions?.trust_signals?.max ?? 20)}`} aria-label={`Trust: ${item.dimensions?.trust_signals?.score ?? 0} out of ${item.dimensions?.trust_signals?.max ?? 20}`}>
                            {item.dimensions?.trust_signals?.score ?? 0}
                          </span>
                        </td>

                        {/* Dimension bars */}
                        <td className="px-4 py-4 hidden lg:table-cell" onClick={() => handleRowClick(item)}>
                          <div className="space-y-1">
                            <DimMiniBar
                              label="API"
                              score={item.dimensions?.api_accessibility?.score ?? 0}
                              max={item.dimensions?.api_accessibility?.max ?? 30}
                            />
                            <DimMiniBar
                              label="Data"
                              score={item.dimensions?.data_structuring?.score ?? 0}
                              max={item.dimensions?.data_structuring?.max ?? 25}
                            />
                            <DimMiniBar
                              label="Agent"
                              score={item.dimensions?.agent_compatibility?.score ?? 0}
                              max={item.dimensions?.agent_compatibility?.max ?? 25}
                            />
                            <DimMiniBar
                              label="Trust"
                              score={item.dimensions?.trust_signals?.score ?? 0}
                              max={item.dimensions?.trust_signals?.max ?? 20}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Stats bar */}
        {!loading && filtered.length > 0 && (
          <div className="flex items-center justify-between mt-6 text-xs text-muted">
            <span>{filtered.length} services</span>
            <span>Average score: {Math.round(filtered.reduce((sum, s) => sum + s.clarvia_score, 0) / filtered.length)}</span>
          </div>
        )}

        {/* CTA */}
        <div className="text-center mt-16 mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 btn-gradient text-white px-8 py-3.5 rounded-xl font-medium text-sm group"
          >
            Scan your service
            <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </Link>
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
            <span className="text-muted/50 cursor-default" title="Coming soon">Terms</span>
            <Link href="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
          </div>
        </div>
      </footer>

      {/* Compare Modal */}
      {showCompare && compareItems.length >= 2 && (
        <CompareModal items={compareItems} onClose={() => setShowCompare(false)} />
      )}
    </div>
  );
}
