import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "DepScope";

export default async function OG() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: "#0a0a0a", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "80px", justifyContent: "center" }}>
        <div style={{ display: "flex", fontSize: "30px", color: "#7dd3fc", fontWeight: 700 }}>depscope.dev</div>
        <div style={{ display: "flex", fontSize: "96px", fontWeight: 700, marginTop: "20px", lineHeight: 1.1 }}>AI编程助手的</div>
        <div style={{ display: "flex", fontSize: "96px", fontWeight: 700, color: "#7dd3fc", lineHeight: 1.1 }}>软件包健康检测</div>
        <div style={{ display: "flex", fontSize: "28px", color: "#d1d5db", marginTop: "28px" }}>免费API，17个生态系统，无需认证</div>
      </div>
    ),
    { ...size },
  );
}
