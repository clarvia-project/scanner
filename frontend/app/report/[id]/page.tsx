"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
      // Retry a few times since webhook might be delayed
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
            // Payment not yet confirmed, wait and retry
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
    <div className="flex flex-col min-h-screen">
      <header className="border-b border-card-border px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="font-mono text-sm tracking-widest text-muted uppercase hover:text-foreground transition-colors"
          >
            Clarvia
          </Link>
          <span className="text-xs text-muted">Detailed Report</span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10">
        {loading && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <p className="text-muted text-sm">
              Confirming payment and generating your report...
            </p>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
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
          <div className="space-y-8">
            <div className="text-center space-y-2">
              <p className="text-score-green text-sm font-mono">
                Payment confirmed
              </p>
              <h1 className="text-2xl font-bold">
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
                className="bg-accent hover:bg-accent-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
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
            <div className="bg-card-bg border border-card-border rounded-lg px-5 py-4">
              <p className="text-sm text-muted">
                Your full report has been generated. Download the PDF above for
                the complete analysis including all 13 sub-factors, 15
                recommendations, and competitive benchmarks.
              </p>
            </div>

            <div className="text-center">
              <Link
                href={`/scan/${scanId}`}
                className="text-accent hover:text-accent-hover text-sm transition-colors"
              >
                View free scan results
              </Link>
            </div>
          </div>
        )}
      </main>

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
