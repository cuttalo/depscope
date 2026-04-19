import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "DepScope — Package Intelligence for AI Agents";

export default async function OG() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%",
          display: "flex", flexDirection: "column",
          background: "#0a0a0a",
          color: "#fff", fontFamily: "system-ui, sans-serif", padding: "80px",
          justifyContent: "center",
        }}
      >
        <div style={{ display: "flex", fontSize: "30px", color: "#7dd3fc", fontWeight: 700, letterSpacing: "-0.02em" }}>depscope.dev</div>
        <div style={{ display: "flex", fontSize: "110px", fontWeight: 700, lineHeight: 1.05, marginTop: "20px", letterSpacing: "-0.04em" }}>Package Intelligence</div>
        <div style={{ display: "flex", fontSize: "110px", fontWeight: 700, lineHeight: 1.05, letterSpacing: "-0.04em", color: "#7dd3fc" }}>for AI Agents</div>
        <div style={{ display: "flex", fontSize: "30px", color: "#d1d5db", marginTop: "30px", maxWidth: "900px" }}>Free API for package health, vulnerabilities, and dependency analysis across 17 ecosystems.</div>
        <div style={{ display: "flex", gap: "24px", marginTop: "36px", fontSize: "22px", color: "#9ca3af" }}>
          <div style={{ display: "flex" }}>npm</div>
          <div style={{ display: "flex" }}>PyPI</div>
          <div style={{ display: "flex" }}>Cargo</div>
          <div style={{ display: "flex" }}>Go</div>
          <div style={{ display: "flex" }}>Maven</div>
          <div style={{ display: "flex" }}>NuGet</div>
          <div style={{ display: "flex" }}>+11 more</div>
        </div>
      </div>
    ),
    { ...size },
  );
}
