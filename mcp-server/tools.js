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
    name: "check_package",
    description:
      "Full health report for a package: health score (0-100), vulnerabilities (CVE), latest version, deprecation, maintainer count, recommendation (safe_to_use | use_with_caution | update_required | find_alternative | do_not_use). ALWAYS call before suggesting `npm install`, `pip install`, or any dependency addition.",
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
      "Health score (0-100) only. Fastest endpoint when you just need a go/no-go. Score >= 70 is generally safe.",
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
    inputSchema: {
      type: "object",
      properties: {
        ecosystem: { type: "string", enum: ECOSYSTEMS },
        package: { type: "string" },
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
      default:
        return fail(`Unknown tool: ${name}`);
    }
  } catch (e) {
    return fail(e.message);
  }
}
