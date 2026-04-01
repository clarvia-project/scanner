/**
 * Central API configuration.
 *
 * All frontend files should import API_BASE from here
 * instead of declaring it locally.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

export interface RecommendResult {
  name: string;
  scan_id: string;
  url: string;
  description: string;
  category: string;
  service_type: string;
  clarvia_score: number;
  rating: string;
  relevance_score: number;
  combined_score: number;
  match_reason: string;
  install_hint: string | null;
  tags: string[];
}

export interface RecommendResponse {
  intent_parsed: { original: string; expanded_terms: string[] };
  recommendations: RecommendResult[];
  total_candidates: number;
  method: string;
}

/** Strip HTML tags from a string and decode common entities */
export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export async function recommendTools(
  intent: string,
  filters?: { service_type?: string; category?: string; min_score?: number },
  limit = 10
): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/v1/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, filters, limit }),
  });
  if (!res.ok) throw new Error("Recommendation failed");
  return res.json();
}
