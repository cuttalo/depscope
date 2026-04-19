export default function ZhIntegratePage() {
  return (
    <div className="min-h-screen p-8 max-w-3xl mx-auto">
      <h1 className="text-4xl font-bold mt-6 mb-2"><span className="gradient-text">集成DepScope</span></h1>
      <p className="text-[var(--text-dim)] mb-8">30秒为您的AI编程助手添加软件包健康检查。无需注册，无需API密钥。</p>

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

        {/* GitHub Actions */}
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-2">GitHub Actions</h2>
          <p className="text-sm text-[var(--text-dim)] mb-4">添加到CI/CD流水线：</p>
          <pre className="bg-[var(--bg)] rounded-lg p-4 text-sm text-[var(--accent)] overflow-x-auto whitespace-pre-wrap">{`- name: DepScope Audit
  run: |
    curl -s -X POST https://depscope.dev/api/scan \\
      -H "Content-Type: application/json" \\
      -d "{\\"ecosystem\\":\\"npm\\",\\"packages\\":$(cat package.json | jq '.dependencies')}" \\
      | jq '.project_risk'`}</pre>
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
