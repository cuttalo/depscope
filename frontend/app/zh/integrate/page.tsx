export default function ZhIntegratePage() {
  return (
    <div className="min-h-screen p-8 max-w-3xl mx-auto">
      <h1 className="text-4xl font-bold mt-6 mb-2"><span className="gradient-text">集成DepScope</span></h1>
      <p className="text-[var(--text-dim)] mb-8">30秒为您的AI编程助手添加软件包健康检查。无需注册，无需API密钥。</p>

            <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--text-faded)]">一键安装</div>
            <div className="text-sm text-[var(--text-dim)] mt-1">无需手动编辑 JSON — 选择您的 IDE。</div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/30">29 个工具 · 无需认证</span>
        </div>
        <div className="grid md:grid-cols-3 gap-3 text-sm">
          <a href="cursor://anysphere.cursor-deeplink/mcp/install?name=depscope&config=eyJ1cmwiOiJodHRwczovL21jcC5kZXBzY29wZS5kZXYvbWNwIn0="
             className="rounded border border-[var(--border)] bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] px-4 py-3">
            <div className="font-semibold text-[var(--text)]">添加到 Cursor</div>
            <div className="text-[11px] text-[var(--text-faded)]">打开 Cursor 自动安装。</div>
          </a>
          <div className="rounded border border-[var(--border)] bg-[var(--bg-input)] px-4 py-3">
            <div className="font-semibold text-[var(--text)]">Claude Code</div>
            <div className="text-[11px] text-[var(--text-faded)]">在终端运行一次：</div>
            <code className="block mt-2 font-mono text-[11px] text-[var(--accent)] break-all">claude mcp add depscope --transport http https://mcp.depscope.dev/mcp</code>
          </div>
          <div className="rounded border border-[var(--border)] bg-[var(--bg-input)] px-4 py-3">
            <div className="font-semibold text-[var(--text)]">VS Code (.vscode/mcp.json)</div>
            <code className="block mt-2 font-mono text-[11px] text-[var(--accent)] break-all">{`{"servers":{"depscope":{"type":"http","url":"https://mcp.depscope.dev/mcp"}}}`}</code>
          </div>
        </div>
        <div className="mt-3 text-[11px] text-[var(--text-faded)]">
          Claude Desktop · Windsurf · Cline · Continue.dev · ChatGPT · Aider — 完整代码片段见下方。
        </div>
      </div>

<div className="space-y-8">
        {/* DeepSeek */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">DeepSeek配置</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在DeepSeek Coder的配置中添加以下指令：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`## 软件包健康检查
Before suggesting any install, verify: curl https://depscope.dev/api/check/{npm|pypi|cargo|go|composer|maven|nuget|rubygems}/{package}。
使用 /api/latest/{ecosystem}/{package} 验证正确版本。
使用 /api/exists/{ecosystem}/{package} 验证软件包是否存在。
如果软件包已弃用，使用 /api/alternatives/{ecosystem}/{package} 查找替代方案。
无需认证。免费API：https://depscope.dev`}</pre>
        </div>

        {/* Claude Code */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">Claude Code</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在项目的CLAUDE.md文件中添加：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`## Package Health
Before suggesting any package install, check it with DepScope:
  Before suggesting any install, verify: curl https://depscope.dev/api/check/{npm|pypi|cargo|go|composer|maven|nuget|rubygems}/{package} — no auth, free`}</pre>
        </div>

        {/* Cursor */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">Cursor</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在.cursorrules文件中添加：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`Before suggesting any npm/pip/cargo install, verify the package:
- Check health: https://depscope.dev/api/check/{ecosystem}/{package}
- Check version: https://depscope.dev/api/latest/{ecosystem}/{package}
- Check exists: https://depscope.dev/api/exists/{ecosystem}/{package}
If deprecated, find alternatives: https://depscope.dev/api/alternatives/{ecosystem}/{package}
No API key needed.`}</pre>
        </div>

        {/* Windsurf */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">Windsurf / Codeium</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在.windsurfrules或项目指令中添加：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`When suggesting package installations, first verify with DepScope API:
GET https://depscope.dev/api/check/{ecosystem}/{package}
Ecosystems: npm, pypi, cargo, go, composer, maven, nuget, rubygems. No auth required.`}</pre>
        </div>

        {/* Any Agent */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">任意AI助手 (curl / HTTP)</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">直接调用API。无需认证，无需注册：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`# 检查软件包
curl https://depscope.dev/api/check/npm/express

# 比较软件包
curl https://depscope.dev/api/compare/npm/express,fastify,hono

# 扫描整个项目
curl -X POST https://depscope.dev/api/scan \\
  -H "Content-Type: application/json" \\
  -d '{"ecosystem":"npm","packages":{"express":"*","lodash":"*"}}'`}</pre>
        </div>

        {/* ChatGPT */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">ChatGPT</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在GPT商店搜索{'"'}DepScope{'"'}，或使用OpenAPI规范：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto">https://depscope.dev/openapi-gpt.json</pre>
        </div>

        {/* MCP — remote */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">MCP服务器 (Claude Code / Desktop / Cursor)</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">23个包智能工具，零配置。推荐使用远程MCP端点：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`# 添加到 ~/.claude/mcp_servers.json 或 Cursor mcp.json
{
  "mcpServers": {
    "depscope": { "url": "https://mcp.depscope.dev/mcp" }
  }
}

# 23个可用工具。AI智能体最常用的:
#   ai_brief         — 300 token的包判定
#   audit_stack      — 一次调用审计N个包
#   get_migration_path — 从已弃用迁移到现代包的代码差异`}</pre>
        </div>

        {/* CLI */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">CLI — 安装前一行审计</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在npm上发布为 depscope-cli。需要Node 18+。</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`# 安装前审计（CI友好，关键问题返回exit 1）
npx -y depscope-cli audit express request lodash

# 从清单文件审计
npx -y depscope-cli audit --file package.json
npx -y depscope-cli audit --file requirements.txt

# 已弃用 → 现代包的代码差异
npx -y depscope-cli migration npm request axios

# 单个包的AI简报（约300 tokens，可粘贴到系统提示）
npx -y depscope-cli brief npm/express`}</pre>
        </div>

        {/* Migration Path */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">迁移路径 (已弃用 → 现代包，含代码差异)</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">精选迁移路径，提供可直接应用的 before/after 代码片段。通过 MCP get_migration_path 或 REST API 调用。</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`# MCP工具调用 (第29个工具)
{"name":"get_migration_path","arguments":{"ecosystem":"npm","from_package":"request","to_package":"axios"}}

# REST API
curl https://depscope.dev/api/migration/npm/request/axios
curl https://depscope.dev/api/migration/pypi/urllib2/requests
curl https://depscope.dev/api/migration/npm/moment/dayjs

# 返回: rationale, effort_minutes, diff_examples[], breaking_changes[]`}</pre>
        </div>

        {/* VS Code */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">VS Code (Copilot / Cline / Continue.dev)</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">VS Code 本身不内置 MCP — 通过任意支持 MCP 的 AI 扩展接入。配置相同的 URL 即可。</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`// 1) VS Code + GitHub Copilot (MCP 预览版)
//    Settings: "chat.mcp.enabled": true
//    创建 .vscode/mcp.json (工作区) 或全局配置:
{
  "servers": {
    "depscope": { "type": "http", "url": "https://mcp.depscope.dev/mcp" }
  }
}

// 2) VS Code + Cline — Settings UI → MCP Servers → Add
//    URL: https://mcp.depscope.dev/mcp

// 3) VS Code + Continue.dev (~/.continue/config.json)
{
  "mcpServers": [
    { "name": "depscope",
      "transport": { "type": "sse", "url": "https://mcp.depscope.dev/mcp" } }
  ]
}

// 4) 后备方案 (无 MCP 扩展): .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "DepScope: audit",
      "type": "shell",
      "command": "npx -y depscope-cli audit --file package.json",
      "problemMatcher": []
    }
  ]
}`}</pre>
        </div>

        {/* GitHub Actions */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">GitHub Actions</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在PR检查中自动阻止已弃用/恶意/被利用的软件包：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`name: Dependency audit
on: [pull_request, push]

jobs:
  depscope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cuttalo/depscope-audit-action@v1
        with:
          manifest: package.json
          fail-on: critical   # critical | risk | none`}</pre>
        </div>

        {/* Python */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">Python / LangChain</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">作为LangChain工具使用：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`from langchain.tools import tool
import requests

@tool
def check_package(ecosystem: str, package: str) -> str:
    """检查软件包是否安全可安装。"""
    r = requests.get(f"https://depscope.dev/api/check/{ecosystem}/{package}")
    return r.json()["recommendation"]["summary"]`}</pre>
        </div>

        {/* Badge */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">README徽章</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">在README中添加健康评分徽章：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`[![health](https://depscope.dev/badge/npm/YOUR-PACKAGE)](https://depscope.dev/pkg/npm/YOUR-PACKAGE)`}</pre>
        </div>
      </div>

      <footer className="mt-12 border-t border-[var(--border)] py-8 text-center text-sm text-[var(--text-dim)]">
        DepScope — 免费软件包智能检测。 <a href="/zh" className="text-[var(--accent)] hover:underline">首页</a> | <a href="/zh/api-docs" className="text-[var(--accent)] hover:underline">API文档</a> | <a href="/" className="text-[var(--accent)] hover:underline">English</a>
      </footer>
    </div>
  );
}
