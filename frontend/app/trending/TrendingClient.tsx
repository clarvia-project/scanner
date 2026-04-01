"use client";

import { useState } from "react";
import Link from "next/link";

interface TrendingTool {
  name: string;
  scan_id: string;
  url: string;
  description: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
}

interface CategoryStat {
  count: number;
  avg_score: number;
  top_score: number;
}

export interface TrendingData {
  top_tools: TrendingTool[];
  by_category: Record<string, TrendingTool[]>;
  rising_stars: TrendingTool[];
  service_type_leaders: Record<string, TrendingTool>;
  category_stats: Record<string, CategoryStat>;
  total_indexed: number;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  mcp_server: { label: "MCP", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  api: { label: "API", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  cli_tool: { label: "CLI", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  skill: { label: "Skill", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  general: { label: "General", color: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
};

const CATEGORY_LABELS: Record<string, { label: string }> = {
  ai: { label: "AI / ML" },
  developer_tools: { label: "Dev Tools" },
  communication: { label: "Communication" },
  data: { label: "Data" },
  productivity: { label: "Productivity" },
  blockchain: { label: "Blockchain" },
  payments: { label: "Payments" },
  mcp: { label: "MCP" },
  cli: { label: "CLI" },
  skills: { label: "Skills" },
  search: { label: "Search" },
  storage: { label: "Storage" },
  cms: { label: "CMS" },
  security: { label: "Security" },
  testing: { label: "Testing" },
  monitoring: { label: "Monitoring" },
  database: { label: "Database" },
  cloud: { label: "Cloud" },
  automation: { label: "Automation" },
  media: { label: "Media" },
  analytics: { label: "Analytics" },
  other: { label: "Other" },
};

function scoreColor(score: number) {
  if (score >= 70) return "text-score-green";
  if (score >= 40) return "text-score-yellow";
  return "text-score-red";
}

function ToolCard({ tool, rank }: { tool: TrendingTool; rank?: number }) {
  const typeInfo = TYPE_LABELS[tool.service_type] || TYPE_LABELS.general;
  return (
    <Link
      href={tool.scan_id.startsWith("tool_") ? `/tool/${tool.scan_id}` : `/scan/${tool.scan_id}`}
      className="glass-card rounded-xl p-4 hover:border-accent/30 transition-all group flex flex-col"
    >
      <div className="flex items-start gap-3 mb-2">
        {rank !== undefined && (
          <span className="text-lg font-bold text-muted/30 font-mono w-6 text-right flex-shrink-0">
            {rank}
          </span>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${typeInfo.color}`}>
              {typeInfo.label}
            </span>
            <span className={`text-xs font-mono font-bold ${scoreColor(tool.clarvia_score)}`}>
              {tool.clarvia_score}
            </span>
          </div>
          <h3 className="text-sm font-semibold truncate group-hover:text-accent transition-colors">
            {tool.name}
          </h3>
        </div>
      </div>
      {tool.description && (
        <p className="text-xs text-muted/70 line-clamp-2 leading-relaxed">
          {tool.description}
        </p>
      )}
    </Link>
  );
}

export default function TrendingClient({ data }: { data: TrendingData }) {
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  return (
    <>
      {/* Category Stats Bar */}
      <div className="flex flex-wrap gap-2 mb-8">
        {Object.entries(data.category_stats || {})
          .sort((a, b) => {
            if (a[0] === "other") return 1;
            if (b[0] === "other") return -1;
            return b[1].count - a[1].count;
          })
          .map(([cat, stats]) => {
            const info = CATEGORY_LABELS[cat] || CATEGORY_LABELS.other;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
                className={`glass-subtle px-3 py-2 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${
                  activeCategory === cat ? "ring-1 ring-accent border-accent/30" : ""
                }`}
              >
                <span className="text-foreground font-semibold">{info.label}</span>
                <span className="text-muted/50">{stats.count}</span>
                <span className={`font-bold ${scoreColor(stats.avg_score)}`}>
                  avg {stats.avg_score}
                </span>
              </button>
            );
          })}
      </div>

      {/* Category-filtered view */}
      {activeCategory && data.by_category?.[activeCategory] && (
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Top {CATEGORY_LABELS[activeCategory]?.label || activeCategory}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.by_category[activeCategory].map((tool, idx) => (
              <ToolCard key={tool.scan_id} tool={tool} rank={idx + 1} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
