"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface KpiData {
  timestamp: string;
  uptime_seconds: number;
  traffic: {
    total_requests: number;
    unique_visitors: number;
    agent_requests: number;
    human_requests: number;
    bot_requests: number;
    agent_ratio: number;
  };
  agents: {
    breakdown: { name: string; requests: number }[];
    unique_agents: number;
  };
  scans: { total: number; unique_urls: number };
  mcp: {
    total_calls: number;
    by_tool: { tool: string; calls: number }[];
  };
  api_usage: {
    top_endpoints: { endpoint: string; calls: number }[];
  };
  performance: {
    avg_response_ms: number;
    p95_response_ms: number;
    error_count: number;
    error_rate: number;
    by_status: Record<string, number>;
  };
  hourly: {
    requests: { hour: string; count: number }[];
    agents: { hour: string; count: number }[];
    scans: { hour: string; count: number }[];
  };
  daily: {
    requests: { date: string; count: number }[];
    agents: { date: string; count: number }[];
    scans: { date: string; count: number }[];
    unique_visitors: { date: string; count: number }[];
  };
  recent_errors: {
    path: string;
    method: string;
    status: number;
    ip: string;
    agent: string | null;
    ts: string;
  }[];
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatUptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return [d && `${d}d`, h && `${h}h`, `${m}m`].filter(Boolean).join(" ");
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-2 w-full rounded-full bg-white/5">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function SparkLine({ data, color = "stroke-accent" }: { data: number[]; color?: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data, 1);
  const w = 160;
  const h = 40;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - (v / max) * (h - 4);
    return `${x},${y}`;
  });
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-10" preserveAspectRatio="none">
      <polyline
        points={points.join(" ")}
        fill="none"
        className={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Components                                                          */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
  sub,
  spark,
}: {
  label: string;
  value: string;
  sub?: string;
  spark?: number[];
}) {
  return (
    <div className="rounded-xl border border-card-border bg-card-bg p-4 flex flex-col gap-2">
      <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
      <span className="text-2xl font-bold text-foreground">{value}</span>
      {sub && <span className="text-xs text-muted">{sub}</span>}
      {spark && spark.length > 1 && <SparkLine data={spark} />}
    </div>
  );
}

function AgentTable({ data }: { data: { name: string; requests: number }[] }) {
  const max = data[0]?.requests ?? 1;
  return (
    <div className="space-y-2">
      {data.map((a) => (
        <div key={a.name} className="flex items-center gap-3">
          <span className="w-28 text-sm text-foreground truncate">{a.name}</span>
          <div className="flex-1">
            <MiniBar value={a.requests} max={max} color="bg-accent" />
          </div>
          <span className="text-xs text-muted w-14 text-right">{formatNum(a.requests)}</span>
        </div>
      ))}
    </div>
  );
}

function EndpointTable({ data }: { data: { endpoint: string; calls: number }[] }) {
  const max = data[0]?.calls ?? 1;
  return (
    <div className="space-y-1.5">
      {data.slice(0, 12).map((ep) => (
        <div key={ep.endpoint} className="flex items-center gap-2">
          <code className="w-48 text-xs text-muted truncate">{ep.endpoint}</code>
          <div className="flex-1">
            <MiniBar value={ep.calls} max={max} color="bg-score-green" />
          </div>
          <span className="text-xs text-muted w-12 text-right">{formatNum(ep.calls)}</span>
        </div>
      ))}
    </div>
  );
}

function ErrorList({ errors }: { errors: KpiData["recent_errors"] }) {
  if (errors.length === 0) return <p className="text-xs text-muted">No recent errors</p>;
  return (
    <div className="space-y-1 max-h-48 overflow-y-auto">
      {errors.map((e, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span
            className={`px-1.5 py-0.5 rounded font-mono ${
              e.status >= 500 ? "bg-score-red/20 text-score-red" : "bg-score-yellow/20 text-score-yellow"
            }`}
          >
            {e.status}
          </span>
          <span className="text-muted">{e.method}</span>
          <code className="text-foreground truncate flex-1">{e.path}</code>
          {e.agent && (
            <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent text-[10px]">
              {e.agent}
            </span>
          )}
          <span className="text-muted text-[10px] shrink-0">
            {new Date(e.ts).toLocaleTimeString()}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function AdminDashboard() {
  const [apiKey, setApiKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchKpi = useCallback(async (key: string) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/admin/kpi`, {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setAuthenticated(false);
          setError("Invalid API key");
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setKpi(data);
      setError("");
      setAuthenticated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch KPI data");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh every 30s
  useEffect(() => {
    if (!authenticated || !autoRefresh) return;
    const interval = setInterval(() => fetchKpi(apiKey), 30_000);
    return () => clearInterval(interval);
  }, [authenticated, autoRefresh, apiKey, fetchKpi]);

  // Persist API key in sessionStorage
  useEffect(() => {
    const saved = sessionStorage.getItem("clarvia_admin_key");
    if (saved) {
      setApiKey(saved);
      fetchKpi(saved);
    }
  }, [fetchKpi]);

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    sessionStorage.setItem("clarvia_admin_key", apiKey);
    fetchKpi(apiKey);
  }

  // Login screen
  if (!authenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <form onSubmit={handleLogin} className="w-full max-w-sm space-y-4 p-6">
          <h1 className="text-xl font-bold text-foreground text-center">Clarvia Admin</h1>
          <input
            type="password"
            placeholder="Admin API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-card-bg border border-card-border text-foreground placeholder:text-muted focus:outline-none focus:border-accent"
          />
          {error && <p className="text-sm text-score-red text-center">{error}</p>}
          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-accent text-white font-medium hover:bg-accent-hover transition"
          >
            Access Dashboard
          </button>
        </form>
      </div>
    );
  }

  if (!kpi) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted">Loading KPI data...</div>
      </div>
    );
  }

  const hourlyReqData = kpi.hourly.requests.map((h) => h.count);
  const hourlyAgentData = kpi.hourly.agents.map((h) => h.count);
  const hourlyScanData = kpi.hourly.scans.map((h) => h.count);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="border-b border-card-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold">Clarvia KPI</h1>
          <span className="text-xs text-muted">
            Uptime: {formatUptime(kpi.uptime_seconds)}
          </span>
          {loading && (
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-accent"
            />
            Auto-refresh 30s
          </label>
          <button
            onClick={() => fetchKpi(apiKey)}
            className="px-3 py-1.5 text-xs rounded-lg border border-card-border hover:bg-card-bg transition"
          >
            Refresh
          </button>
          <button
            onClick={() => {
              setAuthenticated(false);
              sessionStorage.removeItem("clarvia_admin_key");
            }}
            className="px-3 py-1.5 text-xs rounded-lg border border-card-border text-score-red hover:bg-score-red/10 transition"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Row 1: Key metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <StatCard
            label="Total Requests"
            value={formatNum(kpi.traffic.total_requests)}
            spark={hourlyReqData}
          />
          <StatCard
            label="Unique Visitors"
            value={formatNum(kpi.traffic.unique_visitors)}
          />
          <StatCard
            label="Agent Requests"
            value={formatNum(kpi.traffic.agent_requests)}
            sub={`${kpi.traffic.agent_ratio}% of traffic`}
            spark={hourlyAgentData}
          />
          <StatCard
            label="Total Scans"
            value={formatNum(kpi.scans.total)}
            sub={`${formatNum(kpi.scans.unique_urls)} unique URLs`}
            spark={hourlyScanData}
          />
          <StatCard
            label="MCP Calls"
            value={formatNum(kpi.mcp.total_calls)}
          />
          <StatCard
            label="Avg Response"
            value={`${kpi.performance.avg_response_ms}ms`}
            sub={`P95: ${kpi.performance.p95_response_ms}ms`}
          />
        </div>

        {/* Row 2: Agent breakdown + API usage */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Agent breakdown */}
          <div className="rounded-xl border border-card-border bg-card-bg p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">
                Agent Breakdown
              </h2>
              <span className="text-xs text-muted">
                {kpi.agents.unique_agents} unique agents
              </span>
            </div>
            {kpi.agents.breakdown.length > 0 ? (
              <AgentTable data={kpi.agents.breakdown} />
            ) : (
              <p className="text-xs text-muted">No agent traffic yet</p>
            )}
          </div>

          {/* API usage */}
          <div className="rounded-xl border border-card-border bg-card-bg p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
              Top Endpoints
            </h2>
            {kpi.api_usage.top_endpoints.length > 0 ? (
              <EndpointTable data={kpi.api_usage.top_endpoints} />
            ) : (
              <p className="text-xs text-muted">No API calls yet</p>
            )}
          </div>
        </div>

        {/* Row 3: MCP tools + Status codes + Errors */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* MCP tool calls */}
          <div className="rounded-xl border border-card-border bg-card-bg p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
              MCP Tool Calls
            </h2>
            {kpi.mcp.by_tool.length > 0 ? (
              <div className="space-y-2">
                {kpi.mcp.by_tool.map((t) => (
                  <div key={t.tool} className="flex justify-between text-sm">
                    <code className="text-muted truncate">{t.tool}</code>
                    <span className="text-foreground">{formatNum(t.calls)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted">No MCP calls yet</p>
            )}
          </div>

          {/* Status codes */}
          <div className="rounded-xl border border-card-border bg-card-bg p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
              Status Codes
            </h2>
            <div className="space-y-2">
              {Object.entries(kpi.performance.by_status)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([code, count]) => (
                  <div key={code} className="flex items-center gap-2">
                    <span
                      className={`w-10 text-center text-xs font-mono px-1.5 py-0.5 rounded ${
                        Number(code) < 300
                          ? "bg-score-green/20 text-score-green"
                          : Number(code) < 400
                          ? "bg-accent/20 text-accent"
                          : Number(code) < 500
                          ? "bg-score-yellow/20 text-score-yellow"
                          : "bg-score-red/20 text-score-red"
                      }`}
                    >
                      {code}
                    </span>
                    <div className="flex-1">
                      <MiniBar
                        value={count}
                        max={kpi.traffic.total_requests}
                        color={
                          Number(code) < 300
                            ? "bg-score-green"
                            : Number(code) < 500
                            ? "bg-score-yellow"
                            : "bg-score-red"
                        }
                      />
                    </div>
                    <span className="text-xs text-muted w-12 text-right">{formatNum(count)}</span>
                  </div>
                ))}
            </div>
            <div className="mt-3 pt-3 border-t border-card-border flex justify-between text-xs">
              <span className="text-muted">Error rate</span>
              <span
                className={
                  kpi.performance.error_rate > 5
                    ? "text-score-red"
                    : kpi.performance.error_rate > 1
                    ? "text-score-yellow"
                    : "text-score-green"
                }
              >
                {kpi.performance.error_rate}%
              </span>
            </div>
          </div>

          {/* Recent errors */}
          <div className="rounded-xl border border-card-border bg-card-bg p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
              Recent Errors
            </h2>
            <ErrorList errors={kpi.recent_errors} />
          </div>
        </div>

        {/* Row 4: Daily trends */}
        <div className="rounded-xl border border-card-border bg-card-bg p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
            Daily Trends (30d)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <span className="text-xs text-muted">Requests</span>
              <SparkLine data={kpi.daily.requests.map((d) => d.count)} />
              <div className="flex justify-between text-[10px] text-muted mt-1">
                <span>{kpi.daily.requests[0]?.date?.slice(5) ?? ""}</span>
                <span>{kpi.daily.requests.at(-1)?.date?.slice(5) ?? ""}</span>
              </div>
            </div>
            <div>
              <span className="text-xs text-muted">Agent Traffic</span>
              <SparkLine
                data={kpi.daily.agents.map((d) => d.count)}
                color="stroke-score-green"
              />
              <div className="flex justify-between text-[10px] text-muted mt-1">
                <span>{kpi.daily.agents[0]?.date?.slice(5) ?? ""}</span>
                <span>{kpi.daily.agents.at(-1)?.date?.slice(5) ?? ""}</span>
              </div>
            </div>
            <div>
              <span className="text-xs text-muted">Scans</span>
              <SparkLine
                data={kpi.daily.scans.map((d) => d.count)}
                color="stroke-score-yellow"
              />
              <div className="flex justify-between text-[10px] text-muted mt-1">
                <span>{kpi.daily.scans[0]?.date?.slice(5) ?? ""}</span>
                <span>{kpi.daily.scans.at(-1)?.date?.slice(5) ?? ""}</span>
              </div>
            </div>
            <div>
              <span className="text-xs text-muted">Unique Visitors</span>
              <SparkLine
                data={kpi.daily.unique_visitors.map((d) => d.count)}
                color="stroke-[#a78bfa]"
              />
              <div className="flex justify-between text-[10px] text-muted mt-1">
                <span>{kpi.daily.unique_visitors[0]?.date?.slice(5) ?? ""}</span>
                <span>{kpi.daily.unique_visitors.at(-1)?.date?.slice(5) ?? ""}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-muted py-4">
          Last updated: {new Date(kpi.timestamp).toLocaleString()} | Data resets on server restart
        </div>
      </main>
    </div>
  );
}
