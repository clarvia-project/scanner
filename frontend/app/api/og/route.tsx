import { ImageResponse } from "next/og";
import { type NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const ids = searchParams.get("ids") || "";

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  let tools: { name: string; clarvia_score: number; service_type: string }[] =
    [];

  if (ids) {
    try {
      const res = await fetch(
        `${apiBase}/v1/compare?ids=${encodeURIComponent(ids)}`
      );
      if (res.ok) {
        const data = await res.json();
        tools = (data.services || []).map((t: any) => ({
          name: String(t.name || ""),
          clarvia_score: Number(t.clarvia_score || 0),
          service_type: String(t.service_type || "general"),
        }));
      }
    } catch {
      /* fallback */
    }
  }

  const scoreColor = (s: number) =>
    s >= 70 ? "#22c55e" : s >= 40 ? "#eab308" : "#ef4444";

  const hasTools = tools.length > 0;
  const displayTools = hasTools
    ? tools.slice(0, 4)
    : [
        { name: "Tool A", clarvia_score: 0, service_type: "mcp server" },
        { name: "Tool B", clarvia_score: 0, service_type: "api" },
        { name: "Tool C", clarvia_score: 0, service_type: "cli tool" },
      ];

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          backgroundColor: "#0f172a",
          padding: "40px 60px",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "30px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              style={{
                display: "flex",
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                backgroundColor: "#3b82f6",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "22px",
                fontWeight: 700,
              }}
            >
              C
            </div>
            <div
              style={{
                display: "flex",
                color: "#94a3b8",
                fontSize: "20px",
              }}
            >
              clarvia.art
            </div>
          </div>
          <div
            style={{
              display: "flex",
              color: "#3b82f6",
              fontSize: "16px",
              fontWeight: 600,
              letterSpacing: "3px",
            }}
          >
            TOOL COMPARISON
          </div>
        </div>

        {/* Cards */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            gap: "20px",
            flex: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {displayTools.map((tool, i) => {
            const score = tool.clarvia_score;
            const color = score > 0 ? scoreColor(score) : "#475569";
            const label = score > 0 ? String(score) : "?";
            const name =
              tool.name.length > 18
                ? tool.name.slice(0, 18) + "..."
                : tool.name;
            const stype = tool.service_type.replace(/_/g, " ").toUpperCase();

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "16px",
                  padding: "36px 24px",
                  width: "220px",
                  height: "260px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    fontSize: "60px",
                    fontWeight: 800,
                    color: color,
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: "10px",
                    color: "#64748b",
                    letterSpacing: "2px",
                    marginTop: "4px",
                  }}
                >
                  AEO SCORE
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: "17px",
                    fontWeight: 600,
                    color: "#e2e8f0",
                    marginTop: "20px",
                  }}
                >
                  {name}
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: "11px",
                    color: "#3b82f6",
                    marginTop: "8px",
                    padding: "3px 12px",
                    backgroundColor: "rgba(59,130,246,0.1)",
                    borderRadius: "6px",
                  }}
                >
                  {stype}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "20px",
            color: "#475569",
            fontSize: "14px",
          }}
        >
          Compare agent tools at clarvia.art/compare
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
