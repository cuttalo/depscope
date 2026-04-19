"use client";
import { useEffect, useState } from "react";

interface Stats {
  packages_indexed: number;
  vulnerabilities_tracked: number;
  ecosystems: string[];
  mcp_tools?: number;
}

export default function SavingsCounter() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch("/api/stats").then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const ecosystemsCount = stats?.ecosystems?.length ?? 17;
  const packagesIndexed = stats?.packages_indexed ?? 14744;
  const vulnsTracked = stats?.vulnerabilities_tracked ?? 402;

  return (
    <div>
      <h2 className="text-xl md:text-2xl font-bold text-center mb-2">
        Efficiency by design
      </h2>
      <p className="text-center text-[var(--text-dim)] text-sm mb-6">
        What every DepScope call delivers &mdash; no matter how many agents share the cache.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Tokens */}
        <div className="card p-6 text-center border-l-4 border-blue-500">
          <div className="text-xs font-mono tracking-widest uppercase text-blue-400 mb-2">
            {String.fromCodePoint(0x1F524)} Tokens
          </div>
          <div className="text-4xl md:text-5xl font-bold text-[var(--text)] mb-1">
            ~92%
          </div>
          <div className="text-xs text-[var(--text-dim)]">reduction per check</div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 opacity-70">
            ~3K raw JSON tokens &rarr; &lt;100 structured
          </div>
        </div>

        {/* Response */}
        <div className="card p-6 text-center border-l-4 border-orange-500">
          <div className="text-xs font-mono tracking-widest uppercase text-orange-400 mb-2">
            {String.fromCodePoint(0x26A1)} Response
          </div>
          <div className="text-4xl md:text-5xl font-bold text-[var(--text)] mb-1">
            &lt;100ms
          </div>
          <div className="text-xs text-[var(--text-dim)]">cached</div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 opacity-70">
            one fetch, served to every agent
          </div>
        </div>

        {/* Coverage */}
        <div className="card p-6 text-center border-l-4 border-red-500">
          <div className="text-xs font-mono tracking-widest uppercase text-red-400 mb-2">
            {String.fromCodePoint(0x1F512)} Coverage
          </div>
          <div className="text-4xl md:text-5xl font-bold text-[var(--text)] mb-1">
            {packagesIndexed.toLocaleString()}+
          </div>
          <div className="text-xs text-[var(--text-dim)]">packages indexed</div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 opacity-70">
            across {ecosystemsCount} ecosystems &middot; {vulnsTracked} CVEs tracked
          </div>
        </div>
      </div>

      <div className="mt-4 text-center text-xs text-[var(--text-dim)]">
        Shared cache = one fetch serves every agent. Less compute, less CO2, safer code.
      </div>
    </div>
  );
}
