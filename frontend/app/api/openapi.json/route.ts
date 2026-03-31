import { type NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// Proxy the OpenAPI spec from the backend API to clarvia.art/api/openapi.json
// This enables autonomous agents to discover Clarvia's API at the canonical domain.
export async function GET(_req: NextRequest) {
  try {
    const res = await fetch(`${API_BASE}/openapi.json`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 3600 },
    });

    if (res.ok) {
      const spec = await res.json();
      return NextResponse.json(spec, {
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    return new NextResponse("Failed to fetch OpenAPI spec", { status: 502 });
  } catch {
    return new NextResponse("OpenAPI spec unavailable", { status: 503 });
  }
}
