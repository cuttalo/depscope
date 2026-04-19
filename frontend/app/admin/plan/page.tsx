"use client";

import { useEffect, useState } from "react";

// --------------------------------------------------------------------------- //
// Types
// --------------------------------------------------------------------------- //

interface PlanMetrics {
  verticals: {
    packages: number;
    vulnerabilities: number;
    alternatives: number;
    breaking_changes: number;
    errors: number;
    known_bugs: number;
    compat_matrix: number;
  };
  ecosystems: {
    ecosystem: string;
    packages: number;
    vulnerabilities: number;
    alternatives: number;
    breaking_changes: number;
    known_bugs: number;
  }[];
  usage: {
    api_calls_total: number;
    api_calls_30d: number;
    api_calls_7d: number;
    unique_ips_30d: number;
  };
  users: { total: number; active_api_keys: number; by_plan: Record<string, number> };
  revenue: { subscriptions_by_status: Record<string, number>; mrr_eur: number; paying_customers: number };
  distribution: {
    mcp_npm_version_latest: string;
    gpt_store_live: boolean;
    rapidapi_live: boolean;
    total_ecosystems_declared: number;
    ecosystems_with_breaking_or_bugs: number;
  };
}

interface ActionItem {
  id: string;
  area:
    | "distribution"
    | "data"
    | "frontend"
    | "monetization"
    | "reliability"
    | "dx"
    | "growth";
  title: string;
  detail: string;
  impact: "high" | "medium" | "low";
  effort: "XS" | "S" | "M" | "L" | "XL";
  owner: string;
  status: "todo" | "doing" | "done";
}

// --------------------------------------------------------------------------- //
// Action items — the real backlog, ordered by impact/effort
// --------------------------------------------------------------------------- //

const INITIAL_ACTIONS: ActionItem[] = [
  {
    id: "DIST-1",
    area: "distribution",
    title: "Publish MCP server v0.2.0 su npm",
    detail:
      "File aggiornato in /home/deploy/depscope/mcp-server, package.json 0.2.0 pronto. Comando: cd mcp-server && npm publish. Utente logged come depscope su npm.",
    impact: "high",
    effort: "XS",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "DIST-2",
    area: "distribution",
    title: "Primo git commit + push su GitHub",
    detail:
      "Repo vuoto (0 commit). Committare tutto il progetto, push su github.com/cuttalo/depscope. Rende pubblico il lavoro.",
    impact: "high",
    effort: "S",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "DIST-3",
    area: "distribution",
    title: "Submit Smithery + mcp.so",
    detail:
      "Due registry MCP principali. Richiedono solo repo GitHub pubblico + smithery.yaml (già presente). Tra poche ore si è indicizzati.",
    impact: "high",
    effort: "S",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "DIST-4",
    area: "distribution",
    title: "Google Search Console: re-submit sitemap",
    detail:
      "Nuove URL (breaking, compat, errors, bugs, alternatives) vanno comunicate. Google può metterci settimane ad indicizzarle spontaneamente.",
    impact: "medium",
    effort: "XS",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "FE-1",
    area: "frontend",
    title: "Pagine SSR dettaglio /breaking/{eco}/{pkg} e /error/{hash}",
    detail:
      "Hub /explore/* è client-side → non indicizzabile. URL statici per-package sono il vero driver SEO (chi googla stack trace arriva direttamente).",
    impact: "high",
    effort: "M",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DATA-1",
    area: "data",
    title: "Coprire i 8 ecosistemi vuoti (pub, hex, cocoapods, cpan, hackage, cran, conda, homebrew)",
    detail:
      "Dichiariamo 17 ecosistemi ma 8 hanno verticali vuoti. Top 20 pkg/ecosystem con breaking e bugs = 160 entry di credibilità.",
    impact: "medium",
    effort: "L",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DATA-2",
    area: "data",
    title: "Pipeline crawler automatica GitHub changelog → breaking_changes",
    detail:
      "Cron notturno su top-500 package per ecosystem. Parser regex di CHANGELOG.md + sezioni 'BREAKING'. Richiede GitHub token (free 5K req/h).",
    impact: "high",
    effort: "L",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DATA-3",
    area: "data",
    title: "Crawler GitHub issues closed+linked PR → errors",
    detail:
      "Top 100 repo (react, next, prisma, express). Label bug + state closed + comment con fix. Scale errors da 55 a ~500 con dati veri verificabili.",
    impact: "high",
    effort: "L",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "MON-1",
    area: "monetization",
    title: "Attivare Stripe + checkout Piano Plus",
    detail:
      "Stripe config già presente (test keys), manca UI checkout + paywall rate-limit per tier. Senza questo, ZERO revenue possibile.",
    impact: "high",
    effort: "M",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "MON-2",
    area: "monetization",
    title: "Enforce rate limit per tier (anon 200/min, free 500/min, plus 2000/min, enterprise illimitato)",
    detail:
      "Cache Redis esiste. Manca logica differenziata per user.plan in middleware auth. Senza tier non giustifichi il pricing.",
    impact: "medium",
    effort: "S",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "MON-3",
    area: "monetization",
    title: "Enterprise pilot program: 3 aziende gratis in cambio di case study",
    detail:
      "Target: 3 startup AI coding (tipo Continue.dev, Aider, Cline). Instance DepScope dedicata con loro stack priorità. Validazione prezzo enterprise.",
    impact: "high",
    effort: "M",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "REL-1",
    area: "reliability",
    title: "Test suite minimale (pytest + fastapi TestClient)",
    detail:
      "Zero test oggi. Serve almeno: 1 test per endpoint pubblico (18 endpoint), 1 per vertical handler. Evita regressioni quando cambi il DB.",
    impact: "medium",
    effort: "M",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "REL-2",
    area: "reliability",
    title: "CI/CD via GitHub Actions (lint + test + deploy)",
    detail:
      "Oggi tutto manuale via SSH. CI automatica → commit to main si auto-deploya. Richiede rel-1 prima.",
    impact: "medium",
    effort: "M",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "REL-3",
    area: "reliability",
    title: "alerts.py + daily_report.py includere KPI verticali",
    detail:
      "Script esistenti monitorano solo API/DB/disk. Aggiungere alert se counter di una tabella verticale crolla, o se tempo risposta /api/breaking sale.",
    impact: "low",
    effort: "S",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DX-1",
    area: "dx",
    title: "Aggiornare /api-docs con tutti i 13 endpoint nuovi (breaking, bugs, compat, alternatives DB, resolve error)",
    detail:
      "La pagina api-docs è il biglietto da visita per DX. Se mancano i nuovi verticali sembra un prodotto sotto-dimensionato.",
    impact: "medium",
    effort: "S",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DX-2",
    area: "dx",
    title: "SDK Python e Node.js pubblicati (pypi + npm)",
    detail:
      "Non tutti usano MCP. Un `pip install depscope` / `npm install depscope` wrapper con 5 funzioni chiave espande la TAM.",
    impact: "low",
    effort: "M",
    owner: "Claude",
    status: "todo",
  },
  {
    id: "DX-3",
    area: "dx",
    title: "Esempi di integrazione (Cursor mdc, Claude Code hooks, Windsurf cascade)",
    detail:
      "Snippet copy-paste in /integrate. Converte ogni user dev in contributor gratuito (recommanda DepScope al team).",
    impact: "medium",
    effort: "S",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "GROW-1",
    area: "growth",
    title: "Show HN Launch coordinato (post + sub-comment da account alternativo)",
    detail:
      "Già post fatto su HN. Serve SECOND launch sincronizzato con publish MCP npm + pagina /explore/breaking nuova. Front page HN = 5-30k utenti.",
    impact: "high",
    effort: "S",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "GROW-2",
    area: "growth",
    title: "Outreach cold email a 50 founder AI coding agents",
    detail:
      "Target: Cursor, Continue, Aider, Cline, Cody, Codeium, Windsurf. Template di 4 righe: 'questo è DepScope, risolve X, prova con curl Y'.",
    impact: "high",
    effort: "M",
    owner: "Vincenzo",
    status: "todo",
  },
  {
    id: "GROW-3",
    area: "growth",
    title: "Dev.to + Medium articoli tecnici (3 pezzi su error→fix, compat matrix, breaking)",
    detail:
      "Long-tail SEO permanente. Ogni pezzo è una porta d'ingresso con keyword specifica (tipo 'React 19 breaking changes guide').",
    impact: "medium",
    effort: "M",
    owner: "Vincenzo",
    status: "todo",
  },
];

// --------------------------------------------------------------------------- //
// Component
// --------------------------------------------------------------------------- //

const AREA_LABEL: Record<ActionItem["area"], string> = {
  distribution: "Distribuzione",
  data: "Dati",
  frontend: "Frontend/SEO",
  monetization: "Monetizzazione",
  reliability: "Affidabilità",
  dx: "DX/Docs",
  growth: "Crescita",
};

const IMPACT_COLOR: Record<ActionItem["impact"], string> = {
  high: "var(--red)",
  medium: "var(--yellow)",
  low: "var(--text-faded)",
};

const EFFORT_LABEL: Record<ActionItem["effort"], string> = {
  XS: "~30 min",
  S: "~2 h",
  M: "~1 giorno",
  L: "~3-5 giorni",
  XL: "~2 settimane",
};

const STORAGE_KEY = "ds_plan_actions_v1";

function n(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString("it-IT");
}

export default function AdminPlanPage() {
  const [apiKey, setApiKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [metrics, setMetrics] = useState<PlanMetrics | null>(null);
  const [error, setError] = useState("");
  const [actions, setActions] = useState<ActionItem[]>(INITIAL_ACTIONS);
  const [filter, setFilter] = useState<"all" | ActionItem["status"]>("all");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Record<string, ActionItem["status"]>;
        setActions((prev) =>
          prev.map((a) => (parsed[a.id] ? { ...a, status: parsed[a.id] } : a)),
        );
      } catch {}
    }
    const storedKey = localStorage.getItem("ds_admin_key");
    if (storedKey) {
      setApiKey(storedKey);
      void loadWith(storedKey);
    }
  }, []);

  const loadWith = async (key: string) => {
    setError("");
    try {
      const r = await fetch("/api/admin/plan-metrics", {
        headers: { "X-API-Key": key },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d: PlanMetrics = await r.json();
      setMetrics(d);
      setAuthed(true);
      localStorage.setItem("ds_admin_key", key);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Accesso negato");
      setAuthed(false);
    }
  };

  const setStatus = (id: string, status: ActionItem["status"]) => {
    const next = actions.map((a) => (a.id === id ? { ...a, status } : a));
    setActions(next);
    const map = Object.fromEntries(next.map((a) => [a.id, a.status]));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  };

  const resetStatus = () => {
    localStorage.removeItem(STORAGE_KEY);
    setActions(INITIAL_ACTIONS);
  };

  const doneCount = actions.filter((a) => a.status === "done").length;
  const doingCount = actions.filter((a) => a.status === "doing").length;
  const todoCount = actions.filter((a) => a.status === "todo").length;

  const visible =
    filter === "all" ? actions : actions.filter((a) => a.status === filter);

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--border)] rounded-lg p-6">
          <h1 className="text-xl font-semibold mb-1">Admin · Business Plan</h1>
          <p className="text-sm text-[var(--text-dim)] mb-4">
            Solo admin. Inserisci la API key amministrativa.
          </p>
          <input
            type="password"
            placeholder="ds_admin_..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadWith(apiKey)}
            className="w-full px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded text-sm font-mono mb-3"
          />
          <button
            onClick={() => loadWith(apiKey)}
            className="w-full px-4 py-2 bg-[var(--accent)] text-black font-medium rounded"
          >
            Entra
          </button>
          {error && (
            <p className="text-xs text-[var(--red)] mt-3 font-mono">{error}</p>
          )}
        </div>
      </div>
    );
  }

  const m = metrics!;
  const v = m.verticals;
  const popolati = v.alternatives + v.breaking_changes + v.errors + v.known_bugs + v.compat_matrix;
  const ecoFull = m.distribution.ecosystems_with_breaking_or_bugs;
  const ecoDecl = m.distribution.total_ecosystems_declared;
  const coverage = Math.round((popolati / Math.max(v.packages, 1)) * 10000) / 100;

  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <header className="mb-8">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--accent)] mb-2">
            Admin · Business Plan
          </div>
          <h1 className="text-3xl font-semibold text-[var(--text)] mb-2">
            DepScope — piano serio, onesto, eseguibile
          </h1>
          <p className="text-sm text-[var(--text-dim)] max-w-2xl">
            Questa pagina pesca i numeri veri dal database in tempo reale. Le azioni sotto sono tracciabili —
            spunta ciò che hai completato, lo stato si salva nel browser. Aggiornato oggi.
          </p>
        </header>

        {/* Executive summary */}
        <section className="mb-10 border-l-4 border-[var(--accent)] pl-4">
          <h2 className="text-lg font-semibold mb-2">Executive summary</h2>
          <p className="text-sm text-[var(--text)] leading-relaxed">
            DepScope è un&apos;infrastruttura di <em>ground truth</em> per agenti AI che scrivono codice.
            Aggregare registry package + vulnerabilità + errori + compatibilità + breaking changes una volta,
            servirli via MCP/REST a milioni di agenti. Oggi: {n(v.packages)} pacchetti indicizzati su {ecoDecl} ecosistemi
            dichiarati, {n(m.usage.api_calls_total)} chiamate totali, {m.users.total} utenti registrati, 0€ MRR, 0 clienti paganti.
            Siamo in <strong>fase pre-revenue</strong>: prodotto tecnico solido, distribuzione da completare, monetizzazione inattiva.
          </p>
        </section>

        {/* Stato attuale live */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-4">Stato attuale — numeri veri dal DB</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Pacchetti" value={n(v.packages)} sub={`${ecoDecl} ecosistemi`} />
            <Metric label="Vulnerabilità" value={n(v.vulnerabilities)} sub="OSV/CVE" />
            <Metric label="Alternatives" value={n(v.alternatives)} sub="curated" />
            <Metric label="Breaking changes" value={n(v.breaking_changes)} sub={`${ecoFull} eco. coperti`} />
            <Metric label="Errors" value={n(v.errors)} sub="stack-trace → fix" />
            <Metric label="Known bugs" value={n(v.known_bugs)} sub="version-scoped" />
            <Metric label="Compat stacks" value={n(v.compat_matrix)} sub="verified combos" />
            <Metric label="Coverage" value={`${coverage}%`} sub="verticali / packages" />
          </div>

          <h3 className="text-sm font-medium mt-6 mb-2 text-[var(--text-dim)]">Traffico</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="API calls total" value={n(m.usage.api_calls_total)} sub="lifetime (bot esclusi)" />
            <Metric label="30 giorni" value={n(m.usage.api_calls_30d)} sub="" />
            <Metric label="7 giorni" value={n(m.usage.api_calls_7d)} sub="" />
            <Metric label="IP unici 30d" value={n(m.usage.unique_ips_30d)} sub="" />
          </div>

          <h3 className="text-sm font-medium mt-6 mb-2 text-[var(--text-dim)]">Utenti & revenue</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Utenti registrati" value={n(m.users.total)} sub={`${m.users.active_api_keys} API key attive`} />
            <Metric label="Paying customers" value={n(m.revenue.paying_customers)} sub="Stripe non attivo" />
            <Metric label="MRR" value={`${m.revenue.mrr_eur} €`} sub="zero ad oggi" />
            <Metric label="MCP npm" value={`v${m.distribution.mcp_npm_version_latest}`} sub="su disco, da publishare" />
          </div>

          <h3 className="text-sm font-medium mt-6 mb-3 text-[var(--text-dim)]">Copertura per ecosistema</h3>
          <div className="overflow-x-auto border border-[var(--border)] rounded">
            <table className="w-full text-sm">
              <thead className="bg-[var(--surface)] text-[11px] uppercase tracking-wider text-[var(--text-dim)]">
                <tr>
                  <th className="text-left px-3 py-2">Ecosystem</th>
                  <th className="text-right px-3 py-2">Pkg</th>
                  <th className="text-right px-3 py-2">Vulns</th>
                  <th className="text-right px-3 py-2">Alt</th>
                  <th className="text-right px-3 py-2">Breaking</th>
                  <th className="text-right px-3 py-2">Bugs</th>
                  <th className="text-right px-3 py-2">Verticali</th>
                </tr>
              </thead>
              <tbody>
                {m.ecosystems.map((e) => {
                  const hasV = (e.breaking_changes + e.known_bugs + e.alternatives) > 0;
                  return (
                    <tr
                      key={e.ecosystem}
                      className="border-t border-[var(--border)] font-mono tabular-nums"
                    >
                      <td className="px-3 py-2 font-sans font-medium">{e.ecosystem}</td>
                      <td className="text-right px-3 py-2">{n(e.packages)}</td>
                      <td className="text-right px-3 py-2">{n(e.vulnerabilities)}</td>
                      <td className="text-right px-3 py-2">{n(e.alternatives)}</td>
                      <td className="text-right px-3 py-2">{n(e.breaking_changes)}</td>
                      <td className="text-right px-3 py-2">{n(e.known_bugs)}</td>
                      <td className={`text-right px-3 py-2 font-semibold ${hasV ? "text-[var(--green)]" : "text-[var(--red)]"}`}>
                        {hasV ? "✓" : "vuoto"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Mercato */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-3">Mercato & competitor (onesto)</h2>
          <div className="space-y-3 text-sm text-[var(--text)] leading-relaxed">
            <p>
              <strong>Mercato primario</strong>: AI coding agents (Cursor ~500K utenti, Claude Code ~200K, Cline, Continue, Aider, Windsurf, Codeium).
              TAM stimato dev utenti globali: ~30M dev professionisti nel 2026, ~15M toccano agenti AI mensilmente. Mercato cresce &gt;40% YoY.
            </p>
            <p>
              <strong>Competitor diretti</strong>: Socket.dev (supply chain, enterprise 500€+/mese), Snyk (security, pricing enterprise), deps.dev (Google, gratis ma API grezze), Context7 (solo doc librerie, free), libraries.io (metadata grezzi).
              Nessuno fa: 5 verticali integrati + MCP-native + 17 ecosistemi + EU-based.
            </p>
            <p>
              <strong>Moat realistico</strong>: non è il codice (replicabile in 6 mesi da team serio). È la <em>curation dei dati</em> — 177+79+55+38+65 entry verificate a mano oggi, scalabile con pipeline. E la <em>neutralità svizzera</em>: chiunque può integrare, non siamo di Anthropic né di Google.
            </p>
            <p>
              <strong>Window competitivo</strong>: stimo 18-24 mesi prima che Anthropic/Vercel/Google includano intelligence simile nei loro agent nativamente. Dopo, si vive sul moat dati + enterprise self-hosted.
            </p>
          </div>
        </section>

        {/* Revenue model */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-3">Modello revenue — realistico</h2>
          <div className="overflow-x-auto border border-[var(--border)] rounded">
            <table className="w-full text-sm">
              <thead className="bg-[var(--surface)] text-[11px] uppercase tracking-wider text-[var(--text-dim)]">
                <tr>
                  <th className="text-left px-3 py-2">Tier</th>
                  <th className="text-left px-3 py-2">Prezzo</th>
                  <th className="text-left px-3 py-2">Target</th>
                  <th className="text-left px-3 py-2">Scenario 12 mesi</th>
                </tr>
              </thead>
              <tbody className="text-[var(--text)]">
                <tr className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-medium">Free (anon)</td>
                  <td className="px-3 py-2 font-mono">0 €</td>
                  <td className="px-3 py-2">Tutti: AI agents, dev, bot crawler</td>
                  <td className="px-3 py-2">10-50k utenti unici/mese (growth driver)</td>
                </tr>
                <tr className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-medium">Plus (self-serve)</td>
                  <td className="px-3 py-2 font-mono">19 €/mese</td>
                  <td className="px-3 py-2">Dev individuali, rate-limit più alto, analytics proprie</td>
                  <td className="px-3 py-2">50-200 paying → 950-3.800 €/mese</td>
                </tr>
                <tr className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-medium">Team</td>
                  <td className="px-3 py-2 font-mono">99 €/mese</td>
                  <td className="px-3 py-2">Startup 5-30 dev, API keys condivise, dashboard team</td>
                  <td className="px-3 py-2">5-20 team → 495-1.980 €/mese</td>
                </tr>
                <tr className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-medium">Enterprise (self-hosted)</td>
                  <td className="px-3 py-2 font-mono">3-8k €/mese</td>
                  <td className="px-3 py-2">Corpo 200+ dev, on-prem, SLA, custom stack priority</td>
                  <td className="px-3 py-2">2-5 clienti → 6-40k €/mese</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-sm text-[var(--text-dim)] mt-3 leading-relaxed">
            <strong>Target mese 12</strong>: ~8-45k € MRR se distribuzione e monetizzazione partono. <strong>Onestà</strong>: senza attivare Stripe e aprire
            enterprise pilot, ZERO revenue possibile. Oggi il prodotto tecnicamente potrebbe fare 3-5k € MRR subito
            ma il tap è chiuso per mancanza di checkout.
          </p>
        </section>

        {/* Unit economics */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-3">Unit economics (stima conservativa)</h2>
          <ul className="space-y-2 text-sm text-[var(--text)]">
            <li>• <strong>Costo infra</strong>: VM 140 self-hosted su Proxmox esistente = ~0 € marginale. Scaling a 100k utenti/mese richiederebbe upgrade a 8GB RAM (~+15€/mese OVH)</li>
            <li>• <strong>Dominio</strong>: 10,49 €/anno OVH</li>
            <li>• <strong>Email transazionale</strong>: Postfix su VM 130 proprio = 0 €</li>
            <li>• <strong>Stripe fee</strong>: 1,5% + 0,25 € per transazione EU</li>
            <li>• <strong>Crawler AI budget</strong>: 10-50 €/mese di OpenAI/Anthropic se si usa LLM per parsing changelog (opzionale; regex-based è gratis)</li>
            <li>• <strong>Marketing</strong>: 0 € (canale organico: HN, dev.to, Reddit, LinkedIn)</li>
            <li>• <strong>Team</strong>: 1 fondatore (costo opportunità 60-100k €/anno di lavoro full-time non conteggiato qui)</li>
            <li>• <strong>Gross margin</strong>: ~95%+ su ogni € di revenue (costi infra sono fissi e bassi)</li>
          </ul>
        </section>

        {/* Roadmap */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-3">Roadmap 12 mesi — milestone</h2>
          <ol className="space-y-3 text-sm text-[var(--text)]">
            <li><strong>Q2 2026 (Apr-Giu)</strong>: chiudere le 20 action items sotto. Pubblicare MCP npm, primo commit GitHub, Smithery, HN relaunch, pagine SSR dettaglio. Obiettivo: 1k utenti unici/mese.</li>
            <li><strong>Q3 2026 (Lug-Set)</strong>: attivare Stripe, primo paying customer, 3 enterprise pilot in chiusura. Scale dati verticali a 1.000+ entry. Obiettivo: 500 € MRR.</li>
            <li><strong>Q4 2026 (Ott-Dic)</strong>: SDK Python/Node published, primo enterprise paying, case studies. Pipeline crawler automatica su 5K package. Obiettivo: 3k € MRR.</li>
            <li><strong>Q1 2027 (Gen-Mar)</strong>: espansione verticali adiacenti (Docker images, Helm charts). Team hire: 1 dev part-time. Obiettivo: 8k € MRR.</li>
          </ol>
        </section>

        {/* Rischi */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold mb-3">Rischi identificati</h2>
          <div className="space-y-3 text-sm text-[var(--text)]">
            <div>
              <strong className="text-[var(--red)]">R1 — Commoditizzazione (alto)</strong>
              <p className="mt-1 text-[var(--text-dim)]">Anthropic/Google integrano intelligence simile nativamente nei loro agent. Mitigazione: depth su dati + neutralità cross-agent + enterprise self-hosted con SLA.</p>
            </div>
            <div>
              <strong className="text-[var(--yellow)]">R2 — Founder time (medio-alto)</strong>
              <p className="mt-1 text-[var(--text-dim)]">1 persona non basta oltre a 5-10k € MRR. Serve 2º fondatore tecnico o primo hire. Rischio burnout.</p>
            </div>
            <div>
              <strong className="text-[var(--yellow)]">R3 — Dati stale (medio)</strong>
              <p className="mt-1 text-[var(--text-dim)]">Senza crawler automatica, i 79 breaking changes diventano obsoleti in 6-12 mesi. Action DATA-2 è critica.</p>
            </div>
            <div>
              <strong className="text-[var(--yellow)]">R4 — Pricing enterprise mal calibrato (medio)</strong>
              <p className="mt-1 text-[var(--text-dim)]">3-8k €/mese è stima. Potrebbe essere 1k o 20k. Pilot con 3 aziende serve a validare, non a far fatturato subito.</p>
            </div>
            <div>
              <strong className="text-[var(--text-faded)]">R5 — Legali su dati curati (basso)</strong>
              <p className="mt-1 text-[var(--text-dim)]">Se pubblichiamo fix errato che causa danno, potenziale liability. Aggiungere disclaimer + source URL visibile sempre. Già presente.</p>
            </div>
          </div>
        </section>

        {/* Action items */}
        <section className="mb-10">
          <div className="flex items-end justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold">Action items — lista eseguibile</h2>
              <p className="text-xs text-[var(--text-dim)] mt-1">
                {todoCount} da fare · {doingCount} in corso · {doneCount} fatte. Lo stato si salva nel browser.
              </p>
            </div>
            <div className="flex gap-2">
              {(["all", "todo", "doing", "done"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`text-xs px-3 py-1 rounded border ${
                    filter === f
                      ? "bg-[var(--accent)] text-black border-[var(--accent)]"
                      : "border-[var(--border)] text-[var(--text-dim)]"
                  }`}
                >
                  {f === "all" ? "tutte" : f === "todo" ? "da fare" : f === "doing" ? "in corso" : "fatte"}
                </button>
              ))}
              <button
                onClick={resetStatus}
                className="text-xs px-3 py-1 rounded border border-[var(--border)] text-[var(--text-faded)]"
                title="Reset stato locale"
              >
                reset
              </button>
            </div>
          </div>

          <div className="overflow-x-auto border border-[var(--border)] rounded">
            <table className="w-full text-sm">
              <thead className="bg-[var(--surface)] text-[11px] uppercase tracking-wider text-[var(--text-dim)]">
                <tr>
                  <th className="text-left px-3 py-2">ID</th>
                  <th className="text-left px-3 py-2">Area</th>
                  <th className="text-left px-3 py-2">Azione</th>
                  <th className="text-left px-3 py-2">Impatto</th>
                  <th className="text-left px-3 py-2">Effort</th>
                  <th className="text-left px-3 py-2">Owner</th>
                  <th className="text-left px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((a) => (
                  <tr key={a.id} className="border-t border-[var(--border)] align-top">
                    <td className="px-3 py-3 font-mono text-xs text-[var(--text-faded)]">{a.id}</td>
                    <td className="px-3 py-3">
                      <span className="text-xs px-2 py-0.5 rounded bg-[var(--surface)] text-[var(--text-dim)]">
                        {AREA_LABEL[a.area]}
                      </span>
                    </td>
                    <td className="px-3 py-3 max-w-lg">
                      <div className="font-medium text-[var(--text)]">{a.title}</div>
                      <div className="text-xs text-[var(--text-dim)] mt-1 leading-relaxed">{a.detail}</div>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className="text-xs font-mono uppercase"
                        style={{ color: IMPACT_COLOR[a.impact] }}
                      >
                        {a.impact}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-xs font-mono text-[var(--text-dim)]" title={EFFORT_LABEL[a.effort]}>
                      {a.effort}
                    </td>
                    <td className="px-3 py-3 text-xs font-mono text-[var(--text-dim)]">{a.owner}</td>
                    <td className="px-3 py-3">
                      <select
                        value={a.status}
                        onChange={(e) =>
                          setStatus(a.id, e.target.value as ActionItem["status"])
                        }
                        className={`text-xs px-2 py-1 rounded bg-[var(--bg)] border border-[var(--border)] ${
                          a.status === "done"
                            ? "text-[var(--green)]"
                            : a.status === "doing"
                              ? "text-[var(--yellow)]"
                              : "text-[var(--text-dim)]"
                        }`}
                      >
                        <option value="todo">da fare</option>
                        <option value="doing">in corso</option>
                        <option value="done">fatta</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Next moves */}
        <section className="mb-10 bg-[var(--surface)] border border-[var(--border)] rounded p-5">
          <h2 className="text-lg font-semibold mb-2">La mia raccomandazione onesta — ordine temporale</h2>
          <ol className="list-decimal list-inside space-y-2 text-sm text-[var(--text)]">
            <li><strong>Questa settimana</strong>: DIST-1, DIST-2, DIST-3, DIST-4 (tutte &lt; 2h ciascuna). Sblocca la distribuzione.</li>
            <li><strong>Prossime 2 settimane</strong>: FE-1 (pagine SSR dettaglio) + DX-1 (api-docs updated). Queste + la distribuzione = prime 1k utenti unici al mese.</li>
            <li><strong>Mese 1</strong>: MON-1 (Stripe attivato). Senza paywall funzionante, nessuno vi crederà "prodotto".</li>
            <li><strong>Mese 2</strong>: MON-3 (3 enterprise pilot). Valida prezzo reale + genera case study.</li>
            <li><strong>Mese 3</strong>: DATA-2 + DATA-3 (pipeline crawler). Senza dati freschi, il moat dura 6 mesi al massimo.</li>
            <li><strong>Mese 4+</strong>: REL-1, REL-2, DX-2 (igiene professionale che paga lungo termine).</li>
          </ol>
          <p className="text-xs text-[var(--text-faded)] mt-4 leading-relaxed">
            Zero azione su DATA-1 (8 ecosistemi vuoti) fino a mese 3: non vale lo sforzo finché non hai traction sulla coppia eco già servite. Copertura perfetta prima di product-market fit è over-engineering.
          </p>
        </section>

        <footer className="pt-6 border-t border-[var(--border)] text-xs text-[var(--text-faded)]">
          Metrica aggiornata in tempo reale dal DB. Stato azioni salvato in localStorage.
          Pagina solo admin — non indicizzata, non accessibile senza API key amministrativa.
        </footer>
      </main>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3">
      <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-faded)] mb-1">
        {label}
      </div>
      <div className="text-xl font-semibold tabular-nums text-[var(--text)]">{value}</div>
      {sub && <div className="text-[10px] text-[var(--text-dim)] mt-0.5">{sub}</div>}
    </div>
  );
}
