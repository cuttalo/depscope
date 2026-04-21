"use client";

import { useState } from "react";
import { PageHeader, Section, Card, CardBody, Footer, Badge } from "../../../components/ui";
import { CopyButton } from "../../../components/CopyButton";

type Snippet = { id: string; label: string; file: string; note?: string; snippet: string };

const SNIPPETS: Snippet[] = [
  {
    id: "claude-code",
    label: "Claude Code",
    file: "CLAUDE.md (项目根目录或 ~/.claude/CLAUDE.md)",
    note: "把这段放入 CLAUDE.md,Claude Code 下次启动时自动读取。",
    snippet: `## DEPSCOPE — 建议安装任何包之前
在推荐任何 npm / PyPI / Cargo / Go / Maven / NuGet / RubyGems 等包之前,请调用:

  curl https://depscope.dev/api/prompt/{ecosystem}/{package}

使用返回的 health、CVE、deprecation 信息来决定。
精简的 /api/prompt 端点返回比原始 registry JSON 小约 74% 的有效载荷 — 消耗更少的输入 tokens。
开放、无需认证、每分钟 200 次请求、覆盖 17 个生态系统。源码: https://github.com/cuttalo/depscope`,
  },
  {
    id: "cursor",
    label: "Cursor",
    file: ".cursorrules",
    snippet: `建议或安装任何包之前,调用: curl https://depscope.dev/api/prompt/{ecosystem}/{package}
生态系统: npm, pypi, cargo, go, maven, nuget, rubygems, composer, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew。
使用返回的 health/CVE/deprecation 数据来验证建议。如已弃用,调用 /api/alternatives/{ecosystem}/{package}。精简端点,无需认证。`,
  },
  {
    id: "mcp-remote",
    label: "MCP 远程 (无需安装)",
    file: "mcp.json / claude_desktop_config.json",
    note: "零安装。Claude Desktop / Cursor / Windsurf 通过 URL 连接。自动注册 29 个工具。",
    snippet: `{
  "mcpServers": {
    "depscope": {
      "url": "https://mcp.depscope.dev/mcp"
    }
  }
}`,
  },
  {
    id: "mcp-local",
    label: "MCP 本地 (stdio)",
    file: "mcp.json / claude_desktop_config.json",
    note: "适用于不支持远程 MCP 的客户端。需要: npm install -g depscope-mcp。",
    snippet: `{
  "mcpServers": {
    "depscope": {
      "command": "npx",
      "args": ["depscope-mcp"]
    }
  }
}`,
  },
  {
    id: "curl",
    label: "任何代理 (原始 HTTP)",
    file: "代理的工具 / 插件层",
    snippet: `# Token 高效响应 (比原始 registry JSON 小约 74%)
curl https://depscope.dev/api/prompt/npm/express

# 完整结构化响应
curl https://depscope.dev/api/check/npm/express

# 仅实时 CVE 查询
curl https://depscope.dev/api/vulns/npm/express

# 覆盖 17 个生态系统`,
  },
];

export default function AgentSetupPageZh() {
  const [active, setActive] = useState(SNIPPETS[0].id);
  const cur = SNIPPETS.find(s => s.id === active) || SNIPPETS[0];

  return (
    <div className="min-h-screen">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="面向 AI 代理"
          title="将 DepScope 添加到你的代理"
          description="三行配置,让你的 AI 编程代理(Claude、Cursor、Copilot、ChatGPT 等)在推荐任何包之前都能实时验证。"
        />

        <Section>
          <Card>
            <CardBody>
              <p className="text-sm text-[var(--text-dim)]">
                选择你的集成方式。每个片段都可直接复制粘贴。
                <code>/api/prompt</code> 端点返回的有效载荷比原始 registry JSON <strong className="text-[var(--text)]">小约 74%</strong> — 每次安装决策消耗更少输入 tokens。
              </p>
            </CardBody>
          </Card>
        </Section>

        <Section>
          <Card>
            <div className="flex overflow-x-auto border-b border-[var(--border)]">
              {SNIPPETS.map(s => (
                <button key={s.id} onClick={() => setActive(s.id)}
                  className={`px-4 py-3 text-sm whitespace-nowrap transition border-b-2 ${
                    active === s.id
                      ? "text-[var(--text)] border-[var(--accent)]"
                      : "text-[var(--text-dim)] border-transparent hover:text-[var(--text)]"
                  }`}>
                  {s.label}
                </button>
              ))}
            </div>
            <div className="p-5">
              <div className="flex justify-between items-center mb-2 gap-2">
                <div>
                  <div className="text-[11px] text-[var(--text-dim)] font-mono uppercase tracking-wide">{cur.file}</div>
                  {cur.note && <div className="text-xs text-[var(--text-dim)] mt-1">{cur.note}</div>}
                </div>
                <CopyButton text={cur.snippet} />
              </div>
              <pre className="bg-[var(--bg-soft)] border border-[var(--border)] rounded p-4 text-xs text-[var(--accent)] overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
                {cur.snippet}
              </pre>
            </div>
          </Card>
        </Section>

        <Section title="为什么添加这个?">
          <Card>
            <CardBody>
              <ul className="space-y-2 text-sm text-[var(--text-dim)]">
                <li>→ <strong className="text-[var(--text)]">节省 tokens</strong>:原始 registry JSON 是 ~3 KB 模型不需要的键。/api/prompt 返回紧凑字符串 — 相同的安装信号,更少的输入消耗。</li>
                <li>→ <strong className="text-[var(--text)]">当前漏洞数据</strong>:OSV.dev + GitHub Advisory Database 作为实时 API。不再根据 6-12 个月前的训练数据做建议。</li>
                <li>→ <strong className="text-[var(--text)]">弃用与替代方案</strong>:如果包已弃用,响应会说明并提供替代方案。</li>
                <li>→ <strong className="text-[var(--text)]">无虚构包名</strong>:/api/exists 在代理建议安装之前确认包是否真实存在。</li>
                <li>→ <strong className="text-[var(--text)]">覆盖 17 个生态系统</strong>:npm、PyPI、Cargo、Go、Maven、NuGet、RubyGems、Composer、Pub、Hex、Swift、CocoaPods、CPAN、Hackage、CRAN、Conda、Homebrew。</li>
                <li>→ <strong className="text-[var(--text)]">开放基础设施</strong>:MIT 许可证,无需认证,每分钟 200 次请求。核心查询必须保持开放 — AI 代理不会在认证后查询。</li>
              </ul>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
