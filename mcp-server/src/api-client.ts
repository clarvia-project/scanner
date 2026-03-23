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
