const BASE_URL = "https://clarvia-api.onrender.com";

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params } = options;

  let url = `${BASE_URL}${path}`;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "User-Agent": "clarvia-mcp-server/1.0",
  };

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Clarvia API error ${res.status}: ${text || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

// --- Service types ---

export interface Service {
  id?: string;
  name: string;
  url: string;
  score?: number;
  rating?: string;
  category?: string;
  description?: string;
}

export interface ScanResult {
  scan_id?: string;
  clarvia_score: number;
  rating: string;
  dimensions?: Record<string, unknown>;
  recommendations?: string[];
  [key: string]: unknown;
}

export interface ServiceDetails {
  [key: string]: unknown;
}

export interface Category {
  name: string;
  count: number;
  [key: string]: unknown;
}

export interface Stats {
  total_services?: number;
  average_score?: number;
  [key: string]: unknown;
}

export interface RegisterResult {
  profile_id?: string;
  status?: string;
  [key: string]: unknown;
}

// --- API functions ---

export async function searchServices(params: {
  query?: string;
  category?: string;
  min_score?: number;
  limit?: number;
}): Promise<Service[]> {
  return request<Service[]>("/v1/services", {
    params: {
      q: params.query,
      category: params.category,
      min_score: params.min_score,
      limit: params.limit,
    },
  });
}

export async function scanService(url: string): Promise<ScanResult> {
  return request<ScanResult>("/api/scan", {
    method: "POST",
    body: { url },
  });
}

export async function getServiceDetails(scanId: string): Promise<ServiceDetails> {
  return request<ServiceDetails>(`/v1/services/${encodeURIComponent(scanId)}`);
}

export async function listCategories(): Promise<Category[]> {
  return request<Category[]>("/v1/categories");
}

export async function getStats(): Promise<Stats> {
  return request<Stats>("/v1/stats");
}

export async function registerService(params: {
  name: string;
  url: string;
  description: string;
  category: string;
  github_url?: string;
}): Promise<RegisterResult> {
  return request<RegisterResult>("/v1/profiles", {
    method: "POST",
    body: params,
  });
}

// --- v2 API functions ---

export interface GateCheckResult {
  url: string;
  score: number;
  rating: string;
  agent_grade: "AGENT_NATIVE" | "AGENT_FRIENDLY" | "AGENT_POSSIBLE" | "AGENT_HOSTILE";
  pass: boolean;
  reason: string;
  alternatives?: Service[];
}

export interface BatchCheckResult {
  results: GateCheckResult[];
  checked_at: string;
}

export interface ProbeResult {
  url: string;
  reachable: boolean;
  response_time_ms: number;
  has_openapi: boolean;
  has_mcp: boolean;
  has_agents_json: boolean;
  checks: Record<string, boolean>;
}

function gradeFromScore(score: number): GateCheckResult["agent_grade"] {
  if (score >= 90) return "AGENT_NATIVE";
  if (score >= 70) return "AGENT_FRIENDLY";
  if (score >= 50) return "AGENT_POSSIBLE";
  return "AGENT_HOSTILE";
}

export async function gateCheck(
  url: string,
  minRating: GateCheckResult["agent_grade"] = "AGENT_FRIENDLY",
): Promise<GateCheckResult> {
  const scan = await scanService(url);
  const score = scan.clarvia_score;
  const grade = gradeFromScore(score);

  const gradeOrder = ["AGENT_HOSTILE", "AGENT_POSSIBLE", "AGENT_FRIENDLY", "AGENT_NATIVE"];
  const pass = gradeOrder.indexOf(grade) >= gradeOrder.indexOf(minRating);

  let alternatives: Service[] | undefined;
  if (!pass) {
    try {
      alternatives = await searchServices({ min_score: 70, limit: 5 });
    } catch {
      // ignore
    }
  }

  return {
    url,
    score,
    rating: scan.rating,
    agent_grade: grade,
    pass,
    reason: pass
      ? `Service scored ${score} (${grade}), meets minimum ${minRating}`
      : `Service scored ${score} (${grade}), below minimum ${minRating}. Consider alternatives.`,
    alternatives: pass ? undefined : alternatives,
  };
}

export async function batchCheck(urls: string[]): Promise<BatchCheckResult> {
  const results = await Promise.all(urls.map((u) => gateCheck(u)));
  return {
    results,
    checked_at: new Date().toISOString(),
  };
}

export async function findAlternatives(
  category: string,
  minScore: number = 70,
  limit: number = 10,
): Promise<Service[]> {
  return searchServices({ category, min_score: minScore, limit });
}

export async function probeService(url: string): Promise<ProbeResult> {
  return request<ProbeResult>("/api/v1/accessibility-probe", {
    method: "POST",
    body: { url },
  });
}
