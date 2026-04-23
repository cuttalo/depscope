"use client";

import { useEffect, useRef, useState } from "react";

interface LiveEvent {
  ecosystem?: string;
  package?: string;
  endpoint?: string;
  agent?: string;
  country?: string | null;
  status?: number;
  ms?: number | null;
  cache_hit?: boolean;
  mcp_tool?: string | null;
  ts: number;
  _id: number;
}

function agentColor(a?: string): string {
  switch (a) {
    case "claude-code":    return "#d97706";
    case "cursor":         return "#6366f1";
    case "windsurf":       return "#06b6d4";
    case "copilot":        return "#10b981";
    case "aider":          return "#8b5cf6";
    case "openai":
    case "chatgpt":        return "#10a37f";
    case "anthropic":      return "#d97706";
    case "crawler":        return "#64748b";
    case "curl":           return "#94a3b8";
    case "browser":        return "#3b82f6";
    default:               return "#64748b";
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

export function LiveFeed({ title = "Live activity", max = 50 }: { title?: string; max?: number }) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [count, setCount] = useState(0);
  const idRef = useRef(0);
  const [now, setNow] = useState(Date.now() / 1000);

  // Tick every second to refresh relative timestamps.
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
        setEvents((prev) => {
          const next = [data, ...prev];
          return next.length > max ? next.slice(0, max) : next;
        });
        setCount((c) => c + 1);
      } catch {
        /* ignore bad event */
      }
    });
    es.onerror = () => setConnected(false);
    return () => es.close();
  }, [max]);

  return (
    <div className="rounded-lg overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span
              className={connected ? "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" : ""}
              style={{ background: connected ? "var(--green)" : "var(--red)" }}
            />
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: connected ? "var(--green)" : "var(--red)" }} />
          </span>
          <span className="text-sm font-semibold text-[var(--text)]">{title}</span>
          <span className="text-[10px] font-mono text-[var(--text-faded)] uppercase tracking-wider">
            {connected ? "connected" : "reconnecting"}
          </span>
        </div>
        <div className="text-[11px] text-[var(--text-faded)] font-mono tabular-nums">
          {count.toLocaleString()} events
        </div>
      </div>

      <div className="max-h-[520px] overflow-y-auto">
        {events.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs text-[var(--text-faded)]">
            Waiting for activity…
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {events.map((ev) => {
              const ago = fmtAgo(ev.ts, now);
              const isCache = ev.cache_hit;
              const method = (ev.endpoint || "check").toUpperCase();
              const fullPath = ev.ecosystem && ev.package
                ? `${ev.ecosystem}/${ev.package}`
                : (ev.ecosystem || "");
              return (
                <div
                  key={ev._id}
                  className="px-4 py-2 flex items-center gap-3 text-xs font-mono hover:bg-[var(--bg-hover)] transition"
                  style={{ borderColor: "var(--border)" }}
                >
                  {/* time */}
                  <span className="text-[var(--text-faded)] tabular-nums w-10 shrink-0">{ago}</span>

                  {/* status */}
                  <span
                    className="tabular-nums w-8 shrink-0 font-semibold"
                    style={{ color: statusColor(ev.status) }}
                  >
                    {ev.status || "—"}
                  </span>

                  {/* endpoint */}
                  <span className="w-16 shrink-0 text-[var(--text-dim)] uppercase text-[10px]">{method}</span>

                  {/* path */}
                  <span className="flex-1 min-w-0 truncate">
                    {ev.ecosystem && (
                      <span className="text-[var(--text-faded)]">{ev.ecosystem}/</span>
                    )}
                    <span className="text-[var(--text)]">{ev.package || "—"}</span>
                  </span>

                  {/* agent */}
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                    style={{
                      background: `color-mix(in srgb, ${agentColor(ev.agent)} 15%, transparent)`,
                      color: agentColor(ev.agent),
                    }}
                  >
                    {ev.agent || "unknown"}
                  </span>

                  {/* response ms or cache flag */}
                  <span className="tabular-nums text-[var(--text-dim)] w-14 shrink-0 text-right">
                    {isCache ? "cache" : (typeof ev.ms === "number" ? `${ev.ms}ms` : "—")}
                  </span>

                  {/* country */}
                  {ev.country && (
                    <span className="text-[10px] text-[var(--text-faded)] w-6 shrink-0 text-right">
                      {ev.country}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default LiveFeed;
