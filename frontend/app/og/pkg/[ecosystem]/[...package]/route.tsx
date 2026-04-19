import { ImageResponse } from "next/og";

export const runtime = "nodejs";

const ECO_LABEL: Record<string, string> = {
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
  composer: "Composer", maven: "Maven", nuget: "NuGet",
  rubygems: "RubyGems", pub: "Pub", hex: "Hex",
  swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN",
  hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

async function fetchPackage(ecosystem: string, pkg: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/check/${ecosystem}/${pkg}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ ecosystem: string; package: string[] }> },
) {
  const { ecosystem, package: pkgParts } = await params;
  const pkg = Array.isArray(pkgParts) ? pkgParts.join("/") : String(pkgParts);
  const data = await fetchPackage(ecosystem, pkg);
  const score = data?.health?.score ?? 0;
  const version = data?.latest_version ?? "";
  const vulns = data?.vulnerabilities?.count ?? 0;
  const downloads = data?.downloads_weekly ?? 0;
  const scoreColor = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : score >= 40 ? "#f97316" : "#ef4444";
  const vulnColor = vulns === 0 ? "#22c55e" : "#ef4444";
  const fmt = (n: number) => {
    if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#0a0a0a", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "60px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "24px", color: "#7dd3fc" }}>
          <div style={{ display: "flex", fontWeight: 700 }}>DepScope</div>
          <div style={{ display: "flex", color: "#444" }}>/</div>
          <div style={{ display: "flex", color: "#9ca3af" }}>{ECO_LABEL[ecosystem] || ecosystem}</div>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: "18px", marginTop: "30px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", fontSize: "82px", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1 }}>{pkg}</div>
          {version ? <div style={{ display: "flex", fontSize: "28px", color: "#9ca3af" }}>v{version}</div> : null}
        </div>
        {data?.description ? (
          <div style={{ display: "flex", fontSize: "26px", color: "#d1d5db", marginTop: "18px", maxWidth: "1080px", lineHeight: 1.3, overflow: "hidden" }}>
            {String(data.description).slice(0, 180)}
          </div>
        ) : null}
        <div style={{ display: "flex", flex: 1 }} />
        <div style={{ display: "flex", gap: "50px", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", fontSize: "18px", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.1em" }}>Health</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
              <div style={{ display: "flex", fontSize: "88px", fontWeight: 700, color: scoreColor, lineHeight: 1 }}>{score}</div>
              <div style={{ display: "flex", fontSize: "32px", color: "#6b7280" }}>/100</div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", fontSize: "18px", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.1em" }}>Vulns</div>
            <div style={{ display: "flex", fontSize: "88px", fontWeight: 700, color: vulnColor, lineHeight: 1 }}>{vulns}</div>
          </div>
          {downloads > 0 ? (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", fontSize: "18px", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.1em" }}>Weekly dl</div>
              <div style={{ display: "flex", fontSize: "88px", fontWeight: 700, color: "#fff", lineHeight: 1 }}>{fmt(downloads)}</div>
            </div>
          ) : null}
          <div style={{ display: "flex", flex: 1 }} />
          <div style={{ display: "flex", fontSize: "22px", color: "#6b7280" }}>depscope.dev</div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
