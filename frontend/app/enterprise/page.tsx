"use client";

import { useState } from "react";
import { Footer } from "../../components/ui";

export default function EnterprisePage() {
  const [form, setForm] = useState({
    email: "",
    company: "",
    use_case: "",
    team_size: "",
  });
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email.trim()) return;
    setStatus("sending");
    setError("");
    try {
      const body = {
        email: form.email.trim(),
        company: form.company.trim(),
        subject: "Enterprise waitlist — DepScope",
        body:
          `Team size: ${form.team_size || "n/a"}\n` +
          `Use case: ${form.use_case || "n/a"}\n` +
          `Company: ${form.company || "n/a"}`,
        type: "enterprise",
        consent: true,
        source: "enterprise_waitlist",
      };
      const r = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "send failed");
    }
  };

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Hero */}
        <header className="mb-12 text-center">
          <div className="inline-block text-[11px] font-mono text-[var(--accent)] tracking-[0.2em] uppercase mb-3">
            Coming Q1 2027 · Waitlist open
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4 leading-[1.1]">
            DepScope for Enterprise
          </h1>
          <p className="text-base text-[var(--text-dim)] max-w-2xl mx-auto leading-relaxed">
            Private MCP server, SSO, audit export, dedicated support. Same agent-safety
            intelligence your team already uses — wrapped in the guarantees that pass
            procurement review.
          </p>
        </header>

        {/* Feature matrix */}
        <section className="mb-12 grid md:grid-cols-2 gap-3">
          {[
            {
              title: "Private MCP + API",
              body: "Dedicated instance, your IP allowlist, your data residency (EU / US). Zero shared infrastructure.",
            },
            {
              title: "SSO + RBAC",
              body: "Okta / Azure AD / Google Workspace. Admin console with per-user scopes, audit trail, SCIM sync.",
            },
            {
              title: "Audit export",
              body: "CycloneDX + SPDX SBOM every scan, streamed to your S3 / Splunk / Datadog. SOC2-ready evidence pack.",
            },
            {
              title: "SLA + support",
              body: "99.95% uptime, 1h response on P0, dedicated Slack channel with engineer on the other side (not a bot).",
            },
            {
              title: "Custom intel",
              body: "Your internal registry, your allowlist, your deprecated-package rules. Curated historical compromise KB per your industry.",
            },
            {
              title: "Usage analytics",
              body: "Per-team dashboards: which agents ask what, hallucination rate by model, blocked installs, TCO savings.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-lg p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="text-sm font-semibold mb-1.5 text-[var(--text)]">{f.title}</div>
              <p className="text-xs leading-relaxed text-[var(--text-dim)]">{f.body}</p>
            </div>
          ))}
        </section>

        {/* Trust strip */}
        <section className="mb-12 rounded-lg p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { v: "19", label: "Ecosystems", sub: "npm · PyPI · Cargo · Go · Maven · NuGet · …" },
              { v: "CC0", label: "Open dataset", sub: "Hallucination Benchmark, public domain" },
              { v: "EU", label: "Data residency", sub: "GDPR-compliant, IP-hashed, no PII on disk" },
              { v: "MIT", label: "Public core", sub: "Open API + MCP server on GitHub" },
            ].map((s) => (
              <div key={s.label}>
                <div className="text-2xl font-semibold text-[var(--accent)] tabular-nums">{s.v}</div>
                <div className="text-xs font-mono uppercase tracking-wider text-[var(--text-dim)] mt-1">{s.label}</div>
                <div className="text-[10px] text-[var(--text-faded)] mt-0.5">{s.sub}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Waitlist form */}
        <section
          id="waitlist"
          className="rounded-lg p-6 mb-12"
          style={{ background: "var(--bg-card)", border: "1px solid var(--accent)" }}
        >
          <h2 className="text-xl font-semibold mb-2">Get early access</h2>
          <p className="text-sm text-[var(--text-dim)] mb-5">
            First 50 teams on the waitlist get: design-partner pricing (lifetime),
            monthly 1:1 calls during beta, feature input on the roadmap.
          </p>

          {status === "sent" ? (
            <div
              className="rounded p-4 text-sm"
              style={{
                background: "color-mix(in srgb, var(--green) 10%, transparent)",
                border: "1px solid var(--green)",
                color: "var(--green)",
              }}
            >
              <strong>You're on the waitlist.</strong> We'll reach out within 48h from{" "}
              <code className="font-mono text-xs">depscope@cuttalo.com</code>.
              In the meantime, grab the free MCP server at{" "}
              <a href="/integrate" className="underline">
                /integrate
              </a>
              .
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-3">
              <div className="grid md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-1">
                    Work email *
                  </label>
                  <input
                    type="email"
                    required
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="cto@yourcompany.com"
                    className="w-full bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    value={form.company}
                    onChange={(e) => setForm({ ...form, company: e.target.value })}
                    placeholder="Acme Corp"
                    className="w-full bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
                  />
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-1">
                    Dev team size
                  </label>
                  <select
                    value={form.team_size}
                    onChange={(e) => setForm({ ...form, team_size: e.target.value })}
                    className="w-full bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
                  >
                    <option value="">Select…</option>
                    <option>1–10</option>
                    <option>11–50</option>
                    <option>51–200</option>
                    <option>201–1000</option>
                    <option>1000+</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)] mb-1">
                    Main driver
                  </label>
                  <select
                    value={form.use_case}
                    onChange={(e) => setForm({ ...form, use_case: e.target.value })}
                    className="w-full bg-[var(--bg-input)] border border-[var(--border)] rounded px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
                  >
                    <option value="">Select…</option>
                    <option>AI coding agent safety (Claude Code / Cursor / Copilot)</option>
                    <option>Supply-chain security / procurement</option>
                    <option>SOC2 / ISO 27001 evidence</option>
                    <option>SBOM / CycloneDX generation at scale</option>
                    <option>EU Cyber Resilience Act compliance</option>
                    <option>Internal dev platform integration</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2 flex-wrap">
                <button
                  type="submit"
                  disabled={status === "sending" || !form.email.trim()}
                  className="px-5 py-2 rounded bg-[var(--accent)] text-black text-sm font-medium hover:bg-[var(--accent-dim)] transition disabled:opacity-40"
                >
                  {status === "sending" ? "Sending…" : "Join waitlist"}
                </button>
                <span className="text-[11px] text-[var(--text-faded)]">
                  No spam, no third parties. GDPR-compliant — see{" "}
                  <a href="/privacy" className="underline">
                    privacy
                  </a>
                  .
                </span>
              </div>
              {status === "error" && (
                <p className="text-xs text-[var(--red)] font-mono">Error: {error}</p>
              )}
            </form>
          )}
        </section>

        {/* In the meantime */}
        <section className="text-center">
          <p className="text-sm text-[var(--text-dim)] mb-4">
            Don't want to wait? <strong className="text-[var(--text)]">DepScope free</strong> is
            already running in production — same core intelligence, minus the enterprise
            wrapper.
          </p>
          <div className="flex justify-center gap-3 flex-wrap">
            <a
              href="/integrate"
              className="px-4 py-2 rounded bg-[var(--accent)]/15 text-[var(--accent)] text-sm hover:bg-[var(--accent)]/25 transition"
            >
              Wire the free MCP →
            </a>
            <a
              href="/benchmark"
              className="px-4 py-2 rounded border border-[var(--border)] text-[var(--text-dim)] text-sm hover:bg-[var(--bg-hover)] transition"
            >
              See the benchmark
            </a>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
