"use client";

import { useEffect, useState, useCallback, useRef } from "react";

/* ─── Types ─── */
interface Opportunity {
  id: number;
  platform: string;
  url: string;
  title: string;
  relevance_score: number;
  suggested_action: string;
  suggested_content: string;
  status: string;
  created_at: string;
  platform_icon?: string;
  rejected_reason?: string;
  approved_at?: string;
  generated_at?: string;
  executed_at?: string;
  author?: string;
  reactions?: number;
  article_id?: number;
}

interface Dashboard {
  opps_today: number;
  actions_today: number;
  comments_total: number;
  emails_total: number;
  queue_count: number;
  last_run: string | null;
  pipeline: Record<string, number>;
}

interface TimelineEvent {
  id: number;
  action_type: string;
  platform: string;
  target_url: string;
  content: string;
  status: string;
  created_at: string;
}

interface AgentState {
  active: boolean;
  scanning: boolean;
  current_platform?: string;
  uptime_seconds?: number;
}

/* ─── Constants ─── */
const PLATFORM_ICONS: Record<string, string> = {
  devto: "\u{1f4dd}", reddit: "\u{1f534}", hn: "\u{1f7e0}", hackernews: "\u{1f7e0}",
  cursor: "\u{1f4bb}", cursor_forum: "\u{1f4bb}", discord: "\u{1f4ac}", discord_claude: "\u{1f4ac}",
  email: "\u{1f4e7}", npm: "\u{1f4e6}", rapidapi: "\u26a1", gpt_store: "\u{1f916}",
  internal: "\u2699\ufe0f", all: "\u{1f30d}",
};

const PLATFORM_LABELS: Record<string, string> = {
  devto: "Dev.to", reddit: "Reddit", hn: "HN", hackernews: "HN",
  cursor: "Cursor", cursor_forum: "Cursor Forum", discord_claude: "Discord",
  email: "Email", npm: "npm", rapidapi: "RapidAPI", gpt_store: "GPT Store",
  internal: "Internal", all: "All",
};

const STATUS_COLORS: Record<string, string> = {
  found: "#94a3b8", approved: "#3b82f6", content_ready: "#8b5cf6",
  execute: "#f97316", done: "#22c55e", rejected: "#ef4444",
  skipped: "#4b5563", manual_post: "#f472b6",
};

const STATUS_BG: Record<string, string> = {
  found: "rgba(148,163,184,0.15)", approved: "rgba(59,130,246,0.15)", content_ready: "rgba(139,92,246,0.15)",
  execute: "rgba(249,115,22,0.15)", done: "rgba(34,197,94,0.15)", rejected: "rgba(239,68,68,0.15)",
  skipped: "rgba(75,85,99,0.15)", manual_post: "rgba(244,114,182,0.15)",
};

const MANUAL_PLATFORMS = ["reddit", "hn", "hackernews", "discord", "discord_claude"];

const API = "/api/admin/agent";

/* ─── Helpers ─── */
function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "mai";
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return "adesso";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m fa`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h fa`;
  const days = Math.floor(hours / 24);
  return `${days}g fa`;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function relevanceColor(score: number): string {
  if (score > 7) return "var(--green)";
  if (score > 4) return "var(--yellow)";
  return "var(--red)";
}

async function apiFetch(path: string, opts?: RequestInit) {
  const key = typeof window !== "undefined" ? localStorage.getItem("ds_admin_key") || "" : "";
  const res = await fetch(path, {
    ...opts,
    headers: { "X-API-Key": key, "Content-Type": "application/json", ...(opts?.headers || {}) },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

const translate = async (text: string): Promise<string> => {
  if (!text || text.length < 5) return text;
  const chunks = text.match(/.{1,500}/g) || [text];
  const translated = await Promise.all(chunks.map(async (chunk) => {
    const res = await fetch(`/api/translate?text=${encodeURIComponent(chunk)}&to=it`);
    const d = await res.json();
    return d.translated || chunk;
  }));
  return translated.join(" ");
};

/* ─── Component ─── */
export default function MissionControlPage() {
  const [authed, setAuthed] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);

  // Data
  const [agentState, setAgentState] = useState<AgentState>({ active: false, scanning: false });
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);

  // Filters
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Detail panel state
  const [editContent, setEditContent] = useState("");
  const [translatedTitle, setTranslatedTitle] = useState("");
  const [translatedContent, setTranslatedContent] = useState("");
  const [translatedGenerated, setTranslatedGenerated] = useState("");
  const [loadingTranslation, setLoadingTranslation] = useState(false);
  const [articleBody, setArticleBody] = useState("");
  const [loadingArticle, setLoadingArticle] = useState(false);
  const [skipReason, setSkipReason] = useState("");
  const [copied, setCopied] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth
  useEffect(() => {
    const saved = localStorage.getItem("ds_admin_key");
    if (saved) {
      setApiKey(saved);
      fetch("/api/admin/dashboard", { headers: { "X-API-Key": saved } })
        .then(r => { if (r.ok) { setAuthed(true); } else { localStorage.removeItem("ds_admin_key"); } })
        .catch(() => {});
    }
  }, []);

  const login = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/dashboard", { headers: { "X-API-Key": apiKey } });
      if (!res.ok) throw new Error("Accesso negato");
      setAuthed(true);
      localStorage.setItem("ds_admin_key", apiKey);
    } catch { alert("API key non valida"); }
    finally { setLoading(false); }
  };

  // Load all data
  const loadData = useCallback(async () => {
    try {
      const [stateRes, dashRes, oppsRes, tlRes] = await Promise.all([
        apiFetch(`${API}/state`).catch(() => ({ active: false, scanning: false })),
        apiFetch(`${API}/dashboard`).catch(() => null),
        apiFetch(`${API}/opportunities/all`).catch(() => []),
        apiFetch(`${API}/timeline`).catch(() => []),
      ]);
      setAgentState(stateRes);
      setDashboard(dashRes);
      setOpportunities(Array.isArray(oppsRes) ? oppsRes : oppsRes.opportunities || []);
      setTimeline(Array.isArray(tlRes) ? tlRes.slice(0, 5) : (tlRes.events || []).slice(0, 5));
    } catch {}
  }, []);

  useEffect(() => {
    if (!authed) return;
    loadData();
    pollRef.current = setInterval(loadData, 10000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [authed, loadData]);

  // When selecting an opportunity, auto-translate
  const selectOpp = useCallback(async (opp: Opportunity) => {
    setSelectedOpp(opp);
    setEditContent(opp.suggested_content || "");
    setTranslatedTitle("");
    setTranslatedContent("");
    setTranslatedGenerated("");
    setArticleBody("");
    setSkipReason("");
    setCopied(false);
    setMobileDetailOpen(true);

    // Translate title
    setLoadingTranslation(true);
    try {
      const tt = await translate(opp.title);
      setTranslatedTitle(tt);
      if (opp.suggested_content) {
        const tg = await translate(opp.suggested_content);
        setTranslatedGenerated(tg);
      }
    } catch {}
    setLoadingTranslation(false);

    // Fetch article body via our backend API
    if (opp.platform === "devto" || opp.platform === "hn" || opp.platform === "hackernews") {
      setLoadingArticle(true);
      try {
        const res = await apiFetch(`${API}/opportunities/${opp.id}/article`);
        if (res.ok) {
          const data = await res.json();
          const html = data.body_html || "";
          const md = data.body_markdown || data.body || "";
          setArticleBody(html || md);
          // Translate first 500 chars
          const snippet = md.slice(0, 500);
          if (snippet) {
            const tc = await translate(snippet);
            setTranslatedContent(tc);
          }
        }
      } catch {}
      setLoadingArticle(false);
    }
  }, []);

  // Actions
  const toggleAgent = async () => {
    try {
      await apiFetch(`${API}/toggle`, { method: "POST" });
      setAgentState(prev => ({ ...prev, active: !prev.active }));
    } catch {}
  };

  const approveOpp = async (id: number) => {
    setActionLoading("approve");
    try {
      await apiFetch(`${API}/opportunities/${id}/approve`, { method: "PUT" });
      if (selectedOpp?.id === id) setSelectedOpp(prev => prev ? { ...prev, status: "approved" } : null);
      // Poll for content generation completion (backend generates async)
      let attempts = 0;
      const genPoll = setInterval(async () => {
        attempts++;
        if (attempts > 30) { clearInterval(genPoll); setActionLoading(""); return; }
        try {
          const r = await apiFetch(`${API}/opportunities/all`);
          if (r.ok) {
            const opps = await r.json();
            const updated = opps.find((o: Opportunity) => o.id === id);
            if (updated && updated.status === "content_ready") {
              clearInterval(genPoll);
              setSelectedOpp(updated);
              setEditContent(updated.suggested_content || "");
              if (updated.suggested_content) {
                const tg = await translate(updated.suggested_content);
                setTranslatedGenerated(tg);
              }
              await loadData();
              setActionLoading("");
            }
          }
        } catch {}
      }, 3000);
    } catch { setActionLoading(""); }
  };

  const executeOpp = async (id: number) => {
    setActionLoading("execute");
    try {
      await apiFetch(`${API}/opportunities/${id}/execute`, { method: "PUT" });
      await loadData();
      if (selectedOpp?.id === id) setSelectedOpp(prev => prev ? { ...prev, status: "done" } : null);
    } catch {}
    setActionLoading("");
  };

  const rejectOpp = async (id: number, reason?: string) => {
    setActionLoading("reject");
    try {
      await apiFetch(`${API}/opportunities/${id}/reject`, { method: "PUT", body: JSON.stringify({ reason: reason || "skipped" }) });
      await loadData();
      if (selectedOpp?.id === id) setSelectedOpp(prev => prev ? { ...prev, status: "rejected" } : null);
    } catch {}
    setActionLoading("");
  };

  const updateContent = async (id: number, content: string) => {
    setActionLoading("edit");
    try {
      await apiFetch(`${API}/opportunities/${id}/content`, { method: "PUT", body: JSON.stringify({ content }) });
      await loadData();
      if (selectedOpp?.id === id) setSelectedOpp(prev => prev ? { ...prev, suggested_content: content, status: "content_ready" } : null);
    } catch {}
    setActionLoading("");
  };

  const runFullScan = async () => {
    try {
      await apiFetch(`${API}/run`, { method: "POST" });
      setAgentState(prev => ({ ...prev, scanning: true }));
    } catch {}
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Filtered opportunities
  const filtered = opportunities.filter(o => {
    if (platformFilter !== "all" && o.platform !== platformFilter) return false;
    if (statusFilter !== "all" && o.status !== statusFilter) return false;
    return true;
  }).sort((a, b) => b.relevance_score - a.relevance_score);

  // Unique platforms from data
  const platformsInData = [...new Set(opportunities.map(o => o.platform))];

  if (!authed) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
        <div className="card" style={{ padding: 32, width: "100%", maxWidth: 400 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 24, background: "linear-gradient(135deg, #22d3ee, #a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Mission Control</h1>
          <input
            type="password" value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            onKeyDown={e => e.key === "Enter" && login()}
            placeholder="Admin API Key"
            style={{ width: "100%", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 16px", marginBottom: 16, color: "var(--text)", outline: "none", boxSizing: "border-box" }}
          />
          <button onClick={login} disabled={loading}
            style={{ width: "100%", background: "var(--accent)", color: "#000", fontWeight: 600, padding: "12px", borderRadius: 8, border: "none", cursor: "pointer" }}>
            {loading ? "..." : "Accedi"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      {/* ═══ MAIN LAYOUT ═══ */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── SIDEBAR ── */}
        <aside style={{
          width: 250, minWidth: 250, background: "var(--bg-card)", borderRight: "1px solid var(--border)",
          display: "flex", flexDirection: "column", padding: 16, gap: 16, overflowY: "auto",
        }} className="mc-sidebar">
          {/* Agent status */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={toggleAgent}>
            <div style={{
              width: 14, height: 14, borderRadius: 7,
              background: agentState.active ? "var(--green)" : "var(--red)",
              boxShadow: agentState.active ? "0 0 10px rgba(34,197,94,0.6)" : "0 0 10px rgba(239,68,68,0.4)",
              animation: agentState.active ? "mc-pulse 2s infinite" : "none",
            }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: agentState.active ? "var(--green)" : "var(--red)" }}>
              Agent {agentState.active ? "ON" : "OFF"}
            </span>
          </div>

          {/* Scanning status */}
          <div style={{ fontSize: 12, color: "var(--text-dim)", fontFamily: "monospace" }}>
            {agentState.scanning
              ? <span style={{ color: "var(--yellow)" }}>Scanning {agentState.current_platform ? PLATFORM_LABELS[agentState.current_platform] || agentState.current_platform : ""}...</span>
              : "Idle"
            }
          </div>

          {/* KPI */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="card" style={{ padding: "10px 12px" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--accent)" }}>{dashboard?.queue_count ?? 0}</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>In coda</div>
            </div>
            <div className="card" style={{ padding: "10px 12px" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--green)" }}>{dashboard?.actions_today ?? 0}</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Azioni oggi</div>
            </div>
            <div className="card" style={{ padding: "10px 12px" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--yellow)" }}>{dashboard?.emails_total ?? 0}</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Email inviate</div>
            </div>
            <div className="card" style={{ padding: "10px 12px" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--orange)" }}>{dashboard?.comments_total ?? 0}</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Commenti postati</div>
            </div>
          </div>

          {/* Platform filters */}
          <div>
            <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>Piattaforma</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              <button onClick={() => setPlatformFilter("all")}
                style={{ ...filterBtnStyle, background: platformFilter === "all" ? "var(--accent)" : "var(--bg)", color: platformFilter === "all" ? "#000" : "var(--text-dim)" }}>
                Tutti
              </button>
              {["devto", "reddit", "hn", "cursor", "email"].map(p => (
                <button key={p} onClick={() => setPlatformFilter(platformFilter === p ? "all" : p)}
                  style={{ ...filterBtnStyle, background: platformFilter === p ? "var(--accent)" : "var(--bg)", color: platformFilter === p ? "#000" : "var(--text-dim)" }}>
                  {PLATFORM_ICONS[p] || ""} {PLATFORM_LABELS[p] || p}
                </button>
              ))}
            </div>
          </div>

          {/* Status filters */}
          <div>
            <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>Status</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {["all", "found", "approved", "content_ready", "execute"].map(s => (
                <button key={s} onClick={() => setStatusFilter(statusFilter === s ? "all" : s)}
                  style={{
                    ...filterBtnStyle,
                    background: statusFilter === s ? (s === "all" ? "var(--accent)" : STATUS_BG[s]) : "var(--bg)",
                    color: statusFilter === s ? (s === "all" ? "#000" : STATUS_COLORS[s]) : "var(--text-dim)",
                    borderColor: statusFilter === s && s !== "all" ? STATUS_COLORS[s] : "var(--border)",
                  }}>
                  {s === "all" ? "Tutti" : s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Nav links */}
          <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
            <a href="/admin" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>Admin Dashboard</a>
            <a href="/agent" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>Marketing Agent</a>
          </div>
        </aside>

        {/* ── CENTRAL COLUMN ── */}
        <main style={{ flex: 1, overflowY: "auto", padding: 16 }} className="mc-main">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text)" }}>
              Opportunita ({filtered.length})
            </h2>
            <button onClick={loadData} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 12px", fontSize: 12, color: "var(--text-dim)", cursor: "pointer" }}>
              Refresh
            </button>
          </div>

          {filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: 40, color: "var(--text-dim)" }}>
              Nessuna opportunita trovata con questi filtri.
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {filtered.map(opp => (
              <div
                key={opp.id}
                onClick={() => selectOpp(opp)}
                className="card"
                style={{
                  padding: "12px 16px", cursor: "pointer",
                  borderColor: selectedOpp?.id === opp.id ? "var(--accent)" : "var(--border)",
                  transition: "border-color 0.2s, background 0.2s",
                }}
                onMouseEnter={e => { if (selectedOpp?.id !== opp.id) (e.currentTarget as HTMLElement).style.borderColor = "var(--accent)"; }}
                onMouseLeave={e => { if (selectedOpp?.id !== opp.id) (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; }}
              >
                {/* Header row */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 16 }}>{PLATFORM_ICONS[opp.platform] || "\u{1f30d}"}</span>
                  <span style={{
                    fontSize: 12, fontWeight: 700, fontFamily: "monospace",
                    color: relevanceColor(opp.relevance_score),
                    background: `${relevanceColor(opp.relevance_score)}22`,
                    padding: "2px 8px", borderRadius: 4,
                  }}>
                    {opp.relevance_score}/10
                  </span>
                  <span style={{ fontSize: 11, color: "var(--text-dim)", fontFamily: "monospace", marginLeft: "auto" }}>
                    {timeAgo(opp.created_at)}
                  </span>
                </div>

                {/* Title */}
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>
                  {opp.title}
                </div>

                {/* Author + reactions + status */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  {opp.author && <span style={{ fontSize: 11, color: "var(--text-dim)" }}>@{opp.author}</span>}
                  {opp.reactions != null && opp.reactions > 0 && (
                    <span style={{ fontSize: 11, color: "var(--text-dim)" }}>{opp.reactions} reactions</span>
                  )}
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 4,
                    background: STATUS_BG[opp.status] || "rgba(100,116,139,0.15)",
                    color: STATUS_COLORS[opp.status] || "#94a3b8",
                  }}>
                    {opp.status.replace("_", " ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </main>

        {/* ── DETAIL PANEL ── */}
        <aside
          style={{
            width: 400, minWidth: 400, background: "var(--bg-card)", borderLeft: "1px solid var(--border)",
            overflowY: "auto", padding: selectedOpp ? 20 : 0,
            display: selectedOpp ? "block" : "flex", alignItems: "center", justifyContent: "center",
          }}
          className="mc-detail"
        >
          {!selectedOpp ? (
            <div style={{ color: "var(--text-dim)", fontSize: 14, textAlign: "center", padding: 20 }}>
              Seleziona un&apos;opportunita dalla lista
            </div>
          ) : (
            <div>
              {/* Close on mobile */}
              <button
                onClick={() => { setMobileDetailOpen(false); setSelectedOpp(null); }}
                className="mc-detail-close"
                style={{ display: "none", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "var(--text-dim)", cursor: "pointer", marginBottom: 12 }}
              >
                Chiudi
              </button>

              {/* Section 1: Original Detail */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Dettaglio Originale</div>
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, lineHeight: 1.4 }}>{selectedOpp.title}</h3>
                {selectedOpp.url && (
                  <a href={selectedOpp.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 12, color: "var(--accent)", wordBreak: "break-all", display: "block", marginBottom: 8 }}>
                    {selectedOpp.url}
                  </a>
                )}
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 12, color: "var(--text-dim)", marginBottom: 8 }}>
                  <span>{PLATFORM_ICONS[selectedOpp.platform]} {PLATFORM_LABELS[selectedOpp.platform] || selectedOpp.platform}</span>
                  {selectedOpp.author && <span>@{selectedOpp.author}</span>}
                  <span>{new Date(selectedOpp.created_at).toLocaleDateString("it-IT")}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <span style={{
                    fontSize: 20, fontWeight: 800, fontFamily: "monospace",
                    color: relevanceColor(selectedOpp.relevance_score),
                  }}>
                    {selectedOpp.relevance_score}/10
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-dim)" }}>relevance score</span>
                </div>

                {/* Article body */}
                {(selectedOpp.platform === "devto" || selectedOpp.platform === "hn" || selectedOpp.platform === "hackernews") && (
                  <div style={{ marginTop: 8 }}>
                    {loadingArticle ? (
                      <div style={{ fontSize: 12, color: "var(--text-dim)" }}>Caricamento articolo...</div>
                    ) : articleBody ? (
                      <div style={{
                        fontSize: 12, lineHeight: 1.6, color: "var(--text-dim)",
                        maxHeight: 200, overflowY: "auto",
                        background: "var(--bg)", borderRadius: 8, padding: 12,
                        border: "1px solid var(--border)",
                      }} dangerouslySetInnerHTML={{ __html: articleBody }} />
                    ) : null}
                  </div>
                )}
              </div>

              {/* Section 2: Italian Translation */}
              <div style={{ marginBottom: 20, background: "var(--bg)", borderRadius: 8, padding: 12, border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  {"🇮🇹"} Traduzione automatica
                  {loadingTranslation && <span style={{ fontSize: 10 }}>...</span>}
                </div>
                {translatedTitle && (
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 6 }}>{translatedTitle}</div>
                )}
                {translatedContent && (
                  <div style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.5 }}>{translatedContent}</div>
                )}
                {!translatedTitle && !loadingTranslation && (
                  <div style={{ fontSize: 12, color: "var(--text-dim)" }}>Nessuna traduzione disponibile</div>
                )}
              </div>

              {/* Section 3: Suggested Content */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Contenuto Suggerito</div>
                {selectedOpp.status === "content_ready" || selectedOpp.suggested_content ? (
                  <>
                    <textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      style={{
                        width: "100%", minHeight: 150, background: "var(--bg)", border: "1px solid var(--border)",
                        borderRadius: 8, padding: 12, color: "var(--text)", fontSize: 13, resize: "vertical",
                        fontFamily: "system-ui", lineHeight: 1.5, boxSizing: "border-box",
                      }}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
                      <span>{editContent.length} caratteri</span>
                      <button onClick={() => updateContent(selectedOpp.id, editContent)}
                        style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontSize: 11 }}>
                        Salva modifiche
                      </button>
                    </div>
                    {translatedGenerated && (
                      <div style={{ marginTop: 8, background: "var(--bg)", borderRadius: 8, padding: 10, border: "1px solid var(--border)" }}>
                        <div style={{ fontSize: 10, color: "var(--text-dim)", marginBottom: 4 }}>{"🇮🇹"} Traduzione contenuto generato</div>
                        <div style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.5 }}>{translatedGenerated}</div>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ textAlign: "center", padding: 20, background: "var(--bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
                    <div style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 8 }}>
                      {selectedOpp.status === "approved" ? "⏳ Generazione in corso..." : "Contenuto non ancora generato"}
                    </div>
                    {selectedOpp.status !== "approved" && <button onClick={() => approveOpp(selectedOpp.id)}
                      style={{ background: "var(--accent)", color: "#000", border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                      Generate with Claude
                    </button>}
                  </div>
                )}
              </div>

              {/* Section 4: Actions */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Azioni</div>

                {selectedOpp.status === "found" && (
                  <button onClick={() => approveOpp(selectedOpp.id)} disabled={actionLoading === "approve"}
                    style={{ ...actionBtnStyle, background: "rgba(59,130,246,0.15)", color: "#3b82f6", borderColor: "#3b82f644" }}>
                    {actionLoading === "approve" ? "..." : "\u2713 Approve & Generate"}
                  </button>
                )}

                {(selectedOpp.status === "content_ready" || selectedOpp.status === "approved") && !MANUAL_PLATFORMS.includes(selectedOpp.platform) && (
                  <button onClick={() => executeOpp(selectedOpp.id)} disabled={actionLoading === "execute"}
                    style={{ ...actionBtnStyle, background: "rgba(34,197,94,0.15)", color: "var(--green)", borderColor: "rgba(34,197,94,0.3)" }}>
                    {actionLoading === "execute" ? "..." : "\u{1f680} Execute"}
                  </button>
                )}

                {(selectedOpp.status === "content_ready" || selectedOpp.status === "approved") && MANUAL_PLATFORMS.includes(selectedOpp.platform) && (
                  <button onClick={() => copyToClipboard(editContent || selectedOpp.suggested_content)}
                    style={{ ...actionBtnStyle, background: "rgba(139,92,246,0.15)", color: "#8b5cf6", borderColor: "#8b5cf644" }}>
                    {copied ? "\u2713 Copiato!" : "\u{1f4cb} Copy to clipboard"}
                  </button>
                )}

                {selectedOpp.suggested_content && (
                  <button onClick={() => { updateContent(selectedOpp.id, editContent); executeOpp(selectedOpp.id); }} disabled={actionLoading === "edit"}
                    style={{ ...actionBtnStyle, background: "rgba(249,115,22,0.15)", color: "var(--orange)", borderColor: "rgba(249,115,22,0.3)" }}>
                    {actionLoading === "edit" ? "..." : "\u270f\ufe0f Edit & Execute"}
                  </button>
                )}

                <button onClick={() => rejectOpp(selectedOpp.id, "later")}
                  style={{ ...actionBtnStyle, background: "rgba(148,163,184,0.1)", color: "var(--text-dim)", borderColor: "var(--border)" }}>
                  {String.fromCodePoint(0x23f0)} Later
                </button>

                <div style={{ display: "flex", gap: 6 }}>
                  <input value={skipReason} onChange={e => setSkipReason(e.target.value)} placeholder="Motivo (opzionale)"
                    style={{ flex: 1, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, padding: "8px 10px", fontSize: 12, color: "var(--text)", boxSizing: "border-box" }} />
                  <button onClick={() => rejectOpp(selectedOpp.id, skipReason || "skipped")} disabled={actionLoading === "reject"}
                    style={{ ...actionBtnStyle, background: "rgba(239,68,68,0.15)", color: "var(--red)", borderColor: "rgba(239,68,68,0.3)", flex: "none", padding: "8px 14px" }}>
                    {actionLoading === "reject" ? "..." : "\u2717 Skip"}
                  </button>
                </div>

                {selectedOpp.suggested_content && (
                  <button onClick={() => approveOpp(selectedOpp.id)}
                    style={{ ...actionBtnStyle, background: "rgba(139,92,246,0.1)", color: "#a78bfa", borderColor: "rgba(139,92,246,0.2)" }}>
                    {String.fromCodePoint(0x1f504)} Regenerate
                  </button>
                )}
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* ═══ BOTTOM BAR ═══ */}
      <footer style={{
        background: "var(--bg-card)", borderTop: "1px solid var(--border)",
        padding: "10px 20px", display: "flex", alignItems: "center", justifyContent: "space-between",
        gap: 16, flexWrap: "wrap", minHeight: 50,
      }}>
        {/* Timeline events */}
        <div style={{ display: "flex", gap: 12, flex: 1, overflowX: "auto" }}>
          {timeline.length === 0 && <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Nessun evento recente</span>}
          {timeline.map((ev, i) => (
            <div key={ev.id || i} style={{
              fontSize: 11, color: "var(--text-dim)", whiteSpace: "nowrap",
              display: "flex", alignItems: "center", gap: 6,
              background: "var(--bg)", borderRadius: 6, padding: "4px 10px",
              border: "1px solid var(--border)",
            }}>
              <span>{PLATFORM_ICONS[ev.platform] || "\u2699\ufe0f"}</span>
              <span style={{ fontFamily: "monospace", fontSize: 10 }}>{timeAgo(ev.created_at)}</span>
              <span>{ev.action_type}</span>
              <span style={{ color: STATUS_COLORS[ev.status] || "var(--text-dim)" }}>{ev.status}</span>
            </div>
          ))}
        </div>

        {/* Agent uptime */}
        <div style={{ fontSize: 12, color: "var(--text-dim)", whiteSpace: "nowrap" }}>
          {agentState.active
            ? `Agent active${agentState.uptime_seconds ? ` since ${formatUptime(agentState.uptime_seconds)}` : ""}`
            : "Agent inactive"
          }
        </div>

        {/* Run scan button */}
        <button onClick={runFullScan}
          style={{
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)", color: "#fff",
            border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 12,
            fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
          }}>
          Run Full Scan Now
        </button>
      </footer>

      {/* ═══ MOBILE DETAIL MODAL ═══ */}
      {mobileDetailOpen && selectedOpp && (
        <div className="mc-mobile-modal" style={{ display: "none" }}>
          {/* This is handled via CSS media query - the aside becomes a modal on mobile */}
        </div>
      )}

      <style>{`
        @keyframes mc-pulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 10px rgba(34,197,94,0.6); }
          50% { opacity: 0.6; box-shadow: 0 0 20px rgba(34,197,94,0.8); }
        }

        /* Desktop: 3 columns */
        @media (min-width: 1024px) {
          .mc-sidebar { display: flex !important; }
          .mc-detail { display: block !important; }
          .mc-detail-close { display: none !important; }
        }

        /* Mobile: stack */
        @media (max-width: 1023px) {
          .mc-sidebar {
            width: 100% !important;
            min-width: 100% !important;
            border-right: none !important;
            border-bottom: 1px solid var(--border) !important;
            max-height: none !important;
            padding: 12px !important;
          }
          .mc-sidebar > div:nth-child(n+3) {
            /* KPI in row on mobile */
          }
          .mc-main {
            min-height: 300px !important;
          }
          .mc-detail {
            position: fixed !important;
            top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
            width: 100% !important; min-width: 100% !important;
            z-index: 1000 !important;
            background: var(--bg-card) !important;
            display: ${mobileDetailOpen && selectedOpp ? "block" : "none"} !important;
          }
          .mc-detail-close { display: block !important; }
        }
      `}</style>
    </div>
  );
}

/* ─── Style helpers ─── */
const filterBtnStyle: React.CSSProperties = {
  fontSize: 11, padding: "4px 8px", borderRadius: 6,
  border: "1px solid var(--border)", cursor: "pointer",
  transition: "all 0.2s", fontWeight: 500,
};

const actionBtnStyle: React.CSSProperties = {
  width: "100%", padding: "10px 16px", borderRadius: 8,
  border: "1px solid", fontSize: 13, fontWeight: 600,
  cursor: "pointer", textAlign: "left" as const,
  transition: "all 0.2s",
};
