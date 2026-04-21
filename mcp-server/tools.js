/**
 * DepScope MCP — shared tool definitions and dispatcher.
 * Consumed by both the stdio entry point (index.js) and the Streamable HTTP
 * entry point (http-server.js).
 */

const API_BASE = process.env.DEPSCOPE_API_URL || "https://depscope.dev";
const API_KEY = process.env.DEPSCOPE_API_KEY || "";

export const ECOSYSTEMS = [
  "npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems",
  "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda",
  "homebrew",
];

export const TOOLS = [

  {
    name: "ai_brief",
    description:
      "Ultra-compact package brief (~300 tokens, plain text) formatted for direct paste into LLM system prompts. Includes: verdict (SAFE/AVOID/URGENT/MALICIOUS), health, vulns, alternatives, maintainer alerts. PREFER THIS in 95% of agent use cases — only fall back to check_package if you need to programmatically read individual JSON fields. Replaces fetching npm/pypi pages + GitHub issues + security DBs (avg 4-8k tokens saved per call).",
    annotations: {
      title: "ai_brief",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string", description: "Package name." },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "audit_stack",
    description:
      "One-shot audit of a full dependency list (up to 50 packages). Returns prioritized action items (REMOVE NOW / URGENT / REPLACE / REVIEW) and a stack-level summary. Use BEFORE executing `npm install axios express lodash` etc. to validate the whole set in a single call instead of N per-package checks.",
    annotations: {
      title: "audit_stack",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        packages: {
          type: "array",
          description: "List of {ecosystem, package} pairs, max 50.",
          items: {
            type: "object",
            properties: {
              ecosystem: { type: "string", enum: ECOSYSTEMS },
              package: { type: "string" },
            },
            required: ["ecosystem", "package"],
          },
        },
      },
      required: ["packages"],
    },
  },
    {
    name: "get_migration_path",
    description:
      "Get a prescriptive migration plan from a deprecated/legacy package to its modern replacement. Returns rationale, before/after code diff examples ready to apply, breaking changes to handle, and estimated effort in minutes. USE THIS when you need to advise a user on replacing `request`→`axios`, `moment`→`dayjs`, `urllib2`→`requests`, `flask`→`fastapi`, etc. The code diff is literal and ready to paste into their codebase.",
    annotations: {
      title: "get_migration_path",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        from_package: { type: "string", description: "Deprecated/legacy package to migrate away from." },
        to_package: { type: "string", description: "Modern replacement package." },
      },
      required: ["ecosystem", "from_package", "to_package"],
    },
  },
    {
    name: "check_package",
    description:
      "Full machine-readable health report (JSON). Use ONLY when you need to PROGRAMMATICALLY parse fields (scoring, gating in CI, building UI). For most LLM use cases prefer ai_brief — same intelligence in ~300 tokens of plain text instead of ~2000 tokens of JSON. Returns: health score (0-100), vulnerabilities (CVE+KEV+EPSS), latest version, deprecation, maintainer count, recommendation.",
    annotations: {
      title: "check_package",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string", description: "Package name (e.g. 'express', 'fastapi', 'serde')." },
        version: { type: "string", description: "Specific version (optional; default = latest)." },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_health_score",
    description:
      "Single number (0-100) — the cheapest call. Use ONLY when you have already decided to install and just need a go/no-go gate (>=70 = safe). For the verbal decision (SAFE/AVOID/URGENT) prefer ai_brief; for the JSON contract prefer check_package.",
    annotations: {
      title: "get_health_score",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_vulnerabilities",
    description:
      "Known CVE / OSV advisories for a package filtered to affecting the latest version. Use before suggesting install on security-sensitive projects.",
    annotations: {
      title: "get_vulnerabilities",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_latest_version",
    description:
      "Just the latest published version + deprecation flag. The cheapest call; use when you only need a version number.",
    annotations: {
      title: "get_latest_version",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "package_exists",
    description:
      "Boolean: does this exact package name exist in the registry? Use to avoid hallucinating package names when generating install commands.",
    annotations: {
      title: "package_exists",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_package_prompt",
    description:
      "Same info as check_package but returned as compact plain text optimized for inclusion in an LLM context (~74% fewer tokens than the JSON form).",
    annotations: {
      title: "get_package_prompt",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "compare_packages",
    description:
      "Side-by-side comparison (health, vulns, downloads, maintainers, last release) for 2-10 packages in the same ecosystem. Use when the user asks 'X vs Y' or 'which one should I pick'.",
    annotations: {
      title: "compare_packages",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        packages: {
          type: "array",
          items: { type: "string" },
          minItems: 2,
          maxItems: 10,
          description: "Package names to compare, e.g. ['express','fastify','hono'].",
        },
      },
      required: ["ecosystem", "packages"],
    },
  },
    {
    name: "scan_project",
    description:
      "Audit an entire dependency list in one call. Returns per-package health + vulns + aggregate score. Max 100 packages per request.",
    annotations: {
      title: "scan_project",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        packages: {
          type: "array",
          items: { type: "string" },
          description: "Package names (optionally with @version), up to 100.",
          maxItems: 100,
        },
      },
      required: ["ecosystem", "packages"],
    },
  },
    {
    name: "find_alternatives",
    description:
      "Curated replacement packages for a deprecated / unhealthy / legacy package. Returns name, reason, and whether the alternative is a language/stdlib built-in (e.g. `fs.rm` for rimraf). Use instead of guessing or inventing replacement names.",
    annotations: {
      title: "find_alternatives",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_breaking_changes",
    description:
      "Verified breaking changes between two major versions of a package, with migration hints. Call BEFORE suggesting a major-version bump.",
    annotations: {
      title: "get_breaking_changes",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
        from_version: { type: "string" },
        to_version: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_known_bugs",
    description:
      "Non-CVE known bugs per package version. Use when a user reports unexpected behavior — often it's a known bug with a documented fix.",
    annotations: {
      title: "get_known_bugs",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
        version: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "check_compatibility",
    description:
      "Check whether a stack (multi-package combination) is verified to work together.",
    annotations: {
      title: "check_compatibility",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        packages: {
          type: "object",
          description: "Package -> version map, e.g. {\"next\":\"15\",\"react\":\"19\"}.",
          additionalProperties: { type: "string" },
        },
      },
      required: ["packages"],
    },
  },
    {
    name: "resolve_error",
    description:
      "Map an error message / stack trace to a verified fix. Returns status, solution, confidence, source URL.",
    annotations: {
      title: "resolve_error",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        error: { type: "string" },
        context: { type: "object" },
      },
      required: ["error"],
    },
  },
    {
    name: "search_errors",
    description: "Free-text search across the error-fix knowledge base.",
    name: "search_errors",
    description: "Free-text search across the error-fix knowledge base.",
    annotations: {
      title: "search_errors",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 20, default: 10 },
      },
      required: ["query"],
    },
  },
    {
    name: "check_malicious",
    description:
      "Is this package flagged as malicious by OpenSSF/OSV? Call BEFORE suggesting install for any unfamiliar package.",
    annotations: {
      title: "check_malicious",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "check_typosquat",
    description:
      "Is this package a suspected typosquat of a popular package? Use when name looks close to a common one.",
    annotations: {
      title: "check_typosquat",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_scorecard",
    description: "OpenSSF Scorecard security score (0-10) for the linked GitHub repo.",
    name: "get_scorecard",
    description: "OpenSSF Scorecard security score (0-10) for the linked GitHub repo.",
    annotations: {
      title: "get_scorecard",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_maintainer_trust",
    description:
      "Maintainer trust signals: bus factor, contributor count, ownership-change detection, primary author dominance.",
    annotations: {
      title: "get_maintainer_trust",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_quality",
    description:
      "Package quality signals: criticality score, velocity, publish security (npm signed/attested, PyPI trusted publisher).",
    annotations: {
      title: "get_quality",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_provenance",
    description: "Cryptographic provenance attestations (SLSA/Sigstore) for npm/PyPI packages.",
    name: "get_provenance",
    description: "Cryptographic provenance attestations (SLSA/Sigstore) for npm/PyPI packages.",
    annotations: {
      title: "get_provenance",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
      },
      required: ["ecosystem", "package"],
    },
  },
    {
    name: "get_trending",
    description:
      "Live trending packages across ecosystems with rank-change and weekly growth %. Use to answer 'what HTTP client/web framework/ORM is rising right now in npm/PyPI/Cargo'. Optional filter by ecosystem and rank scope.",
    annotations: {
      title: "get_trending",
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS, description: "Optional. If omitted returns cross-ecosystem trending." },
        scope: { type: "string", enum: ["all","week","day"], description: "Time window. Defaults to week." },
        limit: { type: "integer", description: "Max results, 1-50. Default 20." },
      },
    },
  },
  {
    name: "report_anomaly",
    description:
      "Report a technical anomaly observed while calling another DepScope tool: wrong field, stale data, false-positive malicious flag, missing migration path, mis-classified deprecation, etc. Strictly structured input - produces parseable issues that DepScope ingests as training/regression data. CALL THIS FIRST for any technical issue. Only fall back to contact_depscope for genuinely human-only categories (security disclosure, listing request that is not anomaly-shaped). 90% of agent feedback fits report_anomaly.",
    annotations: {
      title: "report_anomaly",
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        tool_called: { type: "string", description: "DepScope tool that produced the anomaly (e.g. ai_brief, check_package, get_migration_path)." },
        ecosystem: { type: "string", description: "Ecosystem of the involved package, if any (npm, pypi, ...)." },
        package: { type: "string", description: "Package name involved, if any." },
        version: { type: "string", description: "Package version involved, if any." },
        observed: { type: "string", description: "What DepScope returned (1-1500 chars)." },
        expected: { type: "string", description: "What you expected to see (1-1500 chars). Be concrete." },
        evidence_url: { type: "string", description: "URL to authoritative source (registry page, GHSA, CVE, repo, ...) supporting your expectation." },
      },
      required: ["tool_called", "observed", "expected"],
    },
  },
    {
    name: "contact_depscope",
    description:
      "Open an inbound ticket with the DepScope team. ONLY 3 valid categories - restrict your usage: (a) `bug` = a wrong or missing data point you observed in a DepScope tool response; (b) `listing` = ask DepScope to index a package or ecosystem we do not cover yet; (c) `security` = security-relevant disclosure about DepScope itself. For unstructured technical feedback prefer the `report_anomaly` tool - it produces actionable issues. For partnership / press / generic feedback the user should email depscope@cuttalo.com directly. Returns a ticket reference id.",
    annotations: {
      title: "contact_depscope",
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        email: { type: "string", description: "Reply-to email of the requester (required)." },
        subject: { type: "string", description: "Short subject line (3-200 chars)." },
        body: { type: "string", description: "Message body (10-8000 chars). Be specific: include package name, ecosystem, error trace, repro steps when applicable." },
        type: { type: "string", enum: ["bug","listing","security"], description: "Category of the request." },
        name: { type: "string", description: "Sender display name (optional)." },
        company: { type: "string", description: "Company / organization (optional)." },
      },
      required: ["email", "subject", "body"],
    },
  },
  {
    name: "check_bulk",
    description:
      "Fast pre-flight check for up to 100 (ecosystem, package) pairs in a single call. DB-only, no registry round-trips — typical latency <100ms for 100 items. Returns per-item status: exists | stdlib | malicious | typosquat_suspect | historical_incident | unknown. CALL THIS FIRST before an agent emits `npm install`/`pip install` on a list — it filters out stdlib modules, hallucinated names, typos, and known bad packages in one shot. Replaces N separate /check calls.",
    annotations: {
      title: "check_bulk",
      readOnlyHint: true,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        items: {
          type: "array",
          maxItems: 100,
          items: {
            type: "object",
            properties: {
              ecosystem: { type: "string", enum: ECOSYSTEMS },
              package: { type: "string" },
            },
            required: ["ecosystem", "package"],
          },
        },
      },
      required: ["items"],
    },
  },
  {
    name: "install_command",
    description:
      "Return the canonical install command(s) for a package across every standard package manager of its ecosystem. Prevents agents from hallucinating install syntax (wrong flags, wrong file format). Input: ecosystem + package (+ optional version; defaults to latest). Output: a primary pinned one-liner plus variants for npm/pnpm/yarn/bun, pip/uv/poetry, cargo, go, composer, maven (XML+Gradle), NuGet, RubyGems, pub, hex, SPM, CocoaPods, CPAN, Hackage, CRAN, conda, Homebrew — whichever are applicable.",
    annotations: {
      title: "install_command",
      readOnlyHint: true,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
        version: { type: "string", description: "Optional explicit version; defaults to latest." },
      },
      required: ["ecosystem", "package"],
    },
  },
  {
    name: "pin_safe",
    description:
      "Recommend the highest version of a package whose known CVEs are below the chosen severity tier. Walks the version history newest-first, filtering prereleases by default. Input: ecosystem + package (+ optional min_severity, constraint like ^16.0.0, include_prerelease). Output: recommended_version plus the walk log showing why each version was skipped. Use BEFORE suggesting a version bump or writing a package.json/requirements.txt line.",
    annotations: {
      title: "pin_safe",
      readOnlyHint: true,
      idempotentHint: true,
      openWorldHint: true,
    },
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
        min_severity: {
          type: "string",
          enum: ["critical", "high", "medium", "low"],
          description: "Lowest severity to exclude. Default: high (excludes critical+high).",
        },
        constraint: {
          type: "string",
          description: "npm-style constraint: ^X.Y.Z, ~X.Y.Z, >=X.Y.Z, or exact X.Y.Z.",
        },
        include_prerelease: { type: "boolean", default: false },
      },
      required: ["ecosystem", "package"],
    },
  },
];

function headers() {
  const h = { "User-Agent": "DepScope-MCP/0.4.1" };
  if (API_KEY) h["X-API-Key"] = API_KEY;
  return h;
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}
async function getText(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.text();
}
async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

function encodePkg(pkg) {
  return pkg.split("/").map(encodeURIComponent).join("/");
}

function ok(data) {
  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return { content: [{ type: "text", text }] };
}
function fail(message) {
  return { content: [{ type: "text", text: `Error: ${message}` }], isError: true };
}

export async function handleToolCall(name, args) {
  try {
    switch (name) {
      case "ai_brief":
        return ok(await getText(`/api/ai/brief/${args.ecosystem}/${encodePkg(args.package)}`));
      case "audit_stack": {
        const body = JSON.stringify({ packages: args.packages, format: "text" });
        const res = await fetch(`${API_BASE}/api/ai/stack`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
        });
        if (!res.ok) return fail(`audit_stack failed: ${res.status}`);
        return ok(await res.text());
      }
      case "get_migration_path":
        return ok(await getJson(`/api/migration/${args.ecosystem}/${encodeURIComponent(args.from_package)}/${encodeURIComponent(args.to_package)}`));
      case "contact_depscope": {
        const body = JSON.stringify({
          email: args.email,
          subject: args.subject,
          body: args.body,
          type: args.type || "other",
          name: args.name || "",
          company: args.company || "",
          source: "mcp",
          consent: true,
        });
        const res = await fetch(`${API_BASE}/api/contact`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Depscope-Source": "mcp" },
          body,
        });
        if (!res.ok) return fail(`contact_depscope failed: ${res.status} ${await res.text().catch(()=>"")}`);
        return ok(await res.json());
      }
      case "report_anomaly": {
        const body = JSON.stringify({
          tool_called: args.tool_called,
          ecosystem: args.ecosystem || "",
          package: args.package || "",
          version: args.version || "",
          observed: args.observed,
          expected: args.expected,
          evidence_url: args.evidence_url || "",
          source: "mcp",
        });
        const res = await fetch(`${API_BASE}/api/anomaly`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Depscope-Source": "mcp" },
          body,
        });
        if (!res.ok) return fail(`report_anomaly failed: ${res.status} ${await res.text().catch(()=>"")}`);
        return ok(await res.json());
      }
      case "get_trending": {
        const params = new URLSearchParams();
        if (args.ecosystem) params.set("ecosystem", args.ecosystem);
        if (args.scope) params.set("scope", args.scope);
        if (args.limit) params.set("limit", String(args.limit));
        const qs = params.toString();
        return ok(await getJson(`/api/trending${qs ? "?" + qs : ""}`));
      }
      case "check_package": {
        const pkg = encodePkg(args.package);
        let path = `/api/check/${args.ecosystem}/${pkg}`;
        if (args.version) path += `?version=${encodeURIComponent(args.version)}`;
        return ok(await getJson(path));
      }
      case "get_health_score":
        return ok(await getJson(`/api/health/${args.ecosystem}/${encodePkg(args.package)}`));
      case "get_vulnerabilities":
        return ok(await getJson(`/api/vulns/${args.ecosystem}/${encodePkg(args.package)}`));
      case "get_latest_version":
        return ok(await getJson(`/api/latest/${args.ecosystem}/${encodePkg(args.package)}`));
      case "package_exists":
        return ok(await getJson(`/api/exists/${args.ecosystem}/${encodePkg(args.package)}`));
      case "get_package_prompt":
        return ok(await getText(`/api/prompt/${args.ecosystem}/${encodePkg(args.package)}`));
      case "compare_packages": {
        const csv = args.packages.map(encodeURIComponent).join(",");
        return ok(await getJson(`/api/compare/${args.ecosystem}/${csv}`));
      }
      case "scan_project": {
        let pkgs = args.packages;
        if (typeof pkgs === "string") { try { pkgs = JSON.parse(pkgs); } catch {} }
        // Backend /api/scan requires dict {name: version}. Accept either array or dict from the caller.
        if (Array.isArray(pkgs)) {
          pkgs = Object.fromEntries(pkgs.map(e => {
            const at = e.lastIndexOf("@");
            return at > 0 ? [e.slice(0, at), e.slice(at + 1)] : [e, "*"];
          }));
        }
        if (!pkgs || typeof pkgs !== "object" || Object.keys(pkgs).length === 0) {
          return fail("\"packages\" must be a non-empty array or {name: version} object");
        }
        return ok(await postJson("/api/scan", { ecosystem: args.ecosystem, packages: pkgs }));
      }
      case "find_alternatives":
        return ok(await getJson(`/api/alternatives/${args.ecosystem}/${encodePkg(args.package)}`));
      case "get_breaking_changes": {
        const pkg = encodePkg(args.package);
        const qs = new URLSearchParams();
        if (args.from_version) qs.set("from_version", args.from_version);
        if (args.to_version) qs.set("to_version", args.to_version);
        const suffix = qs.toString() ? `?${qs}` : "";
        return ok(await getJson(`/api/breaking/${args.ecosystem}/${pkg}${suffix}`));
      }
      case "get_known_bugs": {
        const pkg = encodePkg(args.package);
        const suffix = args.version ? `?version=${encodeURIComponent(args.version)}` : "";
        return ok(await getJson(`/api/bugs/${args.ecosystem}/${pkg}${suffix}`));
      }
      case "check_compatibility": {
        let pkgs = args.packages;
        if (typeof pkgs === "string") { try { pkgs = JSON.parse(pkgs); } catch {} }
        if (!pkgs || typeof pkgs !== "object" || Array.isArray(pkgs) || Object.keys(pkgs).length === 0) {
          return fail("\"packages\" must be a non-empty object, e.g. {\"next\":\"16\",\"react\":\"19\"}");
        }
        return ok(await postJson("/api/compat", { packages: pkgs }));
      }
      case "resolve_error":
        return ok(await postJson(`/api/error/resolve`, { error: args.error, context: args.context }));
      case "search_errors": {
        const qs = new URLSearchParams({ q: args.query });
        if (args.limit) qs.set("limit", String(args.limit));
        return ok(await getJson(`/api/error?${qs}`));
      }
      case "check_malicious":
        return ok(await getJson(`/api/malicious/${args.ecosystem}/${args.package}`));
      case "check_typosquat":
        return ok(await getJson(`/api/typosquat/${args.ecosystem}/${args.package}`));
      case "get_scorecard":
        return ok(await getJson(`/api/scorecard/${args.ecosystem}/${args.package}`));
      case "get_maintainer_trust":
        return ok(await getJson(`/api/maintainers/${args.ecosystem}/${args.package}`));
      case "get_quality":
        return ok(await getJson(`/api/quality/${args.ecosystem}/${args.package}`));
      case "get_provenance":
        return ok(await getJson(`/api/provenance/${args.ecosystem}/${args.package}`));
      case "check_bulk":
        return ok(await postJson(`/api/check_bulk`, { items: args.items || [] }));
      case "install_command": {
        const qs = new URLSearchParams();
        if (args.version) qs.set("version", args.version);
        const q = qs.toString();
        return ok(await getJson(`/api/install/${args.ecosystem}/${args.package}${q ? "?" + q : ""}`));
      }
      case "pin_safe": {
        const qs = new URLSearchParams();
        if (args.min_severity) qs.set("min_severity", args.min_severity);
        if (args.constraint) qs.set("constraint", args.constraint);
        if (args.include_prerelease) qs.set("include_prerelease", "true");
        const q = qs.toString();
        return ok(await getJson(`/api/pin_safe/${args.ecosystem}/${args.package}${q ? "?" + q : ""}`));
      }
      default:
        return fail(`Unknown tool: ${name}`);
    }
  } catch (e) {
    return fail(e.message);
  }
}
