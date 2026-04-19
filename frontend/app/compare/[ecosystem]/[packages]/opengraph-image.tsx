import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "DepScope package comparison";

type Props = { params: Promise<{ ecosystem: string; packages: string }> };

async function fetchCompare(ecosystem: string, packages: string[]) {
  try {
    const r = await fetch(`http://127.0.0.1:8000/api/compare/${ecosystem}/${packages.join(",")}`, { next: { revalidate: 3600 } });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

export default async function OG({ params }: Props) {
  const { ecosystem, packages: slug } = await params;
  const pkgs = decodeURIComponent(slug).split("-vs-").filter(Boolean);
  const data = await fetchCompare(ecosystem, pkgs);
  const winner = data?.winner;

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#0a0a0a", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "60px", justifyContent: "center" }}>
        <div style={{ display: "flex", fontSize: "24px", color: "#7dd3fc", fontWeight: 700 }}>DepScope · {ecosystem}</div>
        <div style={{ display: "flex", fontSize: "72px", fontWeight: 700, marginTop: "20px", lineHeight: 1.1, letterSpacing: "-0.02em" }}>
          {pkgs.join("  vs  ")}
        </div>
        {data?.packages ? (
          <div style={{ display: "flex", gap: "40px", marginTop: "40px", flexWrap: "wrap" }}>
            {data.packages.slice(0, 4).map((p: { package: string; health_score: number }) => (
              <div key={p.package} style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", fontSize: "24px", color: winner === p.package ? "#22c55e" : "#d1d5db", fontWeight: 700 }}>
                  {p.package}{winner === p.package ? " (WINNER)" : ""}
                </div>
                <div style={{ display: "flex", fontSize: "56px", fontWeight: 700, color: "#fff" }}>{p.health_score}</div>
                <div style={{ display: "flex", fontSize: "16px", color: "#9ca3af" }}>health / 100</div>
              </div>
            ))}
          </div>
        ) : null}
        <div style={{ display: "flex", flex: 1 }} />
        <div style={{ display: "flex", fontSize: "20px", color: "#6b7280" }}>depscope.dev/compare/{ecosystem}/{slug}</div>
      </div>
    ),
    { ...size },
  );
}
