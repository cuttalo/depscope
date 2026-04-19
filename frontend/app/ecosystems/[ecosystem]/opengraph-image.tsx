import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "DepScope ecosystem health dashboard";

type Props = { params: Promise<{ ecosystem: string }> };

const ECO_LABEL: Record<string, string> = {
  npm: "npm", pypi: "PyPI", cargo: "Cargo", go: "Go",
  composer: "Composer", maven: "Maven", nuget: "NuGet",
  rubygems: "RubyGems", pub: "Pub", hex: "Hex",
  swift: "Swift", cocoapods: "CocoaPods", cpan: "CPAN",
  hackage: "Hackage", cran: "CRAN", conda: "Conda", homebrew: "Homebrew",
};

export default async function OG({ params }: Props) {
  const { ecosystem } = await params;
  const label = ECO_LABEL[ecosystem] || ecosystem;
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#0a0a0a", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "60px" }}>
        <div style={{ display: "flex", fontSize: "28px", color: "#7dd3fc", fontWeight: 700 }}>DepScope</div>
        <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: "120px", fontWeight: 700, color: "#7dd3fc" }}>{label}</div>
          <div style={{ display: "flex", fontSize: "32px", color: "#d1d5db", marginTop: "10px" }}>Package Health Dashboard</div>
          <div style={{ display: "flex", fontSize: "22px", color: "#9ca3af", marginTop: "40px" }}>Live scores · vulnerabilities · trends</div>
        </div>
        <div style={{ display: "flex", fontSize: "22px", color: "#6b7280", justifyContent: "flex-end" }}>depscope.dev/ecosystems/{ecosystem}</div>
      </div>
    ),
    { ...size },
  );
}
