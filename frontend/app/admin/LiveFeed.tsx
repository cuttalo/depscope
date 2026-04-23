"use client";

import { useEffect, useRef, useState } from "react";

interface LiveEvent {
  ecosystem?: string;
  package?: string;
  endpoint?: string;
  agent?: string;
  kind?: "agent" | "bot" | "human" | "unknown";
  country?: string | null;
  status?: number;
  ms?: number | null;
  cache_hit?: boolean;
  mcp_tool?: string | null;
  ts: number;
  _id: number;
}

// Fallback mapping client-side if event doesn't include kind (older server).
const AGENT_SET = new Set([
  "claude-code", "claude-desktop", "claude-web", "cursor", "windsurf",
  "continue", "aider", "devin", "copilot", "chatgpt", "replit", "cody",
  "tabnine", "zed", "mcp-generic", "python-sdk",
]);
const BOT_SET = new Set([
  "googlebot", "bingbot", "duckduckbot", "yandexbot", "baiduspider",
  "applebot", "facebookbot", "twitterbot", "linkedinbot",
  "anthropic-bot", "openai-bot", "perplexity-bot", "ahrefsbot", "crawler",
]);
const HUMAN_SET = new Set(["browser", "curl"]);

function classify(ev: LiveEvent): "agent" | "bot" | "human" | "unknown" {
  if (ev.kind) return ev.kind;
  const a = ev.agent || "";
  if (AGENT_SET.has(a)) return "agent";
  if (BOT_SET.has(a)) return "bot";
  if (HUMAN_SET.has(a)) return "human";
  return "unknown";
}

function agentColor(a?: string): string {
  switch (a) {
    case "claude-code":
    case "claude-desktop":
    case "claude-web":
    case "anthropic-bot":   return "#d97706";
    case "cursor":          return "#6366f1";
    case "windsurf":        return "#06b6d4";
    case "copilot":         return "#10b981";
    case "aider":           return "#8b5cf6";
    case "continue":        return "#f59e0b";
    case "replit":          return "#f26207";
    case "devin":           return "#a855f7";
    case "openai-bot":
    case "chatgpt":         return "#10a37f";
    case "perplexity-bot":  return "#22d3ee";
    case "googlebot":       return "#4285f4";
    case "bingbot":         return "#00809d";
    case "duckduckbot":     return "#de5833";
    case "yandexbot":       return "#ffcc00";
    case "applebot":        return "#999";
    case "facebookbot":     return "#1877f2";
    case "twitterbot":      return "#1da1f2";
    case "linkedinbot":     return "#0a66c2";
    case "ahrefsbot":       return "#ec4899";
    case "crawler":         return "#64748b";
    case "curl":            return "#94a3b8";
    case "browser":         return "#3b82f6";
    case "mcp-generic":     return "#8b5cf6";
    default:                return "#64748b";
  }
}

function statusColor(s?: number): string {
  if (!s) return "var(--text-faded)";
  if (s >= 500) return "var(--red)";
  if (s === 404) return "var(--orange)";
  if (s === 429) return "var(--yellow)";
  if (s >= 400) return "var(--orange)";
  if (s >= 200 && s < 300) return "var(--green)";
  return "var(--text-faded)";
}

function fmtAgo(ts: number, now: number): string {
  const diff = now - ts;
  if (diff < 2) return "now";
  if (diff < 60) return `${Math.floor(diff)}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h`;
}

function EventRow({ ev, now }: { ev: LiveEvent; now: number }) {
  const ago = fmtAgo(ev.ts, now);
  const isCache = ev.cache_hit;
  const method = (ev.endpoint || "check").toUpperCase();
  return (
    <div
      className="px-3 py-2 flex items-center gap-2 text-[11px] font-mono hover:bg-[var(--bg-hover)] transition border-b"
      style={{ borderColor: "var(--border)" }}
    >
      <span className="text-[var(--text-faded)] tabular-nums w-7 shrink-0">{ago}</span>
      <span
        className="tabular-nums w-8 shrink-0 font-semibold"
        style={{ color: statusColor(ev.status) }}
      >
        {ev.status || "—"}
      </span>
      <span className="w-14 shrink-0 text-[var(--text-dim)] uppercase text-[10px]">{method}</span>
      <span className="flex-1 min-w-0 truncate">
        {ev.ecosystem && <span className="text-[var(--text-faded)]">{ev.ecosystem}/</span>}
        <span className="text-[var(--text)]">{ev.package || "—"}</span>
      </span>
      <span
        className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
        style={{
          background: `color-mix(in srgb, ${agentColor(ev.agent)} 15%, transparent)`,
          color: agentColor(ev.agent),
        }}
      >
        {ev.agent || "unknown"}
      </span>
      <span className="tabular-nums text-[var(--text-dim)] w-12 shrink-0 text-right">
        {isCache ? "cache" : (typeof ev.ms === "number" ? `${ev.ms}ms` : "—")}
      </span>
    </div>
  );
}

function EmptyPane({ msg }: { msg: string }) {
  return (
    <div className="px-3 py-8 text-center text-[11px] text-[var(--text-faded)]">
      {msg}
    </div>
  );
}

export function LiveFeed({ max = 100 }: { max?: number }) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [counts, setCounts] = useState({ agent: 0, bot: 0, human: 0, unknown: 0 });
  const idRef = useRef(0);
  const [now, setNow] = useState(Date.now() / 1000);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const es = new EventSource("/api/admin/live", { withCredentials: true });
    es.addEventListener("hello", () => setConnected(true));
    es.addEventListener("ping", () => setConnected(true));
    es.addEventListener("api_call", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data) as LiveEvent;
        data._id = ++idRef.current;
        const kind = classify(data);
        setEvents((prev) => {
          const next = [data, ...prev];
          return next.length > max ? next.slice(0, max) : next;
        });
        setCounts((c) => ({ ...c, [kind]: c[kind] + 1 }));
      } catch {
        /* ignore bad event */
      }
    });
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, [max]);

  const agentEvents = events.filter((e) => {
    const k = classify(e);
    return k === "agent" || k === "human";
  });
  const botEvents = events.filter((e) => {
    const k = classify(e);
    return k === "bot" || k === "unknown";
  });

  return (
    <div className="rounded-lg overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span
              className={connected ? "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" : ""}
              style={{ background: connected ? "var(--green)" : "var(--red)" }}
            />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: connected ? "var(--green)" : "var(--red)" }} />
          </span>
          <span className="text-sm font-semibold text-[var(--text)]">Live activity</span>
          <span className="text-[10px] font-mono text-[var(--text-faded)] uppercase tracking-wider">
            {connected ? "connected" : "reconnecting"}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono tabular-nums">
          <span className="text-[var(--green)]">{counts.agent} agents</span>
          <span className="text-[var(--text-dim)]">{counts.human} humans</span>
          <span className="text-[var(--text-faded)]">{counts.bot} bots</span>
        </div>
      </div>

      {/* 2-column split */}
      <div className="grid grid-cols-2 divide-x" style={{ borderColor: "var(--border)" }}>
        {/* LEFT: Agents + humans */}
        <div className="min-w-0" style={{ borderColor: "var(--border)" }}>
          <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider flex items-center justify-between border-b"
               style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--green) 5%, transparent)", color: "var(--green)" }}>
            <span>AI Agents · Humans</span>
            <span className="tabular-nums">{agentEvents.length}</span>
          </div>
          <div className="max-h-[520px] overflow-y-auto">
            {agentEvents.length === 0 ? (
              <EmptyPane msg="Waiting for agent traffic…" />
            ) : (
              agentEvents.map((ev) => <EventRow key={ev._id} ev={ev} now={now} />)
            )}
          </div>
        </div>

        {/* RIGHT: Bots / crawlers */}
        <div className="min-w-0" style={{ borderColor: "var(--border)" }}>
          <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider flex items-center justify-between border-b"
               style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--text-faded) 8%, transparent)", color: "var(--text-dim)" }}>
            <span>Bots · Crawlers</span>
            <span className="tabular-nums">{botEvents.length}</span>
          </div>
          <div className="max-h-[520px] overflow-y-auto">
            {botEvents.length === 0 ? (
              <EmptyPane msg="No bot traffic yet." />
            ) : (
              botEvents.map((ev) => <EventRow key={ev._id} ev={ev} now={now} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveFeed;
