"use client";

import { useEffect, useState, useCallback, useRef } from "react";

/* ─── Types ─── */
interface Rule { id: number; rule: string; category: string; priority: number; active: boolean; created_at: string }
interface Plan { id: number; action: string; category: string; timeframe: string; status: string; priority: number; result: string | null; scheduled_at: string | null; completed_at: string | null; created_at: string }
interface Action { id: number; action_type: string; platform: string; target_url: string; content: string; status: string; response: string | null; created_at: string; thread_id?: string; parent_id?: number }
interface Opportunity { id: number; platform: string; url: string; title: string; relevance_score: number; suggested_action: string; suggested_content: string; status: string; created_at: string; platform_icon?: string; rejected_reason?: string; approved_at?: string; generated_at?: string; executed_at?: string }
interface Metric { id: number; date: string; page_views: number; unique_visitors: number; api_calls: number; countries: number; db_packages: number; email_responses: number; new_backlinks: number; devto_views: number; devto_reactions: number; notes: string | null }
interface Dashboard { opps_today: number; actions_today: number; comments_total: number; emails_total: number; queue_count: number; last_run: string | null; metrics_7d: Metric[]; pipeline: Record<string, number> }
interface PlatformStatus { id: number; platform: string; connected: boolean; last_action_at: string | null; actions_today: number; daily_limit: number; api_status: string; notes: string | null; updated_at: string }
interface AgentConfigItem { key: string; value: string; type: string; category: string; label: string; description: string; updated_at: string }
interface RtNotification { type: string; platform?: string; title?: string; url?: string; relevance?: number; author?: string; reactions?: number; suggested_action?: string; article_id?: number; message?: string; id?: string }

type Tab = "dashboard" | "opportunities" | "timeline" | "email" | "plan" | "rules" | "settings";

const PLATFORM_ICONS: Record<string, string> = {
  devto: "\u{1f4dd}", reddit: "\u{1f534}", hn: "\u{1f7e0}", hackernews: "\u{1f7e0}",
  cursor: "\u{1f4bb}", cursor_forum: "\u{1f4bb}", discord: "\u{1f4ac}", discord_claude: "\u{1f4ac}",
  email: "\u{1f4e7}", npm: "\u{1f4e6}", rapidapi: "\u{26a1}", gpt_store: "\u{1f916}",
  internal: "\u{2699}\u{fe0f}", all: "\u{1f30d}",
};

const PLATFORM_LABELS: Record<string, string> = {
  devto: "Dev.to", reddit: "Reddit", hn: "HN", hackernews: "HN",
  cursor: "Cursor", cursor_forum: "Cursor Forum", discord_claude: "Discord",
  email: "Email", npm: "npm", rapidapi: "RapidAPI", gpt_store: "GPT Store",
  internal: "Internal", all: "All",
};

const STATUS_BORDER_COLORS: Record<string, string> = {
  found: "#94a3b8", approved: "#3b82f6", content_ready: "#8b5cf6",
  execute: "#f97316", done: "#22c55e", rejected: "#ef4444",
  skipped: "#4b5563", manual_post: "#f472b6",
};

const PIPELINE_STEPS = ["found", "approved", "content_ready", "execute", "done"];
const PIPELINE_LABELS: Record<string, string> = {
  found: "Found", approved: "Approved", content_ready: "Content Ready",
  execute: "Execute", done: "Done",
};

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "mai";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "adesso";
  if (mins < 60) return `${mins}m fa`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h fa`;
  const days = Math.floor(hours / 24);
  return `${days}g fa`;
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "..." : s;
}

const API = "/api/admin/agent";

async function apiFetch(path: string, opts?: RequestInit) {
  const key = typeof window !== "undefined" ? localStorage.getItem("ds_admin_key") || "" : "";
  const res = await fetch(path, {
    ...opts,
    headers: { "X-API-Key": key, "Content-Type": "application/json", ...(opts?.headers || {}) },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

/* ─── Default prompt values for reset ─── */
const DEFAULT_PROMPTS: Record<string, string> = {
  prompt_comment_devto: "You are a knowledgeable developer commenting on a Dev.to article. Be genuine, add value with real data. NEVER include links. NEVER mention DepScope by name. Keep it under 4 lines. Use data: 14,700+ packages analyzed, 54% score below 60/100. Sound like a peer, not a marketer.",
  prompt_comment_reddit: "You are a developer responding to a Reddit discussion. Be direct, no fluff. Share specific data points. NEVER include links. NEVER self-promote. Max 3-4 sentences.",
  prompt_email_reply: "You are Vincenzo Rubino replying to an email about DepScope. Be brief (3-5 lines), professional but warm. Sign as Vincenzo. Reference the specific topic they mentioned.",
  prompt_article: "You are a technical writer creating a Dev.to article about package health and software supply chain security. Use real data from DepScope analysis of 14,700+ packages. Include code examples with curl commands. At least 800 words. Professional but accessible tone.",
};

/* ─── Toast item type ─── */
interface ToastItem {
  id: string;
  notification: RtNotification;
  visible: boolean;
}

let toastIdCounter = 0;

export default function AgentPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [timeline, setTimeline] = useState<Action[]>([]);
  const [emails, setEmails] = useState<Action[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [platforms, setPlatforms] = useState<PlatformStatus[]>([]);
  const [configs, setConfigs] = useState<AgentConfigItem[]>([]);
  const [configEdits, setConfigEdits] = useState<Record<string, string>>({});
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [filterPlatform, setFilterPlatform] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [editingContent, setEditingContent] = useState<Record<number, string>>({});
  const [newRule, setNewRule] = useState({ rule: "", category: "general", priority: 5 });
  const [newPlan, setNewPlan] = useState({ action: "", category: "general", timeframe: "short", priority: 5 });

  // Real-time agent state
  const [rtActive, setRtActive] = useState(false);
  const [rtRunning, setRtRunning] = useState(false);
  const [rtStatus, setRtStatus] = useState("");
  const [rtPendingCount, setRtPendingCount] = useState(0);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Polling for notifications
  useEffect(() => {
    if (rtActive) {
      const poll = async () => {
        try {
          const data = await apiFetch(`${API}/notifications`);
          setRtActive(data.active);
          setRtRunning(data.running);
          setRtStatus(data.status || "");

          if (data.notifications && data.notifications.length > 0) {
            const newToasts: ToastItem[] = [];
            for (const n of data.notifications) {
              if (n.type === "opportunity" || n.type === "email") {
                const id = `toast-${++toastIdCounter}`;
                newToasts.push({ id, notification: n, visible: true });
              }
            }
            if (newToasts.length > 0) {
              setToasts(prev => [...prev, ...newToasts].slice(-10));
              setRtPendingCount(prev => prev + newToasts.length);
            }
          }
        } catch {
          // ignore polling errors
        }
      };
      poll();
      pollingRef.current = setInterval(poll, 2000);
      return () => {
        if (pollingRef.current) clearInterval(pollingRef.current);
      };
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
  }, [rtActive]);

  // Load initial agent state
  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch(`${API}/state`);
        setRtActive(data.active);
        setRtRunning(data.running);
        setRtStatus(data.status || "");
      } catch {
        // not available yet
      }
    })();
  }, []);

  const toggleAgent = async () => {
    try {
      const data = await apiFetch(`${API}/toggle`, { method: "POST" });
      setRtActive(data.active);
      setRtRunning(data.running);
      if (!data.active) {
        setToasts([]);
        setRtPendingCount(0);
        setRtStatus("Stopped");
      }
    } catch (e) {
      alert("Errore toggle: " + e);
    }
  };

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const approveToast = async (toast: ToastItem) => {
    // Save as opportunity in DB via the standard agent run, or just dismiss
    dismissToast(toast.id);
    setRtPendingCount(prev => Math.max(0, prev - 1));
  };

  const skipToast = (id: string) => {
    dismissToast(id);
    setRtPendingCount(prev => Math.max(0, prev - 1));
  };

  const laterToast = (id: string) => {
    // Just hide from toasts, keep in pending count
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === "dashboard") {
        const [d, p] = await Promise.all([
          apiFetch(`${API}/dashboard`),
          apiFetch(`${API}/platforms`),
        ]);
        setDashboard(d);
        setPlatforms(p);
      } else if (tab === "opportunities") {
        const o = await apiFetch(`${API}/opportunities/all`);
        setOpportunities(o);
      } else if (tab === "timeline") {
        const t = await apiFetch(`${API}/timeline`);
        setTimeline(t);
      } else if (tab === "email") {
        const e = await apiFetch(`${API}/emails`);
        setEmails(e);
      } else if (tab === "plan") {
        const p = await apiFetch(`${API}/plan`);
        setPlans(p);
      } else if (tab === "rules") {
        const r = await apiFetch(`${API}/rules`);
        setRules(r);
      } else if (tab === "settings") {
        const [p, c] = await Promise.all([
          apiFetch(`${API}/platforms`),
          apiFetch(`${API}/config`),
        ]);
        setPlatforms(p);
        setConfigs(c);
        const edits: Record<string, string> = {};
        c.forEach((item: AgentConfigItem) => { edits[item.key] = item.value; });
        setConfigEdits(edits);
      }
    } catch (e) {
      console.error("Load error:", e);
    }
    setLoading(false);
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const runAgent = async () => {
    try {
      await apiFetch(`${API}/run`, { method: "POST" });
      alert("Agent avviato in background");
    } catch (e) { alert("Errore: " + e); }
  };

  const approveOpp = async (id: number) => {
    await apiFetch(`${API}/opportunities/${id}/approve`, { method: "PUT" });
    load();
  };
  const executeOpp = async (id: number) => {
    await apiFetch(`${API}/opportunities/${id}/execute`, { method: "PUT" });
    load();
  };
  const rejectOpp = async (id: number) => {
    const reason = prompt("Motivo del rifiuto:");
    if (reason === null) return;
    await apiFetch(`${API}/opportunities/${id}/reject`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason }) });
    load();
  };
  const skipOpp = async (id: number) => {
    await apiFetch(`${API}/opportunities/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "skipped" }) });
    load();
  };
  const saveContent = async (id: number) => {
    const content = editingContent[id];
    if (!content) return;
    await apiFetch(`${API}/opportunities/${id}/content`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) });
    setEditingContent(prev => { const n = {...prev}; delete n[id]; return n; });
    load();
  };

  const addRule = async () => {
    if (!newRule.rule.trim()) return;
    await apiFetch(`${API}/rules`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newRule) });
    setNewRule({ rule: "", category: "general", priority: 5 });
    load();
  };
  const deleteRule = async (id: number) => {
    await apiFetch(`${API}/rules/${id}`, { method: "DELETE" });
    load();
  };

  const addPlan = async () => {
    if (!newPlan.action.trim()) return;
    await apiFetch(`${API}/plan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newPlan) });
    setNewPlan({ action: "", category: "general", timeframe: "short", priority: 5 });
    load();
  };
  const updatePlan = async (id: number, status: string) => {
    await apiFetch(`${API}/plan/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    load();
  };

  /* ─── Config helpers ─── */
  const saveConfig = async (key: string) => {
    const value = configEdits[key];
    if (value === undefined) return;
    try {
      await apiFetch(`${API}/config/${key}`, { method: "PUT", body: JSON.stringify({ value }) });
      setSavedKeys(prev => new Set(prev).add(key));
      setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete(key); return n; }), 2000);
      setConfigs(prev => prev.map(c => c.key === key ? { ...c, value } : c));
    } catch (e) { alert("Errore salvataggio: " + e); }
  };

  const resetPrompt = async (key: string) => {
    const def = DEFAULT_PROMPTS[key];
    if (!def) return;
    setConfigEdits(prev => ({ ...prev, [key]: def }));
    try {
      await apiFetch(`${API}/config/${key}`, { method: "PUT", body: JSON.stringify({ value: def }) });
      setSavedKeys(prev => new Set(prev).add(key));
      setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete(key); return n; }), 2000);
      setConfigs(prev => prev.map(c => c.key === key ? { ...c, value: def } : c));
    } catch (e) { alert("Errore reset: " + e); }
  };

  const getConfigVal = (key: string) => configEdits[key] ?? "";
  const setConfigVal = (key: string, val: string) => setConfigEdits(prev => ({ ...prev, [key]: val }));
  const getConfigItem = (key: string) => configs.find(c => c.key === key);

  const filteredOpps = opportunities.filter(o => {
    if (filterPlatform !== "all" && o.platform !== filterPlatform) return false;
    if (filterStatus !== "all" && o.status !== filterStatus) return false;
    return true;
  });

  const filteredTimeline = timeline.filter(a => {
    if (filterPlatform !== "all" && a.platform !== filterPlatform) return false;
    return true;
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: "dashboard", label: "Dashboard" },
    { key: "opportunities", label: "Opportunities" },
    { key: "timeline", label: "Timeline" },
    { key: "email", label: "Email" },
    { key: "plan", label: "Plan" },
    { key: "rules", label: "Rules" },
    { key: "settings", label: "Settings" },
  ];

  const relevanceBadge = (score: number) => {
    const color = score >= 8 ? "#22c55e" : score >= 6 ? "#eab308" : score >= 4 ? "#f97316" : "#ef4444";
    return <span style={{ background: color, color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 12, fontWeight: 700 }}>{score}</span>;
  };

  const statusBadge = (status: string) => {
    const color = STATUS_BORDER_COLORS[status] || "#64748b";
    return <span style={{ background: `${color}22`, color, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600, border: `1px solid ${color}44` }}>{status}</span>;
  };

  /* ─── Shared UI components for settings ─── */
  const cardStyle = { background: "#1e293b", borderRadius: 12, padding: 20, border: "1px solid #334155", marginBottom: 16 };
  const cardTitleStyle = { margin: "0 0 16px", fontSize: 16, fontWeight: 700 as const, color: "#f1f5f9" };
  const fieldRowStyle = { display: "flex", alignItems: "center", gap: 12, marginBottom: 12, flexWrap: "wrap" as const };
  const labelStyle = { fontSize: 13, color: "#e2e8f0", fontWeight: 600 as const, minWidth: 180 };
  const descStyle = { fontSize: 11, color: "#64748b", marginTop: 2 };
  const inputStyle = { background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 };
  const selectStyle = { ...inputStyle, minWidth: 120 };
  const btnSaveStyle = (key: string) => ({
    background: savedKeys.has(key) ? "#22c55e" : "#3b82f6", color: "#fff", border: "none", borderRadius: 6,
    padding: "6px 14px", fontSize: 12, fontWeight: 600 as const, cursor: "pointer" as const, minWidth: 70,
  });

  /* ─── Toggle component ─── */
  const Toggle = ({ configKey, warn }: { configKey: string; warn?: boolean }) => {
    const val = getConfigVal(configKey) === "true";
    const item = getConfigItem(configKey);
    return (
      <div style={fieldRowStyle}>
        <div style={{ flex: 1 }}>
          <div style={labelStyle}>{item?.label || configKey}</div>
          <div style={descStyle}>{item?.description}</div>
          {warn && val && <div style={{ fontSize: 11, color: "#ef4444", fontWeight: 700, marginTop: 4 }}>DANGEROUS: agent posts without approval!</div>}
        </div>
        <div
          onClick={async () => {
            const newVal = val ? "false" : "true";
            setConfigVal(configKey, newVal);
            try {
              await apiFetch(`${API}/config/${configKey}`, { method: "PUT", body: JSON.stringify({ value: newVal }) });
              setSavedKeys(prev => new Set(prev).add(configKey));
              setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete(configKey); return n; }), 2000);
              setConfigs(prev => prev.map(c => c.key === configKey ? { ...c, value: newVal } : c));
            } catch (e) { alert("Errore: " + e); }
          }}
          style={{
            width: 48, height: 26, borderRadius: 13, cursor: "pointer",
            background: val ? (warn ? "#ef4444" : "#22c55e") : "#475569",
            position: "relative", transition: "background 0.2s",
          }}
        >
          <div style={{
            width: 20, height: 20, borderRadius: 10, background: "#fff",
            position: "absolute", top: 3, left: val ? 25 : 3,
            transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
          }} />
        </div>
        {savedKeys.has(configKey) && <span style={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>Saved</span>}
      </div>
    );
  };

  /* ─── NumberField component ─── */
  const NumberField = ({ configKey, min, max, step }: { configKey: string; min?: number; max?: number; step?: number }) => {
    const item = getConfigItem(configKey);
    return (
      <div style={fieldRowStyle}>
        <div style={{ flex: 1 }}>
          <div style={labelStyle}>{item?.label || configKey}</div>
          <div style={descStyle}>{item?.description}</div>
        </div>
        <input
          type="number"
          value={getConfigVal(configKey)}
          onChange={e => setConfigVal(configKey, e.target.value)}
          min={min} max={max} step={step}
          style={{ ...inputStyle, width: 90, textAlign: "right" }}
        />
        <button onClick={() => saveConfig(configKey)} style={btnSaveStyle(configKey)}>
          {savedKeys.has(configKey) ? "Saved" : "Save"}
        </button>
      </div>
    );
  };

  /* ─── ModelSelect component ─── */
  const ModelSelect = ({ configKey }: { configKey: string }) => {
    const item = getConfigItem(configKey);
    return (
      <div style={fieldRowStyle}>
        <div style={{ flex: 1 }}>
          <div style={labelStyle}>{item?.label || configKey}</div>
          <div style={descStyle}>{item?.description}</div>
        </div>
        <select
          value={getConfigVal(configKey)}
          onChange={async (e) => {
            const newVal = e.target.value;
            setConfigVal(configKey, newVal);
            try {
              await apiFetch(`${API}/config/${configKey}`, { method: "PUT", body: JSON.stringify({ value: newVal }) });
              setSavedKeys(prev => new Set(prev).add(configKey));
              setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete(configKey); return n; }), 2000);
              setConfigs(prev => prev.map(c => c.key === configKey ? { ...c, value: newVal } : c));
            } catch (e2) { alert("Errore: " + e2); }
          }}
          style={selectStyle}
        >
          <option value="haiku">Haiku (fast/cheap)</option>
          <option value="sonnet">Sonnet (balanced)</option>
          <option value="opus">Opus (best quality)</option>
        </select>
        {savedKeys.has(configKey) && <span style={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>Saved</span>}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 16px", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: "#e2e8f0", background: "#0f172a", minHeight: "100vh" }}>

      {/* ═══ TOAST CONTAINER ═══ */}
      <div style={{
        position: "fixed", bottom: 20, right: 20, zIndex: 1000,
        width: 380, maxHeight: "80vh", overflowY: "auto",
        display: "flex", flexDirection: "column-reverse", gap: 8,
        pointerEvents: "none",
      }}>
        {toasts.map((toast) => {
          const n = toast.notification;
          const isEmail = n.type === "email";
          const borderColor = isEmail ? "#3b82f6" : "#a78bfa";
          return (
            <div
              key={toast.id}
              style={{
                background: "#1e293b",
                border: `1px solid ${borderColor}44`,
                borderLeft: `4px solid ${borderColor}`,
                borderRadius: 12,
                padding: 16,
                boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
                animation: "slideInRight 0.3s ease",
                pointerEvents: "auto",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 18 }}>
                  {isEmail ? "\u{1f4e7}" : (PLATFORM_ICONS[n.platform || ""] || "\u{1f50d}")}
                </span>
                <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#f1f5f9", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {truncate(n.title || "", 50)}
                </span>
                {n.relevance && (
                  <span style={{
                    background: n.relevance >= 8 ? "#22c55e" : n.relevance >= 6 ? "#eab308" : "#f97316",
                    color: "#fff", borderRadius: 4, padding: "2px 6px", fontSize: 11, fontWeight: 700,
                  }}>
                    {n.relevance}
                  </span>
                )}
              </div>
              {n.author && (
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 8 }}>
                  {n.author} {n.reactions ? `| ${n.reactions} reactions` : ""}
                </div>
              )}
              <div style={{ display: "flex", gap: 6 }}>
                {isEmail ? (
                  <>
                    <button onClick={() => { approveToast(toast); setTab("email"); }} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Reply</button>
                    <button onClick={() => skipToast(toast.id)} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" }}>Skip</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => approveToast(toast)} style={{ background: "#22c55e", color: "#fff", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Approve</button>
                    <button onClick={() => skipToast(toast.id)} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" }}>Skip</button>
                    <button onClick={() => laterToast(toast.id)} style={{ background: "#1e293b", color: "#eab308", border: "1px solid #334155", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" }}>Later</button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ═══ STATUS BAR (when agent active) ═══ */}
      {rtActive && rtStatus && (
        <div style={{
          position: "fixed", bottom: 20, left: 20, zIndex: 999,
          background: "#1e293b", border: "1px solid #334155", borderRadius: 8,
          padding: "6px 14px", fontSize: 12, color: "#94a3b8",
          display: "flex", alignItems: "center", gap: 8,
          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: 4,
            background: rtRunning ? "#22c55e" : "#64748b",
            animation: rtRunning ? "pulse 2s infinite" : "none",
          }} />
          <span>{rtStatus}</span>
        </div>
      )}

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, background: "linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Marketing Agent</h1>
            {dashboard?.last_run && (
              <p style={{ margin: "4px 0 0", fontSize: 13, color: "#94a3b8" }}>Ultima esecuzione: {timeAgo(dashboard.last_run)}</p>
            )}
          </div>
          {/* Real-time toggle */}
          <div
            onClick={toggleAgent}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              cursor: "pointer", userSelect: "none",
              background: rtActive ? "rgba(34,197,94,0.1)" : "rgba(100,116,139,0.1)",
              border: `1px solid ${rtActive ? "#22c55e44" : "#33415577"}`,
              borderRadius: 20, padding: "6px 16px",
              transition: "all 0.3s",
            }}
          >
            <div style={{
              width: 12, height: 12, borderRadius: 6,
              background: rtActive ? "#22c55e" : "#64748b",
              boxShadow: rtActive ? "0 0 8px #22c55e88" : "none",
              animation: rtActive ? "pulse 2s infinite" : "none",
              transition: "all 0.3s",
            }} />
            <span style={{
              fontSize: 13, fontWeight: 600,
              color: rtActive ? "#22c55e" : "#64748b",
            }}>
              {rtActive ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {rtPendingCount > 0 && (
            <button
              onClick={() => setTab("opportunities")}
              style={{
                background: "rgba(249,115,22,0.15)", color: "#f97316",
                border: "1px solid #f9731644", borderRadius: 8,
                padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              {rtPendingCount} pending approval
            </button>
          )}
          <a href="/admin" style={{ color: "#60a5fa", fontSize: 13, textDecoration: "none" }}>Analytics</a>
          <a href="/mission-control" style={{ color: "#60a5fa", fontSize: 13, textDecoration: "none" }}>Mission Control</a>
          <button onClick={runAgent} style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Run Agent Now</button>
          <button onClick={load} style={{ background: "#1e293b", color: "#94a3b8", border: "1px solid #334155", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer" }}>{loading ? "..." : "Refresh"}</button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: "1px solid #1e293b", paddingBottom: 8, overflowX: "auto" }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{ background: tab === t.key ? "#1e293b" : "transparent", color: tab === t.key ? "#60a5fa" : "#64748b", border: tab === t.key ? "1px solid #334155" : "1px solid transparent", borderRadius: "8px 8px 0 0", padding: "8px 16px", fontSize: 13, fontWeight: tab === t.key ? 600 : 400, cursor: "pointer", whiteSpace: "nowrap" }}>{t.label}</button>
        ))}
      </div>

      {/* ═══ DASHBOARD ═══ */}
      {tab === "dashboard" && dashboard && (
        <div>
          {/* KPI Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
            {[
              { label: "Opportunita oggi", value: dashboard.opps_today, sub: `${Object.values(dashboard.pipeline).reduce((a, b) => a + b, 0)} totali` },
              { label: "Email", value: dashboard.emails_total, sub: `${dashboard.actions_today} azioni oggi` },
              { label: "Commenti", value: dashboard.comments_total, sub: "totale pubblicati" },
              { label: "In coda", value: dashboard.queue_count, sub: "da processare" },
              { label: "Piattaforme", value: platforms.filter(p => p.connected).length, sub: `/ ${platforms.length} totali` },
            ].map((kpi, i) => (
              <div key={i} style={{ background: "#1e293b", borderRadius: 12, padding: 16, border: "1px solid #334155" }}>
                <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>{kpi.label}</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#f8fafc" }}>{kpi.value}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>{kpi.sub}</div>
              </div>
            ))}
          </div>

          {/* Pipeline */}
          <div style={{ background: "#1e293b", borderRadius: 12, padding: 16, border: "1px solid #334155", marginBottom: 24 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#94a3b8" }}>Pipeline</h3>
            <div style={{ display: "flex", gap: 0, alignItems: "center" }}>
              {PIPELINE_STEPS.map((step, i) => {
                const count = dashboard.pipeline[step] || 0;
                const color = STATUS_BORDER_COLORS[step];
                return (
                  <div key={step} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    <div style={{ background: `${color}22`, border: `2px solid ${color}`, borderRadius: 10, padding: "12px 8px", textAlign: "center", flex: 1, minWidth: 80 }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color }}>{count}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{PIPELINE_LABELS[step]}</div>
                    </div>
                    {i < PIPELINE_STEPS.length - 1 && <div style={{ color: "#334155", fontSize: 18, padding: "0 4px" }}>&rarr;</div>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Metrics chart */}
          {dashboard.metrics_7d.length > 0 && (
            <div style={{ background: "#1e293b", borderRadius: 12, padding: 16, border: "1px solid #334155", marginBottom: 24 }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#94a3b8" }}>Trend 7 giorni</h3>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end", height: 120 }}>
                {dashboard.metrics_7d.map((m, i) => {
                  const maxViews = Math.max(...dashboard.metrics_7d.map(x => x.page_views || 1));
                  const h = Math.max(((m.page_views || 0) / maxViews) * 100, 4);
                  return (
                    <div key={i} style={{ flex: 1, textAlign: "center" }}>
                      <div style={{ background: "linear-gradient(180deg, #3b82f6, #1e40af)", height: h, borderRadius: "4px 4px 0 0", minHeight: 4 }} title={`${m.page_views} views`}></div>
                      <div style={{ fontSize: 10, color: "#64748b", marginTop: 4 }}>{new Date(m.date).toLocaleDateString("it", { day: "2-digit", month: "2-digit" })}</div>
                      <div style={{ fontSize: 10, color: "#94a3b8" }}>{m.page_views}v</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Platform Status */}
          <div style={{ background: "#1e293b", borderRadius: 12, padding: 16, border: "1px solid #334155" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#94a3b8" }}>Piattaforme</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
              {platforms.map(p => (
                <div key={p.platform} style={{ background: "#0f172a", borderRadius: 8, padding: 12, border: `1px solid ${p.connected ? "#22c55e33" : "#33415577"}`, display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 20 }}>{PLATFORM_ICONS[p.platform] || "\u{2699}\u{fe0f}"}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{PLATFORM_LABELS[p.platform] || p.platform}</div>
                    <div style={{ fontSize: 11, color: p.connected ? "#22c55e" : "#64748b" }}>
                      {p.connected ? "Connesso" : "Manuale"} {p.api_status !== "active" && p.api_status !== "manual_only" ? `(${p.api_status})` : ""}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#f8fafc" }}>{p.actions_today}</div>
                    <div style={{ fontSize: 10, color: "#64748b" }}>/{p.daily_limit} oggi</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ OPPORTUNITIES ═══ */}
      {tab === "opportunities" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <select value={filterPlatform} onChange={e => setFilterPlatform(e.target.value)} style={{ background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 12px", fontSize: 13 }}>
              <option value="all">Tutte le piattaforme</option>
              {["devto", "reddit", "hn", "cursor", "email"].map(p => <option key={p} value={p}>{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}</option>)}
            </select>
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 12px", fontSize: 13 }}>
              <option value="all">Tutti gli stati</option>
              {["found", "approved", "content_ready", "execute", "done", "rejected", "manual_post"].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {filteredOpps.length === 0 && <div style={{ color: "#64748b", padding: 40, textAlign: "center" }}>Nessuna opportunita trovata</div>}

          {filteredOpps.map(o => {
            const borderColor = STATUS_BORDER_COLORS[o.status] || "#334155";
            return (
              <div key={o.id} style={{ background: "#1e293b", borderRadius: 10, marginBottom: 12, border: `1px solid #33415577`, borderLeft: `4px solid ${borderColor}`, overflow: "hidden" }}>
                <div style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 8, borderBottom: "1px solid #0f172a" }}>
                  <span style={{ fontSize: 18 }}>{PLATFORM_ICONS[o.platform] || "\u{1f4cb}"}</span>
                  <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>{truncate(o.title, 80)}</span>
                  {relevanceBadge(o.relevance_score)}
                  {statusBadge(o.status)}
                </div>
                <div style={{ padding: "8px 16px 12px" }}>
                  {o.url && !o.url.startsWith("email://") && (
                    <a href={o.url} target="_blank" rel="noopener noreferrer" style={{ color: "#60a5fa", fontSize: 12, wordBreak: "break-all" }}>{truncate(o.url, 80)}</a>
                  )}
                  {o.suggested_content && (
                    <div style={{ marginTop: 8 }}>
                      {editingContent[o.id] !== undefined ? (
                        <div>
                          <textarea
                            value={editingContent[o.id]}
                            onChange={e => setEditingContent(prev => ({ ...prev, [o.id]: e.target.value }))}
                            style={{ width: "100%", minHeight: 100, background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: 8, fontSize: 13, resize: "vertical" }}
                          />
                          <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                            <button onClick={() => saveContent(o.id)} style={{ background: "#22c55e", color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, cursor: "pointer" }}>Salva</button>
                            <button onClick={() => setEditingContent(prev => { const n = {...prev}; delete n[o.id]; return n; })} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, cursor: "pointer" }}>Annulla</button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ background: "#0f172a", borderRadius: 6, padding: 10, fontSize: 13, color: "#cbd5e1", whiteSpace: "pre-wrap", maxHeight: 150, overflow: "auto", lineHeight: 1.5 }}>
                          {o.suggested_content}
                        </div>
                      )}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: 11, color: "#64748b" }}>
                    <span>Trovato: {timeAgo(o.created_at)}</span>
                    {o.approved_at && <span>Approvato: {timeAgo(o.approved_at)}</span>}
                    {o.generated_at && <span>Generato: {timeAgo(o.generated_at)}</span>}
                    {o.executed_at && <span>Eseguito: {timeAgo(o.executed_at)}</span>}
                    {o.rejected_reason && <span style={{ color: "#ef4444" }}>Motivo: {o.rejected_reason}</span>}
                  </div>
                </div>
                <div style={{ padding: "8px 16px 12px", display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {o.status === "found" && (
                    <>
                      <button onClick={() => approveOpp(o.id)} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Approve</button>
                      <button onClick={() => skipOpp(o.id)} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer" }}>Skip</button>
                    </>
                  )}
                  {o.status === "approved" && (
                    <span style={{ fontSize: 12, color: "#eab308", padding: "6px 14px" }}>Generating... (prossimo run)</span>
                  )}
                  {o.status === "content_ready" && (
                    <>
                      <button onClick={() => executeOpp(o.id)} style={{ background: "#f97316", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Execute</button>
                      <button onClick={() => setEditingContent(prev => ({ ...prev, [o.id]: o.suggested_content || "" }))} style={{ background: "#1e293b", color: "#60a5fa", border: "1px solid #334155", borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer" }}>Edit</button>
                      <button onClick={() => rejectOpp(o.id)} style={{ background: "#334155", color: "#ef4444", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer" }}>Reject</button>
                    </>
                  )}
                  {o.status === "execute" && (
                    <span style={{ fontSize: 12, color: "#f97316", padding: "6px 14px" }}>Posting... (prossimo run)</span>
                  )}
                  {o.status === "done" && o.executed_at && (
                    <span style={{ fontSize: 12, color: "#22c55e", padding: "6px 14px" }}>Completato {timeAgo(o.executed_at)}</span>
                  )}
                  {o.status === "manual_post" && (
                    <span style={{ fontSize: 12, color: "#f472b6", padding: "6px 14px" }}>Post manuale richiesto</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ═══ TIMELINE ═══ */}
      {tab === "timeline" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <select value={filterPlatform} onChange={e => setFilterPlatform(e.target.value)} style={{ background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 12px", fontSize: 13 }}>
              <option value="all">Tutte le piattaforme</option>
              {["devto", "reddit", "hn", "cursor", "email", "internal"].map(p => <option key={p} value={p}>{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}</option>)}
            </select>
          </div>

          {filteredTimeline.map(a => (
            <div key={a.id} style={{ background: "#1e293b", borderRadius: 8, padding: "10px 14px", marginBottom: 6, border: "1px solid #334155", display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{ fontSize: 16, marginTop: 2 }}>{PLATFORM_ICONS[a.platform] || "\u{2699}\u{fe0f}"}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 2 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>{a.action_type}</span>
                  {statusBadge(a.status)}
                  <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>{timeAgo(a.created_at)}</span>
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {truncate(a.content || a.target_url || "", 120)}
                </div>
              </div>
            </div>
          ))}
          {filteredTimeline.length === 0 && <div style={{ color: "#64748b", padding: 40, textAlign: "center" }}>Nessuna azione nella timeline</div>}
        </div>
      )}

      {/* ═══ EMAIL ═══ */}
      {tab === "email" && (
        <div>
          {emails.length === 0 && <div style={{ color: "#64748b", padding: 40, textAlign: "center" }}>Nessuna email</div>}
          {emails.map(e => {
            const isSent = e.action_type === "send_email";
            return (
              <div key={e.id} style={{ background: "#1e293b", borderRadius: 8, padding: "12px 14px", marginBottom: 6, border: "1px solid #334155", borderLeft: `3px solid ${isSent ? "#22c55e" : "#3b82f6"}` }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: 14 }}>{isSent ? "\u{2709}\u{fe0f}" : "\u{1f4e8}"}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{isSent ? "Inviata" : "Ricevuta"}</span>
                  <span style={{ fontSize: 12, color: "#60a5fa" }}>{e.target_url}</span>
                  {statusBadge(e.status)}
                  <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>{timeAgo(e.created_at)}</span>
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", whiteSpace: "pre-wrap", maxHeight: 100, overflow: "auto" }}>
                  {e.content}
                </div>
                {e.thread_id && <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>Thread: {e.thread_id}</div>}
              </div>
            );
          })}
        </div>
      )}

      {/* ═══ PLAN ═══ */}
      {tab === "plan" && (
        <div>
          <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginBottom: 16, border: "1px solid #334155", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input value={newPlan.action} onChange={e => setNewPlan({ ...newPlan, action: e.target.value })} placeholder="Nuova azione..." style={{ flex: 1, minWidth: 200, background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 }} />
            <select value={newPlan.timeframe} onChange={e => setNewPlan({ ...newPlan, timeframe: e.target.value })} style={{ background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}>
              <option value="short">Breve</option><option value="medium">Medio</option><option value="long">Lungo</option>
            </select>
            <select value={newPlan.category} onChange={e => setNewPlan({ ...newPlan, category: e.target.value })} style={{ background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}>
              <option value="general">General</option><option value="content">Content</option><option value="outreach">Outreach</option><option value="seo">SEO</option><option value="product">Product</option>
            </select>
            <button onClick={addPlan} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Aggiungi</button>
          </div>

          {["short", "medium", "long"].map(tf => {
            const items = plans.filter(p => p.timeframe === tf);
            if (items.length === 0) return null;
            const tfLabels: Record<string, string> = { short: "Breve termine", medium: "Medio termine", long: "Lungo termine" };
            const completed = items.filter(p => p.status === "completed").length;
            const pct = Math.round((completed / items.length) * 100);
            return (
              <div key={tf} style={{ marginBottom: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#94a3b8" }}>{tfLabels[tf]}</h3>
                  <div style={{ flex: 1, height: 6, background: "#334155", borderRadius: 3 }}>
                    <div style={{ width: `${pct}%`, height: "100%", background: "#22c55e", borderRadius: 3, transition: "width 0.3s" }} />
                  </div>
                  <span style={{ fontSize: 12, color: "#64748b" }}>{pct}%</span>
                </div>
                {items.map(p => (
                  <div key={p.id} style={{ background: "#1e293b", borderRadius: 8, padding: "10px 14px", marginBottom: 4, border: "1px solid #334155", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, color: "#94a3b8", minWidth: 20 }}>[{p.priority}]</span>
                    <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0" }}>{p.action}</span>
                    {statusBadge(p.status)}
                    <div style={{ display: "flex", gap: 4 }}>
                      {p.status === "planned" && <button onClick={() => updatePlan(p.id, "in_progress")} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 4, padding: "3px 8px", fontSize: 11, cursor: "pointer" }}>Start</button>}
                      {p.status === "in_progress" && <button onClick={() => updatePlan(p.id, "completed")} style={{ background: "#22c55e", color: "#fff", border: "none", borderRadius: 4, padding: "3px 8px", fontSize: 11, cursor: "pointer" }}>Complete</button>}
                      {["planned", "in_progress"].includes(p.status) && <button onClick={() => updatePlan(p.id, "cancelled")} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 4, padding: "3px 8px", fontSize: 11, cursor: "pointer" }}>Cancel</button>}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {/* ═══ RULES ═══ */}
      {tab === "rules" && (
        <div>
          <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginBottom: 16, border: "1px solid #334155", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input value={newRule.rule} onChange={e => setNewRule({ ...newRule, rule: e.target.value })} placeholder="Nuova regola..." style={{ flex: 1, minWidth: 200, background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 }} />
            <select value={newRule.category} onChange={e => setNewRule({ ...newRule, category: e.target.value })} style={{ background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}>
              <option value="general">General</option><option value="content">Content</option><option value="outreach">Outreach</option><option value="tone">Tone</option>
            </select>
            <button onClick={addRule} style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Aggiungi</button>
          </div>

          {rules.map(r => (
            <div key={r.id} style={{ background: "#1e293b", borderRadius: 8, padding: "10px 14px", marginBottom: 4, border: "1px solid #334155", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ background: "#3b82f622", color: "#60a5fa", borderRadius: 4, padding: "2px 6px", fontSize: 11 }}>{r.category}</span>
              <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0" }}>{r.rule}</span>
              <span style={{ fontSize: 11, color: "#64748b" }}>P{r.priority}</span>
              <button onClick={() => deleteRule(r.id)} style={{ background: "none", color: "#ef444488", border: "none", fontSize: 14, cursor: "pointer" }}>x</button>
            </div>
          ))}
          {rules.length === 0 && <div style={{ color: "#64748b", padding: 40, textAlign: "center" }}>Nessuna regola</div>}
        </div>
      )}

      {/* ═══ SETTINGS ═══ */}
      {tab === "settings" && (
        <div>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>Connessioni Piattaforme</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12, marginBottom: 24 }}>
            {platforms.map(p => (
              <div key={p.platform} style={{ background: "#1e293b", borderRadius: 10, padding: 16, border: `1px solid ${p.connected ? "#22c55e33" : "#334155"}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 22 }}>{PLATFORM_ICONS[p.platform] || "\u{2699}\u{fe0f}"}</span>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#f1f5f9" }}>{PLATFORM_LABELS[p.platform] || p.platform}</div>
                    <div style={{ fontSize: 11, color: p.connected ? "#22c55e" : "#64748b" }}>{p.api_status}</div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", display: "flex", flexDirection: "column", gap: 4 }}>
                  <div>Stato: <strong style={{ color: p.connected ? "#22c55e" : "#f97316" }}>{p.connected ? "Connesso" : "Non connesso"}</strong></div>
                  <div>Azioni oggi: {p.actions_today} / {p.daily_limit}</div>
                  <div>Ultima azione: {p.last_action_at ? timeAgo(p.last_action_at) : "mai"}</div>
                  {p.notes && <div>Note: {p.notes}</div>}
                </div>
              </div>
            ))}
          </div>

          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Claude AI</h3>
            <ModelSelect configKey="claude_model" />
            <ModelSelect configKey="claude_model_comments" />
            <ModelSelect configKey="claude_model_articles" />
            <ModelSelect configKey="claude_model_emails" />
            <NumberField configKey="claude_max_tokens_day" min={1000} max={500000} step={1000} />
            <div style={fieldRowStyle}>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>{getConfigItem("claude_temperature")?.label || "Temperature"}</div>
                <div style={descStyle}>{getConfigItem("claude_temperature")?.description}</div>
              </div>
              <input
                type="range" min="0" max="1" step="0.1"
                value={getConfigVal("claude_temperature") || "0.7"}
                onChange={e => setConfigVal("claude_temperature", e.target.value)}
                style={{ width: 120, accentColor: "#3b82f6" }}
              />
              <span style={{ fontSize: 13, color: "#e2e8f0", minWidth: 30, textAlign: "right" }}>{getConfigVal("claude_temperature") || "0.7"}</span>
              <button onClick={() => saveConfig("claude_temperature")} style={btnSaveStyle("claude_temperature")}>
                {savedKeys.has("claude_temperature") ? "Saved" : "Save"}
              </button>
            </div>
          </div>

          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Schedule</h3>
            <div style={fieldRowStyle}>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>{getConfigItem("cron_frequency_hours")?.label || "Run Frequency"}</div>
                <div style={descStyle}>{getConfigItem("cron_frequency_hours")?.description}</div>
              </div>
              <select
                value={getConfigVal("cron_frequency_hours")}
                onChange={async (e) => {
                  const newVal = e.target.value;
                  setConfigVal("cron_frequency_hours", newVal);
                  try {
                    await apiFetch(`${API}/config/cron_frequency_hours`, { method: "PUT", body: JSON.stringify({ value: newVal }) });
                    setSavedKeys(prev => new Set(prev).add("cron_frequency_hours"));
                    setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete("cron_frequency_hours"); return n; }), 2000);
                    setConfigs(prev => prev.map(c => c.key === "cron_frequency_hours" ? { ...c, value: newVal } : c));
                  } catch (e2) { alert("Errore: " + e2); }
                }}
                style={selectStyle}
              >
                <option value="1">Ogni ora</option>
                <option value="2">Ogni 2 ore</option>
                <option value="4">Ogni 4 ore</option>
                <option value="6">Ogni 6 ore</option>
                <option value="12">Ogni 12 ore</option>
                <option value="24">Ogni 24 ore</option>
              </select>
              {savedKeys.has("cron_frequency_hours") && <span style={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>Saved</span>}
            </div>
            <div style={fieldRowStyle}>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>Active Hours (UTC)</div>
                <div style={descStyle}>Time window when agent can operate</div>
              </div>
              <input type="number" min={0} max={23} value={getConfigVal("active_hours_start")} onChange={e => setConfigVal("active_hours_start", e.target.value)} style={{ ...inputStyle, width: 60, textAlign: "right" }} />
              <span style={{ color: "#64748b" }}>to</span>
              <input type="number" min={0} max={23} value={getConfigVal("active_hours_end")} onChange={e => setConfigVal("active_hours_end", e.target.value)} style={{ ...inputStyle, width: 60, textAlign: "right" }} />
              <span style={{ color: "#64748b", fontSize: 12 }}>UTC</span>
              <button onClick={async () => { await saveConfig("active_hours_start"); await saveConfig("active_hours_end"); }} style={btnSaveStyle("active_hours_start")}>
                {savedKeys.has("active_hours_start") ? "Saved" : "Save"}
              </button>
            </div>
            <div style={fieldRowStyle}>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>Active Days</div>
                <div style={descStyle}>Days when agent is active (1=Mon, 7=Sun)</div>
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                {[
                  { day: "1", label: "Mon" }, { day: "2", label: "Tue" }, { day: "3", label: "Wed" },
                  { day: "4", label: "Thu" }, { day: "5", label: "Fri" }, { day: "6", label: "Sat" }, { day: "7", label: "Sun" },
                ].map(({ day, label }) => {
                  const days = (getConfigVal("active_days") || "").split(",").map(d => d.trim());
                  const active = days.includes(day);
                  return (
                    <button
                      key={day}
                      onClick={async () => {
                        let newDays: string[];
                        if (active) { newDays = days.filter(d => d !== day); } else { newDays = [...days, day].sort(); }
                        const newVal = newDays.filter(d => d).join(",");
                        setConfigVal("active_days", newVal);
                        try {
                          await apiFetch(`${API}/config/active_days`, { method: "PUT", body: JSON.stringify({ value: newVal }) });
                          setSavedKeys(prev => new Set(prev).add("active_days"));
                          setTimeout(() => setSavedKeys(prev => { const n = new Set(prev); n.delete("active_days"); return n; }), 2000);
                          setConfigs(prev => prev.map(c => c.key === "active_days" ? { ...c, value: newVal } : c));
                        } catch (e) { alert("Errore: " + e); }
                      }}
                      style={{
                        background: active ? "#3b82f6" : "#0f172a", color: active ? "#fff" : "#64748b",
                        border: `1px solid ${active ? "#3b82f6" : "#334155"}`,
                        borderRadius: 6, padding: "4px 8px", fontSize: 11, fontWeight: 600, cursor: "pointer",
                      }}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
              {savedKeys.has("active_days") && <span style={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>Saved</span>}
            </div>
          </div>

          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Platform Limits</h3>
            <NumberField configKey="max_actions_devto" min={0} max={50} />
            <NumberField configKey="max_actions_reddit" min={0} max={20} />
            <NumberField configKey="max_actions_email" min={0} max={50} />
            <NumberField configKey="max_actions_hn" min={0} max={10} />
            <NumberField configKey="max_actions_cursor" min={0} max={20} />
            <NumberField configKey="min_delay_minutes" min={1} max={120} />
            <NumberField configKey="min_relevance_score" min={1} max={10} />
          </div>

          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Automation</h3>
            <Toggle configKey="auto_execute" warn />
            <NumberField configKey="auto_approve_above" min={1} max={10} />
            <NumberField configKey="auto_skip_below" min={1} max={10} />
            <Toggle configKey="auto_generate" />
            <Toggle configKey="notify_email" />
          </div>

          <div style={cardStyle}>
            <h3 style={cardTitleStyle}>Prompt Templates</h3>
            {["prompt_comment_devto", "prompt_comment_reddit", "prompt_email_reply", "prompt_article"].map(key => {
              const item = getConfigItem(key);
              return (
                <div key={key} style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                    <div>
                      <div style={labelStyle}>{item?.label || key}</div>
                      <div style={descStyle}>{item?.description}</div>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => resetPrompt(key)} style={{ background: "#334155", color: "#94a3b8", border: "none", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}>Reset to Default</button>
                      <button onClick={() => saveConfig(key)} style={btnSaveStyle(key)}>
                        {savedKeys.has(key) ? "Saved" : "Save"}
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={getConfigVal(key)}
                    onChange={e => setConfigVal(key, e.target.value)}
                    rows={4}
                    style={{ width: "100%", background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 8, padding: 10, fontSize: 13, resize: "vertical", lineHeight: 1.5, boxSizing: "border-box" }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ CSS Animations ═══ */}
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
