"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { API_BASE } from "@/lib/api";
import Nav from "@/app/components/Nav";

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const scanId = params.id as string;
  const sessionId = searchParams.get("session_id");

  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!scanId) return;

    async function fetchReport() {
      let attempts = 0;
      while (attempts < 5) {
        try {
          const res = await fetch(`${API_BASE}/api/report/${scanId}`);
          if (res.ok) {
            const data = await res.json();
            setReport(data);
            setLoading(false);
            return;
          }
          if (res.status === 402) {
            attempts++;
            await new Promise((r) => setTimeout(r, 2000));
            continue;
          }
          throw new Error(`Failed to load report (${res.status})`);
        } catch (err) {
          if (attempts >= 4) {
            setError(
              err instanceof Error ? err.message : "Failed to load report"
            );
            setLoading(false);
            return;
          }
          attempts++;
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    }

    fetchReport();
  }, [scanId]);

  return (
    <div className="flex flex-col min-h-screen bg-gradient-mesh">
      <Nav />

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
        {loading && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center glow-accent">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-muted text-sm">
              Confirming payment and generating your report...
            </p>
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
              href={`/scan/${scanId}`}
              className="text-accent hover:text-accent-hover text-sm transition-colors"
            >
              Back to scan results
            </Link>
          </div>
        )}

        {report && (
          <div className="space-y-10">
            <div className="text-center space-y-4">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-score-green/20 bg-score-green/5 text-xs text-score-green font-medium">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Payment confirmed
              </div>
              <h1 className="text-3xl font-bold">
                {(report as Record<string, unknown>).service_name as string} — Full Report
              </h1>
              <p className="text-sm text-muted font-mono">
                {(report as Record<string, unknown>).url as string}
              </p>
            </div>

            {/* Download PDF */}
            <div className="flex justify-center">
              <a
                href={`${API_BASE}/api/report/${scanId}/pdf`}
                className="btn-gradient text-white px-8 py-4 rounded-xl text-sm font-medium transition-colors inline-flex items-center gap-3 group"
              >
                <svg
                  className="w-5 h-5 group-hover:-translate-y-0.5 transition-transform"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Download PDF Report
              </a>
            </div>

            {/* Report content preview */}
            <div className="glass-card rounded-2xl px-7 py-6">
              <p className="text-sm text-muted">
                Your full report has been generated. Download the PDF above for
                the complete analysis including all 13 sub-factors, 15
                recommendations, and competitive benchmarks.
              </p>
            </div>

            <div className="text-center">
              <Link
                href={`/scan/${scanId}`}
                className="inline-flex items-center gap-2 text-accent hover:text-accent-hover text-sm transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
                </svg>
                View free scan results
              </Link>
            </div>
          </div>
        )}
      </main>

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
