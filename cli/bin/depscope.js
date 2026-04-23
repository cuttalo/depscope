#!/usr/bin/env node
/**
 * depscope-cli — thin HTTP wrapper over https://depscope.dev
 *
 * Usage:
 *   depscope check npm/express        # full JSON (≈2k tokens)
 *   depscope prompt pypi/requests     # LLM-optimized brief (≈500 tokens, text)
 *   depscope brief pypi/requests      # alias for prompt
 *   depscope scan package-lock.json   # audit a whole lockfile
 *   depscope scan requirements.txt
 *   depscope sbom package-lock.json > sbom.cdx.json    # CycloneDX output
 *   depscope alt npm/request          # suggested alternatives
 *   depscope malicious --live         # real-time SSE stream (no auth)
 *
 * Short-hands:
 *   depscope npm/express              # == check
 *   depscope express                  # == check npm/express (npm default)
 *
 * Exit codes:
 *   0   safe_to_use / update_required / find_alternative
 *   1   do_not_use OR malicious OR historical compromise match
 *   2   network / not found
 *   3   usage error
 *
 * No auth, no config, no telemetry. Hit https://depscope.dev/api-docs for
 * the full API reference.
 */
"use strict";

const API = process.env.DEPSCOPE_API_URL || "https://depscope.dev";
const UA = `depscope-cli/0.1.0 node/${process.version.slice(1)}`;
const fs = require("node:fs");
const path = require("node:path");

const COLOR = process.stdout.isTTY && !process.env.NO_COLOR;
const c = {
  reset: COLOR ? "\x1b[0m" : "",
  bold: COLOR ? "\x1b[1m" : "",
  dim: COLOR ? "\x1b[2m" : "",
  red: COLOR ? "\x1b[31m" : "",
  green: COLOR ? "\x1b[32m" : "",
  yellow: COLOR ? "\x1b[33m" : "",
  blue: COLOR ? "\x1b[34m" : "",
  cyan: COLOR ? "\x1b[36m" : "",
};

function usage() {
  console.log(`${c.bold}depscope${c.reset} — package intelligence for humans and agents

${c.bold}Usage${c.reset}
  depscope <command> <ecosystem>/<package>[@<version>]
  depscope <ecosystem>/<package>            shortcut for check
  depscope <package>                         assumes npm

${c.bold}Commands${c.reset}
  ${c.cyan}check${c.reset}      full JSON (${c.dim}health, vulns, license_risk, historical_compromise${c.reset})
  ${c.cyan}prompt${c.reset}     LLM-optimized plain-text brief (~500 tokens)
  ${c.cyan}brief${c.reset}      alias for prompt
  ${c.cyan}alt${c.reset}        curated alternatives
  ${c.cyan}scan${c.reset}       audit a lockfile (${c.dim}package-lock.json, requirements.txt, Pipfile.lock, poetry.lock, Cargo.lock, go.sum, ...${c.reset})
  ${c.cyan}sbom${c.reset}       emit CycloneDX SBOM from a lockfile
  ${c.cyan}malicious${c.reset}  ${c.dim}--live${c.reset}: real-time SSE stream of new malicious advisories

${c.bold}Examples${c.reset}
  depscope check npm/express
  depscope prompt pypi/requests
  depscope express
  depscope alt npm/moment
  depscope scan package-lock.json
  depscope scan poetry.lock
  depscope sbom Cargo.lock > sbom.cdx.json
  depscope malicious --live

${c.bold}Docs${c.reset} ${API}/api-docs  ·  ${c.bold}MCP${c.reset} https://mcp.depscope.dev/mcp
`);
}

function parsePkgArg(arg) {
  // Accept "npm/express" or "pypi/@anthropic-ai/sdk" or plain "express" (default npm).
  if (!arg) return null;
  if (!arg.includes("/")) return { ecosystem: "npm", pkg: arg };
  const slash = arg.indexOf("/");
  const eco = arg.slice(0, slash).toLowerCase();
  const pkg = arg.slice(slash + 1);
  return { ecosystem: eco, pkg };
}

async function httpJSON(path, opts = {}) {
  const url = API + path;
  const res = await fetch(url, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      "User-Agent": UA,
      "Accept-Encoding": "gzip, br",
      "Accept": opts.accept || "application/json",
    },
  });
  if (res.status === 404) {
    const body = await res.json().catch(() => ({}));
    return { status: 404, body };
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return { status: 200, body: await res.json() };
  return { status: 200, body: await res.text() };
}

async function cmdCheck(pkgArg, { format = "pretty" } = {}) {
  const p = parsePkgArg(pkgArg);
  if (!p) { usage(); process.exit(3); }
  const r = await httpJSON(`/api/check/${p.ecosystem}/${encodeURIComponent(p.pkg)}`);
  if (r.status === 404) {
    const d = r.body.detail || r.body;
    console.log(`${c.red}${c.bold}not_found${c.reset} ${p.ecosystem}/${p.pkg}`);
    const ts = d.typosquat;
    if (ts && ts.is_suspected_typosquat) {
      console.log(`${c.yellow}⚠ typosquat${c.reset} of ${c.cyan}${ts.likely_target}${c.reset} (distance ${ts.distance})`);
    }
    const dym = d.did_you_mean || [];
    if (dym.length) {
      console.log(`${c.dim}did you mean:${c.reset}`);
      for (const m of dym.slice(0, 5)) {
        console.log(`  • ${p.ecosystem}/${m.name} ${c.dim}(health ${m.health_score || "—"})${c.reset}`);
      }
    }
    process.exit(2);
  }
  const d = r.body;
  if (format === "json") { console.log(JSON.stringify(d, null, 2)); return 0; }
  const rec = d.recommendation || {};
  const action = rec.action || "unknown";
  const actColor =
    action === "do_not_use" ? c.red :
    action === "find_alternative" || action === "update_required" ? c.yellow :
    action === "safe_to_use" ? c.green : c.dim;
  console.log(`${c.bold}${p.ecosystem}/${d.package}${c.reset} ${c.dim}@${d.latest_version}${c.reset}`);
  if (d.description) console.log(c.dim + d.description.slice(0, 100) + c.reset);
  console.log("");
  console.log(`${actColor}${c.bold}${action.toUpperCase().replace(/_/g, " ")}${c.reset}  ${rec.summary || ""}`);
  if (d.health) {
    const s = d.health.score;
    const sc = s >= 80 ? c.green : s >= 60 ? c.yellow : c.red;
    console.log(`Health:     ${sc}${s}/100${c.reset} (${d.health.risk})`);
  }
  const v = d.vulnerabilities || {};
  const vColor = v.critical ? c.red : v.high ? c.yellow : c.green;
  console.log(`Vulns:      ${vColor}${v.count ?? 0}${c.reset}  ${c.dim}(${v.critical || 0} crit, ${v.high || 0} high, ${v.medium || 0} med)${c.reset}`);
  if (d.license_risk && d.license_risk !== "unknown") {
    const lr = d.license_risk;
    const lc = lr === "permissive" ? c.green : lr === "network_copyleft" || lr === "proprietary" ? c.red : c.yellow;
    console.log(`License:    ${d.license}  ${lc}${lr.replace(/_/g, " ")}${c.reset}`);
  } else if (d.license) {
    console.log(`License:    ${d.license}`);
  }
  if (d.historical_compromise?.count) {
    const hc = d.historical_compromise;
    if (hc.matches_current_version) {
      console.log(`${c.red}${c.bold}⚠ historical compromise matches this version${c.reset}`);
    } else {
      console.log(`${c.yellow}⚠ ${hc.count} historical compromise incident(s) on record${c.reset}`);
    }
  }
  if (rec.alternatives?.length) {
    console.log(`Alternatives: ${rec.alternatives.slice(0, 3).map(a => c.cyan + a.name + c.reset).join(", ")}`);
  }
  console.log(`${c.dim}${API}/pkg/${p.ecosystem}/${d.package}${c.reset}`);
  return action === "do_not_use" || d.historical_compromise?.matches_current_version ? 1 : 0;
}

async function cmdPrompt(pkgArg) {
  const p = parsePkgArg(pkgArg);
  if (!p) { usage(); process.exit(3); }
  const r = await httpJSON(`/api/prompt/${p.ecosystem}/${encodeURIComponent(p.pkg)}`, { accept: "text/plain" });
  if (r.status === 404) {
    console.log(`not_found ${p.ecosystem}/${p.pkg}`);
    process.exit(2);
  }
  console.log(r.body);
  return 0;
}

async function cmdAlt(pkgArg) {
  const p = parsePkgArg(pkgArg);
  if (!p) { usage(); process.exit(3); }
  const r = await httpJSON(`/api/alternatives/${p.ecosystem}/${encodeURIComponent(p.pkg)}`);
  if (r.status === 404) {
    console.log(`not_found ${p.ecosystem}/${p.pkg}`);
    process.exit(2);
  }
  const alts = r.body.alternatives || [];
  if (!alts.length) {
    console.log(`${c.dim}no curated alternatives for ${p.ecosystem}/${p.pkg}${c.reset}`);
    return 0;
  }
  console.log(`${c.bold}Alternatives to ${p.ecosystem}/${p.pkg}:${c.reset}`);
  for (const a of alts) {
    console.log(`  ${c.cyan}${a.name || a.package}${c.reset} ${c.dim}${a.reason || ""}${c.reset}`);
  }
  return 0;
}

async function cmdScan(lockfilePath, { format = "native" } = {}) {
  if (!lockfilePath) { console.error("depscope scan <lockfile>"); process.exit(3); }
  if (!fs.existsSync(lockfilePath)) { console.error(`file not found: ${lockfilePath}`); process.exit(3); }
  const content = fs.readFileSync(lockfilePath, "utf8");
  const kind = path.basename(lockfilePath);
  const body = JSON.stringify({ lockfile: content, lockfile_kind: kind, format });
  const res = await fetch(API + "/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": UA, "Accept-Encoding": "gzip, br" },
    body,
  });
  if (!res.ok) {
    console.error(`HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    process.exit(2);
  }
  const d = await res.json();
  if (format !== "native") { console.log(JSON.stringify(d, null, 2)); return 0; }
  console.log(`${c.bold}Scan: ${lockfilePath}${c.reset}`);
  console.log(`ecosystem: ${d.ecosystem}  packages: ${d.total || d.packages?.length}`);
  const risk = d.project_risk;
  const riskC = risk === "critical" ? c.red : risk === "high" ? c.red : risk === "moderate" ? c.yellow : c.green;
  console.log(`project_risk: ${riskC}${risk}${c.reset}`);
  console.log("");
  const pkgs = d.packages || [];
  let redCount = 0;
  for (const p of pkgs) {
    if (p.error) {
      console.log(`  ${c.red}✗${c.reset} ${p.package} ${c.dim}${p.error}${c.reset}`);
      continue;
    }
    const r = p.recommendation || "unknown";
    const sym = r === "do_not_use" ? `${c.red}⨯` : r === "find_alternative" || r === "update_required" ? `${c.yellow}!` : `${c.green}✓`;
    console.log(`  ${sym}${c.reset} ${p.package} ${c.dim}@${p.requested_version || p.latest_version}${c.reset}  ${c.dim}${r}${c.reset}`);
    if (r === "do_not_use") redCount++;
  }
  return redCount > 0 ? 1 : 0;
}

async function cmdSbom(lockfilePath) {
  if (!lockfilePath) { console.error("depscope sbom <lockfile>"); process.exit(3); }
  const content = fs.readFileSync(lockfilePath, "utf8");
  const kind = path.basename(lockfilePath);
  const body = JSON.stringify({ lockfile: content, lockfile_kind: kind, format: "cyclonedx" });
  const res = await fetch(API + "/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": UA },
    body,
  });
  if (!res.ok) { console.error(`HTTP ${res.status}`); process.exit(2); }
  process.stdout.write(await res.text());
  return 0;
}

async function cmdMalicious(flag) {
  if (flag !== "--live") { console.error("depscope malicious --live"); process.exit(3); }
  console.log(`${c.dim}subscribing to ${API}/api/live/malicious …${c.reset}`);
  const res = await fetch(API + "/api/live/malicious", {
    headers: { "User-Agent": UA, "Accept": "text/event-stream" },
  });
  if (!res.ok || !res.body) { console.error(`HTTP ${res.status}`); process.exit(2); }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const evt = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const lines = evt.split("\n");
      const event = lines.find(l => l.startsWith("event: "))?.slice(7) || "message";
      const data = lines.find(l => l.startsWith("data: "))?.slice(6);
      if (event === "advisory" && data) {
        try {
          const d = JSON.parse(data);
          const t = new Date((d.published_at || Date.now())).toISOString().slice(0, 19).replace("T", " ");
          const replay = d.replay ? `${c.dim}(replay)${c.reset} ` : `${c.red}${c.bold}NEW${c.reset}     `;
          console.log(`${t}  ${replay}${c.red}${d.ecosystem}${c.reset}/${d.package}  ${c.dim}${d.summary || ""}${c.reset}`);
        } catch {}
      }
    }
  }
  return 0;
}

async function main() {
  const args = process.argv.slice(2);
  if (!args.length || args[0] === "-h" || args[0] === "--help") { usage(); process.exit(0); }
  const cmd = args[0];
  try {
    switch (cmd) {
      case "check":     process.exit(await cmdCheck(args[1]));
      case "prompt":
      case "brief":     process.exit(await cmdPrompt(args[1]));
      case "alt":
      case "alternatives": process.exit(await cmdAlt(args[1]));
      case "scan":      process.exit(await cmdScan(args[1]));
      case "sbom":      process.exit(await cmdSbom(args[1]));
      case "malicious": process.exit(await cmdMalicious(args[1]));
      default:
        // Shortcut: first arg looks like eco/pkg or plain pkg -> check
        if (cmd.startsWith("-")) { usage(); process.exit(3); }
        process.exit(await cmdCheck(cmd));
    }
  } catch (e) {
    console.error(`${c.red}error:${c.reset} ${e.message}`);
    process.exit(2);
  }
}

main();
