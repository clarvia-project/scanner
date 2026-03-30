const BASE_URL = "https://clarvia-api.onrender.com";

// --- In-memory cache with 5-minute TTL ---

interface CacheEntry<T = unknown> {
  data: T;
  expiresAt: number;
}

const cache = new Map<string, CacheEntry>();
const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

function cacheGet<T>(key: string): T | undefined {
  const entry = cache.get(key);
  if (!entry) return undefined;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return undefined;
  }
  return entry.data as T;
}

function cacheSet<T>(key: string, data: T, ttlMs: number = DEFAULT_TTL_MS): void {
  // Evict expired entries when cache grows large (simple GC)
  if (cache.size > 500) {
    const now = Date.now();
    for (const [k, v] of cache) {
      if (now > v.expiresAt) cache.delete(k);
    }
  }
  cache.set(key, { data, expiresAt: Date.now() + ttlMs });
}

// --- HTTP request layer ---

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
  /** Set to false to skip cache for this request (default: true for GET) */
  useCache?: boolean;
  /** Override TTL for this request in ms */
  cacheTtlMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, useCache = true, cacheTtlMs } = options;

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

  // Only cache GET requests (reads); POST requests always go through
  const isGetRequest = method === "GET";
  if (isGetRequest && useCache) {
    const cached = cacheGet<T>(url);
    if (cached !== undefined) {
      return cached;
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "User-Agent": "clarvia-mcp-server/1.1.2",
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

  const data = (await res.json()) as T;

  // Cache successful GET responses
  if (isGetRequest && useCache) {
    cacheSet(url, data, cacheTtlMs);
  }

  return data;
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
  service_type?: string;
  min_score?: number;
  limit?: number;
}): Promise<Service[]> {
  return request<Service[]>("/v1/services", {
    params: {
      q: params.query,
      category: params.category,
      service_type: params.service_type,
      min_score: params.min_score,
      limit: params.limit,
    },
  });
}

export interface FeedbackResult {
  status: string;
  total_feedback: number;
}

export async function submitFeedback(params: {
  profile_id: string;
  outcome: "success" | "failure" | "partial";
  agent_id?: string;
  error_message?: string;
  latency_ms?: number;
}): Promise<FeedbackResult> {
  return request<FeedbackResult>("/v1/feedback", {
    method: "POST",
    body: params,
  });
}

export async function scanService(url: string): Promise<ScanResult> {
  // Scan results are POST but idempotent — cache by URL
  const cacheKey = `scan:${url}`;
  const cached = cacheGet<ScanResult>(cacheKey);
  if (cached) return cached;

  const result = await request<ScanResult>("/api/scan", {
    method: "POST",
    body: { url },
    useCache: false,
  });
  cacheSet(cacheKey, result);
  return result;
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
  // Probe results are POST but idempotent — cache with shorter TTL (2 min)
  const cacheKey = `probe:${url}`;
  const cached = cacheGet<ProbeResult>(cacheKey);
  if (cached) return cached;

  const result = await request<ProbeResult>("/api/v1/accessibility-probe", {
    method: "POST",
    body: { url },
    useCache: false,
  });
  cacheSet(cacheKey, result, 2 * 60 * 1000); // 2 min TTL for probes (more real-time)
  return result;
}

// --- Setup comparison API ---

export interface SetupTool {
  name: string;
  input_name: string;
  score: number | null;
  category: string;
  rank_in_category: number | null;
  scan_id: string | null;
}

export interface RegisterSetupResult {
  setup_id: string;
  tools: SetupTool[];
  summary: {
    total: number;
    matched: number;
    unmatched: number;
    avg_score: number;
  };
}

export interface CompareResult {
  setup_id: string;
  comparisons: Array<{
    current: { name: string; score: number | null; rank?: number; status?: string };
    better_alternatives: Array<{ name: string; score: number; scan_id: string }>;
    category: string;
    category_avg: number | null;
    upgrade_potential?: boolean;
  }>;
  summary: { total_tools: number; upgradable: number };
}

export interface RecommendResult {
  setup_id: string;
  recommendations: Array<{
    name: string;
    score: number;
    category: string;
    scan_id: string;
    reason: string;
  }>;
  based_on_categories: string[];
}

export async function registerSetup(
  tools: string[],
  setupId?: string,
): Promise<RegisterSetupResult> {
  return request<RegisterSetupResult>("/v1/setup/register", {
    method: "POST",
    body: { tools, setup_id: setupId },
  });
}

export async function compareSetup(setupId: string): Promise<CompareResult> {
  return request<CompareResult>(`/v1/setup/${encodeURIComponent(setupId)}/compare`);
}

// --- CS (Customer Support) API ---

export interface CreateTicketResult {
  ticket_id: string;
  status: string;
  message: string;
  track_url: string;
}

export async function createCSTicket(params: {
  type: "bug" | "feature" | "question" | "security";
  title: string;
  description: string;
  agent_id?: string;
  service_url?: string;
  severity?: string;
  metadata?: Record<string, unknown>;
}): Promise<CreateTicketResult> {
  return request<CreateTicketResult>("/v1/cs/tickets", {
    method: "POST",
    body: params,
  });
}

export interface TicketListResult {
  total: number;
  tickets: Array<{
    ticket_id: string;
    type: string;
    title: string;
    status: string;
    severity: string;
    created_at: string;
  }>;
}

export async function listCSTickets(params?: {
  type?: string;
  status?: string;
  agent_id?: string;
}): Promise<TicketListResult> {
  return request<TicketListResult>("/v1/cs/tickets", {
    params: params as Record<string, string | undefined>,
  });
}

export interface TopPick {
  name: string;
  url: string;
  score: number;
  rating: string;
  category: string;
  scan_id: string;
  description: string;
}

export interface TopPicksResult {
  top_picks: TopPick[];
  by_category: Record<string, TopPick[]>;
  total: number;
  threshold: number;
}

export async function getTopPicks(params?: {
  category?: string;
  limit?: number;
}): Promise<TopPicksResult> {
  return request<TopPicksResult>("/v1/featured/top", {
    params: {
      category: params?.category,
      limit: params?.limit,
    },
  });
}

export async function recommendForSetup(
  setupId: string,
  limit: number = 10,
): Promise<RecommendResult> {
  return request<RecommendResult>(`/v1/setup/${encodeURIComponent(setupId)}/recommend`, {
    params: { limit },
  });
}
