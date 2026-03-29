import { ImageResponse } from "next/og";
import { type NextRequest } from "next/server";

export const runtime = "edge";

// Inline SVG owl logo as a data URI for use in ImageResponse <img>
const OWL_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200"><g><ellipse cx="46" cy="96" rx="30" ry="22" fill="#6fb2ff" transform="rotate(-18 46 96)"/><ellipse cx="154" cy="96" rx="30" ry="22" fill="#6fb2ff" transform="rotate(18 154 96)"/><ellipse cx="30" cy="102" rx="14" ry="10" fill="#5aa2fb" transform="rotate(-28 30 102)"/><ellipse cx="170" cy="102" rx="14" ry="10" fill="#5aa2fb" transform="rotate(28 170 102)"/><circle cx="100" cy="102" r="52" fill="#2583f6"/><ellipse cx="100" cy="118" rx="28" ry="24" fill="#8fc3ff"/><path d="M67 62 Q72 45 85 56 Q77 60 74 70 Z" fill="#2583f6"/><path d="M133 62 Q128 45 115 56 Q123 60 126 70 Z" fill="#2583f6"/><ellipse cx="82" cy="89" rx="23" ry="25" fill="#beddff"/><ellipse cx="118" cy="89" rx="23" ry="25" fill="#beddff"/><ellipse cx="82" cy="90" rx="16" ry="18" fill="#ffffff"/><ellipse cx="118" cy="90" rx="16" ry="18" fill="#ffffff"/><circle cx="86" cy="93" r="6.5" fill="#111111"/><circle cx="114" cy="93" r="6.5" fill="#111111"/><circle cx="88.5" cy="90.5" r="2" fill="#ffffff"/><circle cx="116.5" cy="90.5" r="2" fill="#ffffff"/><path d="M100 96 L91 104 Q100 110 109 104 Z" fill="#f59e0b"/><g fill="#f59e0b"><ellipse cx="83" cy="152" rx="6" ry="4"/><path d="M78 152 L73 158 L79 156 Z"/><path d="M83 153 L83 160 L86 154 Z"/><path d="M88 152 L93 158 L87 156 Z"/></g><g fill="#f59e0b"><ellipse cx="117" cy="152" rx="6" ry="4"/><path d="M112 152 L107 158 L113 156 Z"/><path d="M117 153 L117 160 L120 154 Z"/><path d="M122 152 L127 158 L121 156 Z"/></g><ellipse cx="100" cy="122" rx="7" ry="5" fill="#7ebaff"/><ellipse cx="88" cy="131" rx="6" ry="4" fill="#7ebaff"/><ellipse cx="112" cy="131" rx="6" ry="4" fill="#7ebaff"/></g></svg>`;

const owlDataUri = `data:image/svg+xml;base64,${btoa(OWL_SVG)}`;
// 64x64 PNG logo as base64 data URI (works reliably in Edge Runtime ImageResponse)
const owlPngDataUri = "data:image/png;base64,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";

const scoreColor = (s: number) =>
  s >= 70 ? "#22c55e" : s >= 40 ? "#eab308" : "#ef4444";

const scoreLabel = (s: number) =>
  s >= 80 ? "Excellent" : s >= 60 ? "Good" : s >= 40 ? "Fair" : "Needs Work";

/**
 * OG Image API — generates dynamic Open Graph preview cards.
 *
 * Query params:
 *   (none)              → Default landing page card
 *   type=tool           → Individual tool card
 *     &name=...         → Tool name
 *     &score=...        → Clarvia score (0-100)
 *     &stype=...        → Service type (mcp_server, api, etc.)
 *     &category=...     → Category label
 *   ids=...             → Compare mode (existing behavior)
 */
// CSS owl version — Satori can't render <img> reliably, so owl is built with CSS divs
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const type = searchParams.get("type");
  const ids = searchParams.get("ids") || "";

  // ─── Tool-specific OG card ───
  if (type === "tool") {
    const name = searchParams.get("name") || "Unknown Tool";
    const score = parseInt(searchParams.get("score") || "0", 10);
    const stype = (searchParams.get("stype") || "tool")
      .replace(/_/g, " ")
      .toUpperCase();
    const category = searchParams.get("category") || "";

    const color = score > 0 ? scoreColor(score) : "#475569";
    const label = score > 0 ? scoreLabel(score) : "Unscored";
    const displayName =
      name.length > 32 ? name.slice(0, 32) + "..." : name;

    return new ImageResponse(
      (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            backgroundColor: "#0b0f18",
            padding: "50px 70px",
          }}
        >
          {/* Header: logo + branding */}
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                gap: "14px",
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={owlPngDataUri}
                width="48"
                height="48"
                alt=""
                style={{ borderRadius: "12px" }}
              />
              <div
                style={{
                  display: "flex",
                  color: "#94a3b8",
                  fontSize: "22px",
                  fontWeight: 600,
                }}
              >
                clarvia
              </div>
            </div>
            <div
              style={{
                display: "flex",
                color: "#475569",
                fontSize: "14px",
                fontWeight: 500,
                letterSpacing: "2px",
              }}
            >
              AEO SCORE REPORT
            </div>
          </div>

          {/* Main content */}
          <div
            style={{
              display: "flex",
              flex: 1,
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              gap: "60px",
            }}
          >
            {/* Score circle */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "200px",
                  height: "200px",
                  borderRadius: "100px",
                  border: `6px solid ${color}`,
                  backgroundColor: "rgba(255,255,255,0.02)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    fontSize: "72px",
                    fontWeight: 800,
                    color: color,
                  }}
                >
                  {score > 0 ? String(score) : "?"}
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  fontSize: "16px",
                  fontWeight: 600,
                  color: color,
                  marginTop: "12px",
                  letterSpacing: "1px",
                }}
              >
                {label.toUpperCase()}
              </div>
            </div>

            {/* Tool info */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                maxWidth: "600px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  fontSize: "44px",
                  fontWeight: 800,
                  color: "#f1f5f9",
                  lineHeight: 1.2,
                }}
              >
                {displayName}
              </div>
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  gap: "12px",
                  marginTop: "20px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    fontSize: "13px",
                    color: "#3b82f6",
                    padding: "6px 16px",
                    backgroundColor: "rgba(59,130,246,0.12)",
                    borderRadius: "8px",
                    fontWeight: 600,
                  }}
                >
                  {stype}
                </div>
                {category && (
                  <div
                    style={{
                      display: "flex",
                      fontSize: "13px",
                      color: "#94a3b8",
                      padding: "6px 16px",
                      backgroundColor: "rgba(148,163,184,0.1)",
                      borderRadius: "8px",
                    }}
                  >
                    {category}
                  </div>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  fontSize: "18px",
                  color: "#64748b",
                  marginTop: "24px",
                }}
              >
                Agent readiness analysis on clarvia.art
              </div>
            </div>
          </div>

          {/* Footer */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: "15px",
                color: "#334155",
              }}
            >
              clarvia.art
            </div>
            <div
              style={{
                display: "flex",
                fontSize: "13px",
                color: "#334155",
              }}
            >
              AI Engine Optimization Standard
            </div>
          </div>
        </div>
      ),
      { width: 1200, height: 630 }
    );
  }

  // ─── Compare mode (existing) ───
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://clarvia-api.onrender.com";
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

  const hasTools = tools.length > 0;

  // ─── Default landing OG image ───
  if (!hasTools && !ids) {
    return new ImageResponse(
      (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            backgroundColor: "#0b0f18",
            padding: "60px 80px",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {/* Owl logo + brand name */}
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              gap: "18px",
              marginBottom: "32px",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={owlPngDataUri}
              width="80"
              height="80"
              alt=""
              style={{ borderRadius: "20px" }}
            />
            <div
              style={{
                display: "flex",
                color: "#f1f5f9",
                fontSize: "52px",
                fontWeight: 700,
              }}
            >
              clarvia
            </div>
          </div>

          {/* Tagline */}
          <div
            style={{
              display: "flex",
              fontSize: "48px",
              fontWeight: 800,
              color: "#f8fafc",
              textAlign: "center",
              lineHeight: 1.2,
              maxWidth: "900px",
            }}
          >
            Is your service ready for AI agents?
          </div>

          {/* Subtitle */}
          <div
            style={{
              display: "flex",
              fontSize: "22px",
              color: "#94a3b8",
              marginTop: "20px",
              textAlign: "center",
              maxWidth: "700px",
            }}
          >
            The AEO standard for agent discoverability and trust
          </div>

          {/* Stats bar */}
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              gap: "48px",
              marginTop: "44px",
            }}
          >
            {[
              { label: "Tools Scored", value: "28K+" },
              { label: "Tool Types", value: "5" },
              { label: "Score Range", value: "0-100" },
            ].map((stat, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    fontSize: "36px",
                    fontWeight: 800,
                    color: "#3b82f6",
                  }}
                >
                  {stat.value}
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: "14px",
                    color: "#64748b",
                    letterSpacing: "1px",
                  }}
                >
                  {stat.label.toUpperCase()}
                </div>
              </div>
            ))}
          </div>

          {/* URL */}
          <div
            style={{
              display: "flex",
              fontSize: "18px",
              color: "#475569",
              marginTop: "36px",
            }}
          >
            clarvia.art
          </div>
        </div>
      ),
      { width: 1200, height: 630 }
    );
  }

  // ─── Compare mode cards ───
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
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={owlPngDataUri}
              width="40"
              height="40"
              alt=""
            />
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
