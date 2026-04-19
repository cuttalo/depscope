// @ts-nocheck
/* eslint-disable */
"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

const PitchApp = dynamic(() => import("./scenes"), {
  ssr: false,
  loading: () => null,
});

const BOT_UA = /bot|crawler|spider|GPTBot|ClaudeBot|PerplexityBot|CCBot|Bytespider|Amazonbot|Applebot|Google-Extended|anthropic-ai/i;

export default function PitchSection() {
  const ref = useRef<HTMLDivElement>(null);
  const [shouldRender, setShouldRender] = useState(false);
  const [isHuman, setIsHuman] = useState(false);

  useEffect(() => {
    if (typeof navigator === "undefined") return;
    setIsHuman(!BOT_UA.test(navigator.userAgent || ""));
  }, []);

  useEffect(() => {
    if (!isHuman || !ref.current) return;
    const el = ref.current;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setShouldRender(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [isHuman]);

  if (!isHuman) return null;

  return (
    <div
      ref={ref}
      data-nosnippet
      aria-hidden="true"
      style={{
        position: "relative",
        width: "100%",
        maxWidth: 1200,
        margin: "0 auto",
        aspectRatio: "16 / 9",
        background: "#050607",
        borderRadius: 14,
        overflow: "hidden",
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 30px 80px rgba(0,0,0,0.4)",
      }}
    >
      {shouldRender && <PitchApp />}
    </div>
  );
}
