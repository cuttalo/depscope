"use client";

import dynamic from "next/dynamic";

const PitchApp = dynamic(() => import("./scenes"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#050607",
        color: "rgba(231,236,232,0.55)",
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 14,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      loading pitch…
    </div>
  ),
});

export default function PitchClient() {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#050607",
      }}
    >
      <PitchApp />
    </div>
  );
}
