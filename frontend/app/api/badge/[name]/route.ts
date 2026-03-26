import { type NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";

// Proxy to backend badge generator, which has full prebuilt-scans lookup.
// This route makes https://clarvia.art/api/badge/{name} the canonical badge URL.
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const { searchParams } = req.nextUrl;

  // Forward style/label/compact query params to backend
  const qs = searchParams.toString();
  const backendUrl = `${API_BASE}/api/badge/${encodeURIComponent(name)}${qs ? `?${qs}` : ""}`;

  try {
    const res = await fetch(backendUrl, {
      headers: { Accept: "image/svg+xml" },
      next: { revalidate: 3600 },
    });

    if (res.ok) {
      const svg = await res.text();
      return new NextResponse(svg, {
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=3600, s-maxage=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }
  } catch {
    /* fallback to inline badge below */
  }

  // Fallback: minimal "N/A" badge when backend is unavailable
  const label = searchParams.get("label") ?? "AEO Score";
  const labelW = label.length * 6.5 + 10;
  const valueW = 34;
  const totalW = labelW + valueW;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${totalW}" height="20" role="img" aria-label="${label}: N/A">
  <title>${label}: N/A</title>
  <clipPath id="r"><rect width="${totalW}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="${labelW}" height="20" fill="#555"/>
    <rect x="${labelW}" width="${valueW}" height="20" fill="#9f9f9f"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="${labelW / 2}" y="14">${label}</text>
    <text x="${labelW + valueW / 2}" y="14">N/A</text>
  </g>
</svg>`;

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=60",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
