"use client";

import { useState, useEffect } from "react";
import SavingsCounter from "../savings-counter";

interface HealthBreakdown {
  maintenance: number;
  popularity: number;
  security: number;
  maturity: number;
  community: number;
}

interface Vulnerability {
  vuln_id: string;
  severity: string;
  summary: string;
  fixed_version: string | null;
}

interface PackageResult {
  package: string;
  ecosystem: string;
  latest_version: string;
  description: string;
  license: string;
  repository: string;
  health: {
    score: number;
    risk: string;
    breakdown: HealthBreakdown;
    deprecated: boolean;
  };
  vulnerabilities: {
    count: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    details: Vulnerability[];
  };
  versions: {
    latest: string;
    total_count: number;
    recent: string[];
  };
  metadata: {
    deprecated: boolean;
    deprecated_message: string | null;
    maintainers_count: number;
    last_published: string;
    first_published: string;
    dependencies_count: number;
    dependencies: string[];
  };
  recommendation: {
    action: string;
    issues: string[];
    use_version: string;
    version_hint: string | null;
    summary: string;
  };
  _response_ms: number;
  _cache: string;
}

function ScoreRing({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : score >= 40 ? "#f97316" : "#ef4444";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={radius} stroke="#1e1e2e" strokeWidth="8" fill="none" />
        <circle cx="70" cy="70" r={radius} stroke={color} strokeWidth="8" fill="none"
          strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
          className="score-ring" />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold" style={{ color }}>{score}</span>
        <span className="text-xs text-[var(--text-dim)]">/100</span>
      </div>
    </div>
  );
}

function Badge({ severity }: { severity: string }) {
  const c: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400 border-red-500/30",
    high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    low: "bg-green-500/20 text-green-400 border-green-500/30",
  };
  return <span className={`px-2 py-0.5 text-xs rounded border ${c[severity] || c.low}`}>{severity}</span>;
}

const SETUP_TABS = [
  {
    id: "claude",
    label: "Claude Code",
    file: "CLAUDE.md",
    snippet: `## DEPSCOPE — Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "cursor",
    label: "Cursor",
    file: ".cursorrules",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — no auth, free`,
  },
  {
    id: "windsurf",
    label: "Windsurf",
    file: ".windsurfrules",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg}`,
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    file: "deepseek config",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — no auth, free`,
  },
  {
    id: "tongyi",
    label: "Tongyi Qianwen",
    file: "tongyi config",
    snippet: `Before any install: curl depscope.dev/api/check/{eco}/{pkg} — no auth, free`,
  },
  {
    id: "chatgpt",
    label: "ChatGPT",
    file: "GPT Store",
    snippet: `Search "DepScope" in the GPT Store — or use the OpenAPI spec:
https://depscope.dev/openapi-gpt.json`,
  },
  {
    id: "curl",
    label: "Any Agent",
    file: "curl / HTTP",
    snippet: `curl https://depscope.dev/api/check/npm/express`,
  },
];

function SetupSnippets() {
  const [activeTab, setActiveTab] = useState("claude");
  const [copied, setCopied] = useState(false);

  const active = SETUP_TABS.find((t) => t.id === activeTab) || SETUP_TABS[0];

  const copyToClipboard = () => {
    navigator.clipboard.writeText(active.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card border border-[var(--accent)]/20 overflow-hidden max-w-3xl mx-auto">
      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-[var(--border)] bg-[var(--bg)]">
        {SETUP_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setCopied(false); }}
            className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition ${
              activeTab === tab.id
                ? "text-[var(--accent)] border-b-2 border-[var(--accent)] bg-[var(--bg-card)]"
                : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg-card)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-5">
        <div className="flex justify-between items-center mb-3">
          <span className="text-xs text-[var(--text-dim)] font-mono">{active.file}</span>
          <button
            onClick={copyToClipboard}
            className={`text-xs px-3 py-1.5 rounded-md font-medium transition ${
              copied
                ? "bg-[var(--green)]/20 text-[var(--green)]"
                : "bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20"
            }`}
          >
            {copied ? "已复制!" : "复制"}
          </button>
        </div>
        <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap leading-relaxed">{active.snippet}</pre>
      </div>
    </div>
  );
}

interface StatsData {
  packages_indexed: number;
  vulnerabilities_tracked: number;
  ecosystems: string[];
  mcp_tools?: number;
}

const ECOSYSTEM_LABELS: Record<string, string> = {
  npm: "npm",
  pypi: "PyPI",
  cargo: "Cargo",
  go: "Go",
  composer: "Composer",
  maven: "Maven",
  nuget: "NuGet",
  rubygems: "RubyGems",
  pub: "Pub",
  hex: "Hex",
  swift: "Swift",
  cocoapods: "CocoaPods",
  cpan: "CPAN",
  hackage: "Hackage",
  cran: "CRAN",
  conda: "Conda",
  homebrew: "Homebrew",
};

export default function ZhHome() {
  const [query, setQuery] = useState("");
  const [ecosystem, setEcosystem] = useState("npm");
  const [availableEcosystems, setAvailableEcosystems] = useState<string[]>(["npm", "pypi", "cargo", "go", "composer", "maven", "nuget", "rubygems", "pub", "hex", "swift", "cocoapods", "cpan", "hackage", "cran", "conda", "homebrew"]);
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch("/api/stats").then(r => r.json()).then(d => {
      if (d.ecosystems?.length) setAvailableEcosystems(d.ecosystems);
      setStats(d);
    }).catch(() => {});
  }, []);
  const [result, setResult] = useState<PackageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`/api/check/${ecosystem}/${query.trim()}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `未找到软件包 (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">

      {/* === 1. HERO === */}
      <header className="pt-10 md:pt-16 pb-4 md:pb-6 px-4 text-center" id="top">
        <p className="text-sm font-mono text-[var(--accent)] mb-3 tracking-wider">AI代理包智能服务</p>
        <h1 className="text-3xl md:text-5xl font-bold mb-3 leading-tight">
          节省令牌。节省能源。<br /><span className="text-[var(--accent)]">发布更安全的代码。</span>
        </h1>
        <p className="text-base text-[var(--text-dim)] mb-8 max-w-lg mx-auto">
          {stats?.ecosystems?.length || 17}个生态系统的包健康API。为每个AI代理缓存。免费，无需认证。
        </p>

        {/* Search */}
        <div className="max-w-2xl mx-auto mb-4">
          <div className="card search-box p-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <select value={ecosystem} onChange={(e) => setEcosystem(e.target.value)}
              className="bg-transparent border-r border-[var(--border)] px-3 py-3 text-sm text-[var(--accent)] cursor-pointer focus:outline-none">
              {availableEcosystems.map((eco) => (
                <option key={eco} value={eco}>{eco}</option>
              ))}
            </select>
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="express, fastapi, serde, @anthropic-ai/sdk..."
              className="flex-1 bg-transparent px-3 py-3 text-base md:text-lg focus:outline-none placeholder:text-[var(--text-dim)]/50" />
            <button onClick={search} disabled={loading}
              className="bg-[var(--accent)] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[var(--accent-dim)] transition disabled:opacity-50">
              {loading ? "..." : "检查"}
            </button>
          </div>
          {error && <p className="text-red-400 text-sm mt-2 text-center">{error}</p>}
        </div>

        {/* Trust badges */}
        <div className="flex flex-wrap justify-center gap-2 md:gap-3 text-xs md:text-sm text-[var(--text-dim)]">
          {availableEcosystems.map((eco) => (
            <a key={eco} href={`/ecosystems/${eco}`}
              className="px-2 md:px-3 py-1 rounded-full border border-[var(--border)] hover:border-[var(--accent)]/50 hover:text-[var(--accent)] transition">
              {ECOSYSTEM_LABELS[eco] || eco}
            </a>
          ))}
        </div>
      </header>

      {/* Results */}
      {result && (
        <div className="max-w-4xl mx-auto px-4 pb-20 space-y-6">
          {/* Header */}
          <div className="card p-6">
            <div className="flex items-start justify-between gap-4 md:gap-6 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h2 className="text-2xl font-bold">{result.package}</h2>
                  <span className="text-sm px-2 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/20">{result.ecosystem}</span>
                  <span className="text-sm text-[var(--text-dim)]">v{result.latest_version}</span>
                  {result._cache === "hit" && <span className="text-xs text-green-400">已缓存</span>}
                </div>
                <p className="text-[var(--text-dim)] mb-3">{result.description}</p>
                <div className="flex flex-wrap gap-4 text-sm text-[var(--text-dim)]">
                  {result.license && <span>许可证: {result.license}</span>}
                  <span>{result.versions.total_count} 个版本</span>
                  <span>{result.metadata.maintainers_count} 个维护者</span>
                  <span>{result.metadata.dependencies_count} 个依赖</span>
                  <span>{result._response_ms}ms</span>
                </div>
                {result.repository && (
                  <a href={result.repository} target="_blank" rel="noopener"
                    className="text-sm text-[var(--accent)] hover:underline mt-2 inline-block">
                    {result.repository.replace("https://github.com/", "")}
                  </a>
                )}
              </div>
              <ScoreRing score={result.health.score} />
            </div>
          </div>

          {/* Recommendation */}
          <div className={`card p-4 border-l-4 ${
            result.recommendation.action === "safe_to_use" ? "border-l-green-500" :
            result.recommendation.action === "do_not_use" ? "border-l-red-500" : "border-l-yellow-500"
          }`}>
            <p className="font-medium">{result.recommendation.summary}</p>
            {result.recommendation.version_hint && (
              <p className="text-sm text-[var(--text-dim)] mt-1">{result.recommendation.version_hint}</p>
            )}
            {result.recommendation.issues.length > 0 && (
              <ul className="mt-2 text-sm text-[var(--text-dim)]">
                {result.recommendation.issues.map((issue, i) => <li key={i}>- {issue}</li>)}
              </ul>
            )}
          </div>

          {/* Health Breakdown */}
          <div className="card p-6">
            <h3 className="font-semibold mb-4">健康评分详情</h3>
            <div className="grid grid-cols-5 gap-4">
              {Object.entries(result.health.breakdown).map(([key, value]) => {
                const max = key === "maintenance" || key === "security" ? 25 : key === "popularity" ? 20 : 15;
                const pct = (value / max) * 100;
                const labels: Record<string, string> = {
                  maintenance: "维护",
                  popularity: "流行度",
                  security: "安全",
                  maturity: "成熟度",
                  community: "社区",
                };
                return (
                  <div key={key} className="text-center">
                    <div className="text-2xl font-bold mb-1">{value}<span className="text-xs text-[var(--text-dim)]">/{max}</span></div>
                    <div className="w-full bg-[var(--bg)] rounded-full h-1.5 mb-1">
                      <div className="h-1.5 rounded-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="text-xs text-[var(--text-dim)]">{labels[key] || key}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Vulnerabilities */}
          {result.vulnerabilities.count > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">漏洞 ({result.vulnerabilities.count})</h3>
              <div className="flex gap-3 mb-4 flex-wrap">
                {result.vulnerabilities.critical > 0 && <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-sm">{result.vulnerabilities.critical} 严重</span>}
                {result.vulnerabilities.high > 0 && <span className="px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 text-sm">{result.vulnerabilities.high} 高危</span>}
                {result.vulnerabilities.medium > 0 && <span className="px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-sm">{result.vulnerabilities.medium} 中危</span>}
                {result.vulnerabilities.low > 0 && <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm">{result.vulnerabilities.low} 低危</span>}
              </div>
              <div className="space-y-3">
                {result.vulnerabilities.details.slice(0, 10).map((vuln, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[var(--bg)]">
                    <Badge severity={vuln.severity} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-mono text-[var(--text-dim)]">{vuln.vuln_id}</span>
                      <p className="text-sm mt-1 break-words">{vuln.summary}</p>
                      {vuln.fixed_version && <p className="text-xs text-green-400 mt-1">已在 {vuln.fixed_version} 修复</p>}
                    </div>
                  </div>
                ))}
                {result.vulnerabilities.count > 10 && (
                  <p className="text-sm text-[var(--text-dim)] text-center">... 还有 {result.vulnerabilities.count - 10} 个</p>
                )}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {result.metadata.dependencies && result.metadata.dependencies.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">依赖 ({result.metadata.dependencies_count})</h3>
              <div className="flex flex-wrap gap-2">
                {result.metadata.dependencies.slice(0, 30).map((dep, i) => (
                  <button key={i} onClick={() => { setQuery(typeof dep === 'string' ? dep.split(/[<>=! ]/)[0] : dep); search(); }}
                    className="px-3 py-1 text-sm rounded-full bg-[var(--bg)] text-[var(--text-dim)] hover:text-[var(--accent)] hover:bg-[var(--accent)]/10 transition cursor-pointer border border-[var(--border)]">
                    {typeof dep === 'string' ? dep.split(/[<>=! ]/)[0] : dep}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* API call */}
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <code className="text-xs text-[var(--text-dim)]">GET /api/check/{result.ecosystem}/{result.package}</code>
              <span className="text-xs text-[var(--text-dim)]">{result._response_ms}ms | {result._cache}</span>
            </div>
          </div>
        </div>
      )}

      {/* === LANDING CONTENT === */}
      {!result && (
        <div className="px-4 pb-12 md:pb-20">

          {/* === PROBLEM -> SOLUTION === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <div className="flex flex-col md:flex-row items-stretch gap-0">

              {/* Problem 1 */}
              <div className="flex-1 p-5 md:p-6 border border-[var(--border)] rounded-t-xl md:rounded-l-xl md:rounded-tr-none bg-[var(--red)]/5 border-b-0 md:border-b md:border-r-0">
                <img src="/mission-1.webp" alt="" className="w-full h-24 md:h-32 object-cover rounded-lg mb-4 opacity-75" />
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--red)]/20 flex items-center justify-center text-sm font-bold text-red-400">1</div>
                  <span className="text-xs font-mono text-red-400 tracking-wider uppercase">问题</span>
                </div>
                <span className="inline-block text-[10px] font-mono tracking-widest uppercase text-red-400 mb-2">{String.fromCodePoint(0x1F512)} 安全风险</span>
                <h3 className="font-bold text-base mb-2">AI代理猜测包信息</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed">
                  它建议过时的库、错误的版本和已知漏洞的包。训练数据已经过期。
                </p>
              </div>

              {/* Problem 2 */}
              <div className="flex-1 p-5 md:p-6 border border-[var(--border)] bg-[var(--orange)]/5 border-b-0 md:border-b md:border-r-0">
                <img src="/mission-2.webp" alt="" className="w-full h-24 md:h-32 object-cover rounded-lg mb-4 opacity-75" />
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--orange)]/20 flex items-center justify-center text-sm font-bold text-orange-400">2</div>
                  <span className="text-xs font-mono text-orange-400 tracking-wider uppercase">问题</span>
                </div>
                <span className="inline-block text-[10px] font-mono tracking-widest uppercase text-orange-400 mb-2">{String.fromCodePoint(0x26A1)} 浪费能源和令牌</span>
                <h3 className="font-bold text-base mb-2">每个代理重复获取相同数据</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed">
                  数百万次重复调用npm、PyPI、OSV。浪费带宽、能源和令牌。
                </p>
              </div>

              {/* Solution */}
              <div className="flex-1 p-5 md:p-6 border border-[var(--border)] rounded-b-xl md:rounded-r-xl md:rounded-bl-none bg-[var(--accent)]/5 border-[var(--accent)]/30">
                <img src="/mission-3.webp" alt="" className="w-full h-24 md:h-32 object-cover rounded-lg mb-4 opacity-75" />
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-sm font-bold text-[var(--accent)]">{String.fromCodePoint(0x2713)}</div>
                  <span className="text-xs font-mono text-[var(--accent)] tracking-wider uppercase">解决方案</span>
                </div>
                <h3 className="font-bold text-base mb-2">一次API调用，搞定。</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed">
                  健康评分、漏洞、建议。{stats?.ecosystems?.length || 17}个生态系统。缓存。免费。无需认证。
                </p>
              </div>

            </div>
          </div>

          {/* === 2. SETUP === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto" id="setup">
            <h2 className="text-xl md:text-2xl font-bold text-center mb-2">添加到你的AI代理</h2>
            <p className="text-center text-[var(--text-dim)] text-sm mb-6 max-w-xl mx-auto">
              配置文件中加一行。你的代理在每次安装时节省令牌，你的用户节省能源，你发布更安全的代码。
            </p>
            <SetupSnippets />
          </div>

          {/* === 3. KPI STRIP === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="card p-5 text-center">
                <div className="text-xl md:text-3xl font-bold text-[var(--accent)]">
                  {stats?.packages_indexed?.toLocaleString() || "14,744"}
                </div>
                <div className="text-xs text-[var(--text-dim)] mt-1">已索引包</div>
              </div>
              <div className="card p-5 text-center">
                <div className="text-xl md:text-3xl font-bold text-[var(--green, #22c55e)]">
                  {stats?.ecosystems?.length || 17}
                </div>
                <div className="text-xs text-[var(--text-dim)] mt-1">生态系统</div>
              </div>
              <div className="card p-5 text-center">
                <div className="text-xl md:text-3xl font-bold text-[var(--red, #ef4444)]">
                  {stats?.vulnerabilities_tracked?.toLocaleString() || "402"}
                </div>
                <div className="text-xs text-[var(--text-dim)] mt-1">已追踪漏洞</div>
              </div>
              <div className="card p-5 text-center">
                <div className="text-xl md:text-3xl font-bold text-[var(--orange, #f97316)]">
                  {stats?.mcp_tools ?? 12}
                </div>
                <div className="text-xs text-[var(--text-dim)] mt-1">MCP 工具</div>
              </div>
            </div>
          </div>

          {/* === 3b. THREE SAVINGS === */}
          <section className="mb-8 md:mb-12 max-w-5xl mx-auto">
            <h2 className="text-xl md:text-2xl font-bold text-center mb-6">DepScope为您节省的三样东西</h2>
            <div className="grid md:grid-cols-3 gap-5">
              {/* Card 1: Tokens */}
              <div className="card p-6 border-l-4 border-blue-500">
                <div className="text-3xl mb-3">{String.fromCodePoint(0x1F524)}</div>
                <h3 className="font-bold text-lg mb-2">令牌</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed mb-3">
                  解析 npm/PyPI JSON，AI代理每次查询会消耗约3K令牌。使用 DepScope，结构化答案少于100令牌。
                </p>
                <div className="text-xs font-mono text-[var(--accent)]">减少约 92%</div>
              </div>

              {/* Card 2: Energy */}
              <div className="card p-6 border-l-4 border-orange-500">
                <div className="text-3xl mb-3">{String.fromCodePoint(0x26A1)}</div>
                <h3 className="font-bold text-lg mb-2">能源</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed mb-3">
                  共享缓存 = 一次获取服务成千上万次。更少的计算、更少的带宽、跨公共注册表更少的 CO2。
                </p>
                <div className="text-xs font-mono text-[var(--accent)]">数据中心受益</div>
              </div>

              {/* Card 3: Security */}
              <div className="card p-6 border-l-4 border-red-500">
                <div className="text-3xl mb-3">{String.fromCodePoint(0x1F512)}</div>
                <h3 className="font-bold text-lg mb-2">安全</h3>
                <p className="text-sm text-[var(--text-dim)] leading-relaxed mb-3">
                  追踪 {stats?.vulnerabilities_tracked?.toLocaleString() || "400"}+ 漏洞，仅过滤最新版本。加上传递依赖、许可证审计、弃用警报。
                </p>
                <div className="text-xs font-mono text-[var(--accent)]">不只是噪音</div>
              </div>
            </div>
          </section>

          {/* === 4. WITH vs WITHOUT === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <h2 className="text-xl md:text-2xl font-bold text-center mb-4 md:mb-6">它如何改变游戏规则</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="card p-6 border-l-4" style={{ borderLeftColor: "var(--red)" }}>
                <h3 className="font-semibold mb-4" style={{ color: "var(--red)" }}>不使用 DepScope</h3>
                <ul className="space-y-3 text-sm">
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 shrink-0">&#10005;</span>
                    <span className="text-[var(--text-dim)]">代理从<strong className="text-[var(--text)]">过时的训练数据</strong>中建议包</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 shrink-0">&#10005;</span>
                    <span className="text-[var(--text-dim)]">不知道是否<strong className="text-[var(--text)]">已弃用或有漏洞</strong></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 shrink-0">&#10005;</span>
                    <span className="text-[var(--text-dim)]">版本错误、依赖损坏、<strong className="text-[var(--text)]">安全漏洞</strong></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 shrink-0">&#10005;</span>
                    <span className="text-[var(--text-dim)]">你在<strong className="text-[var(--text)]">生产环境</strong>才发现问题</span>
                  </li>
                </ul>
              </div>
              <div className="card p-6 border-l-4" style={{ borderLeftColor: "var(--green)" }}>
                <h3 className="font-semibold mb-4" style={{ color: "var(--green)" }}>使用 DepScope</h3>
                <ul className="space-y-3 text-sm">
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 shrink-0">&#10003;</span>
                    <span className="text-[var(--text-dim)]">代理在建议前<strong className="text-[var(--text)]">调用 DepScope API</strong></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 shrink-0">&#10003;</span>
                    <span className="text-[var(--text-dim)]"><strong className="text-[var(--text)]">实时健康检查</strong>，评分 0-100</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 shrink-0">&#10003;</span>
                    <span className="text-[var(--text-dim)]">漏洞、弃用、替代方案<strong className="text-[var(--text)]">一次调用搞定</strong></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 shrink-0">&#10003;</span>
                    <span className="text-[var(--text-dim)]">在写一行代码之前做出<strong style={{ color: "var(--green)" }}>明智选择</strong></span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* === 5. PUNTI DI FORZA === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="card p-6">
                <h3 className="font-semibold mb-2 text-[var(--accent)]">零认证</h3>
                <p className="text-sm text-[var(--text-dim)]">无需 API 密钥。无需注册。无限制。直接调用。</p>
              </div>
              <div className="card p-6">
                <h3 className="font-semibold mb-2 text-[var(--accent)]">{stats?.ecosystems?.length || 17} 个生态系统</h3>
                <p className="text-sm text-[var(--text-dim)]">npm、PyPI、Cargo、Go、Maven、NuGet 等。一个端点搞定全部。</p>
              </div>
              <div className="card p-6">
                <h3 className="font-semibold mb-2 text-[var(--accent)]">专为 AI 设计</h3>
                <p className="text-sm text-[var(--text-dim)]">结构化 JSON。OpenAPI 规范。MCP 服务器。ChatGPT 插件。兼容所有代理。</p>
              </div>
            </div>
          </div>

          {/* === 6. TRY IT LIVE === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-6">在线体验</h2>
            <div className="card p-6 overflow-hidden">
              <div className="bg-[var(--bg)] rounded-lg p-5 font-mono text-sm leading-relaxed overflow-x-auto">
                <div className="text-[var(--text-dim)] mb-3">$ curl depscope.dev/api/check/npm/express</div>
                <div className="text-[var(--text-dim)]">{"{"}</div>
                <div className="ml-4"><span className="text-purple-400">&quot;health&quot;</span>: {"{"}</div>
                <div className="ml-8"><span className="text-purple-400">&quot;score&quot;</span>: <span className="text-[var(--accent)] font-bold">80</span>,</div>
                <div className="ml-8"><span className="text-purple-400">&quot;risk&quot;</span>: <span className="text-green-400">&quot;low&quot;</span></div>
                <div className="ml-4">{"}"},</div>
                <div className="ml-4"><span className="text-purple-400">&quot;recommendation&quot;</span>: {"{"}</div>
                <div className="ml-8"><span className="text-purple-400">&quot;action&quot;</span>: <span className="text-green-400">&quot;safe_to_use&quot;</span></div>
                <div className="ml-4">{"}"},</div>
                <div className="ml-4"><span className="text-purple-400">&quot;vulnerabilities&quot;</span>: {"{"}</div>
                <div className="ml-8"><span className="text-purple-400">&quot;count&quot;</span>: <span className="text-green-400">0</span></div>
                <div className="ml-4">{"}"}</div>
                <div className="text-[var(--text-dim)]">{"}"}</div>
              </div>
              <div className="mt-4 text-center">
                <button
                  onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); }}
                  className="text-sm text-[var(--accent)] hover:underline font-medium"
                >
                  用你的包试试 &rarr;
                </button>
              </div>
            </div>
          </div>

          {/* === 7. EXPLORE ECOSYSTEMS === */}
          <div className="mb-12 max-w-6xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-6">探索生态系统</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
              {availableEcosystems.map((eco) => (
                <a key={eco} href={`/ecosystems/${eco}`}
                  className="card p-5 text-center hover:border-[var(--accent)]/50 transition">
                  <h3 className="font-semibold text-[var(--accent)] mb-1">{ECOSYSTEM_LABELS[eco] || eco}</h3>
                  <p className="text-xs text-[var(--text-dim)]">浏览软件包</p>
                </a>
              ))}
            </div>
          </div>

          {/* === LIVE SAVINGS COUNTER === */}
          <div className="mb-8 md:mb-12 max-w-5xl mx-auto">
            <SavingsCounter />
          </div>

          {/* === FOR AI AGENTS (Chinese specific) === */}
          <div className="mb-8 md:mb-12 max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-6">为 AI 编程助手而生</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="card p-6">
                <h3 className="font-semibold text-[var(--accent)] mb-2">DeepSeek 用户</h3>
                <p className="text-sm text-[var(--text-dim)]">在 DeepSeek Coder 的配置中添加 DepScope API 调用，安装任何软件包前自动验证。</p>
              </div>
              <div className="card p-6">
                <h3 className="font-semibold text-[var(--accent)] mb-2">通义千问用户</h3>
                <p className="text-sm text-[var(--text-dim)]">在通义千问的工具配置中集成 DepScope，获取实时包健康数据和漏洞信息。</p>
              </div>
              <div className="card p-6">
                <h3 className="font-semibold text-[var(--accent)] mb-2">Claude Code 用户</h3>
                <p className="text-sm text-[var(--text-dim)]">添加到 CLAUDE.md 文件，Claude 将在建议安装前自动检查软件包。</p>
              </div>
              <div className="card p-6">
                <h3 className="font-semibold text-[var(--accent)] mb-2">Cursor 用户</h3>
                <p className="text-sm text-[var(--text-dim)]">添加到 .cursorrules 文件，Cursor 将自动验证每个软件包建议。</p>
              </div>
            </div>
          </div>

          {/* === 8. FOOTER CTA === */}
          <div className="mb-12 mt-12 max-w-4xl mx-auto text-center">
            <h2 className="text-xl md:text-2xl font-bold mb-4">准备发布更安全的代码？</h2>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a href="/zh/integrate" className="border border-[var(--accent)]/50 text-[var(--accent)] font-semibold px-6 py-3 rounded-lg hover:bg-[var(--accent)]/10 transition text-center">
                集成指南
              </a>
              <a href="/zh/api-docs" className="border border-[var(--border)] text-[var(--text)] font-semibold px-6 py-3 rounded-lg hover:bg-[var(--bg-card)] transition text-center">
                API 文档
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-10 text-sm text-[var(--text-dim)]">
        <div className="max-w-4xl mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 mb-8">
            <div>
              <h4 className="font-semibold text-[var(--text)] mb-3">DepScope</h4>
              <p className="text-xs leading-relaxed">
                节省令牌。节省能源。发布更安全的代码。免费包智能 API，覆盖 {stats?.ecosystems?.length || 17} 个生态系统。
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--text)] mb-3">资源</h4>
              <div className="flex flex-col gap-1.5">
                <a href="/zh/api-docs" className="hover:text-[var(--accent)] transition">API 文档</a>
                <a href="/docs" className="hover:text-[var(--accent)] transition">Swagger / OpenAPI</a>
                <a href="/popular" className="hover:text-[var(--accent)] transition">热门软件包</a>
                <a href="/stats" className="hover:text-[var(--accent)] transition">实时统计</a>
                <a href="/.well-known/ai-plugin.json" className="hover:text-[var(--accent)] transition">AI Plugin</a>
              </div>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--text)] mb-3">Legal</h4>
              <div className="flex flex-col gap-1.5">
                <a href="/privacy" className="hover:text-[var(--accent)] transition">Privacy Policy</a>
                <a href="/contact" className="hover:text-[var(--accent)] transition">Contact</a>
                <a href="mailto:depscope@cuttalo.com" className="hover:text-[var(--accent)] transition">depscope@cuttalo.com</a>
              </div>
            </div>
          </div>
          <div className="border-t border-[var(--border)] pt-6 flex flex-col md:flex-row justify-between items-center gap-2">
            <p className="text-xs">
              &copy; {new Date().getFullYear()}{" "}
              <a href="https://cuttalo.com" className="hover:text-[var(--accent)] transition">Cuttalo srl</a>
              {" - Italy "}&mdash; VAT IT03242390734
            </p>
            <a href="/" className="text-xs hover:text-[var(--accent)] transition">English</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
