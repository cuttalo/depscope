export default function ZhApiDocsPage() {
  const endpoints = [
    {
      method: "GET",
      path: "/api/check/{ecosystem}/{package}",
      desc: "完整的软件包智能检测：健康评分、漏洞、版本、推荐建议。",
      example: "curl https://depscope.dev/api/check/npm/express",
      params: [
        { name: "ecosystem", type: "string", desc: "17个支持的生态系统 (见 /api/stats)" },
        { name: "package", type: "string", desc: "软件包名称（支持scope：@org/pkg）" },
        { name: "version", type: "query string", desc: "可选：指定检查的版本" },
      ],
    },
    {
      method: "GET",
      path: "/api/latest/{ecosystem}/{package}",
      desc: "仅获取最新版本。超快速，缓存响应。",
      example: "curl https://depscope.dev/api/latest/npm/express",
      params: [
        { name: "ecosystem", type: "string", desc: "17个支持的生态系统 (见 /api/stats)" },
        { name: "package", type: "string", desc: "软件包名称" },
      ],
    },
    {
      method: "GET",
      path: "/api/exists/{ecosystem}/{package}",
      desc: "检查软件包是否存在于注册表中。返回 true/false。",
      example: "curl https://depscope.dev/api/exists/pypi/django",
      params: [
        { name: "ecosystem", type: "string", desc: "17个支持的生态系统 (见 /api/stats)" },
        { name: "package", type: "string", desc: "软件包名称" },
      ],
    },
    {
      method: "GET",
      path: "/api/health/{ecosystem}/{package}",
      desc: "仅健康评分（0-100）。",
      example: "curl https://depscope.dev/api/health/pypi/fastapi",
      params: [],
    },
    {
      method: "GET",
      path: "/api/vulns/{ecosystem}/{package}",
      desc: "来自OSV数据库的已知漏洞。",
      example: "curl https://depscope.dev/api/vulns/npm/lodash",
      params: [],
    },
    {
      method: "GET",
      path: "/api/versions/{ecosystem}/{package}",
      desc: "版本历史和最新版本信息。",
      example: "curl https://depscope.dev/api/versions/cargo/serde",
      params: [],
    },
    {
      method: "GET",
      path: "/api/search/{ecosystem}",
      desc: "在生态系统中按关键词搜索软件包。",
      example: "curl https://depscope.dev/api/search/npm?q=http",
      params: [
        { name: "ecosystem", type: "string", desc: "17个支持的生态系统 (见 /api/stats)" },
        { name: "q", type: "query string", desc: "搜索关键词" },
      ],
    },
    {
      method: "GET",
      path: "/api/alternatives/{ecosystem}/{package}",
      desc: "获取软件包的推荐替代方案（特别适用于已弃用的软件包）。",
      example: "curl https://depscope.dev/api/alternatives/npm/request",
      params: [
        { name: "ecosystem", type: "string", desc: "17个支持的生态系统 (见 /api/stats)" },
        { name: "package", type: "string", desc: "软件包名称" },
      ],
    },
    {
      method: "GET",
      path: "/api/compare/{ecosystem}/{pkg1},{pkg2},{pkg3}",
      desc: "并排比较多个软件包（2-10个）。",
      example: "curl https://depscope.dev/api/compare/npm/express,fastify,hono",
      params: [],
    },
    {
      method: "POST",
      path: "/api/scan",
      desc: "一次性审计整个项目的依赖（最多100个软件包）。",
      example: 'curl -X POST https://depscope.dev/api/scan -H "Content-Type: application/json" -d \'{"ecosystem":"npm","packages":{"express":"^4.0","lodash":"^4.17"}}\'',
      params: [],
    },
    {
      method: "GET",
      path: "/api/now",
      desc: "当前UTC日期/时间。方便AI助手检查服务器时间。",
      example: "curl https://depscope.dev/api/now",
      params: [],
    },
    {
      method: "GET",
      path: "/api/stats",
      desc: "公开使用统计和热门软件包。",
      example: "curl https://depscope.dev/api/stats",
      params: [],
    },
  ];

  const badgeEndpoints = [
    {
      method: "GET",
      path: "/badge/{ecosystem}/{package}",
      desc: "健康评分徽章（SVG）。嵌入README或文档。显示0-100评分和颜色编码。",
      example: "curl https://depscope.dev/badge/npm/express",
      embedExample: "![DepScope](https://depscope.dev/badge/npm/express)",
      htmlExample: '<img src="https://depscope.dev/badge/npm/express" alt="DepScope health score">',
    },
    {
      method: "GET",
      path: "/badge/score/{ecosystem}/{package}",
      desc: "仅评分徽章（紧凑型）。同样SVG格式，极简风格。",
      example: "curl https://depscope.dev/badge/score/pypi/django",
      embedExample: "![Score](https://depscope.dev/badge/score/pypi/django)",
      htmlExample: '<img src="https://depscope.dev/badge/score/pypi/django" alt="DepScope score">',
    },
  ];

  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mt-6 mb-2"><span className="gradient-text">API文档</span></h1>
      <p className="text-[var(--text-dim)] mb-8">
        免费、开放的API。无需认证。每分钟200次请求。JSON响应。
      </p>

      <div className="card p-4 mb-8 border-l-4 border-l-[var(--accent)]">
        <p className="text-sm"><strong>基础URL:</strong> <code className="text-[var(--accent)]">https://depscope.dev</code></p>
        <p className="text-sm mt-1"><strong>认证:</strong> 无需认证。直接调用。</p>
        <p className="text-sm mt-1"><strong>速率限制:</strong> 每IP 200次请求/分钟</p>
        <p className="text-sm mt-1"><strong>格式:</strong> JSON (UTF-8)</p>
      </div>

      {/* Navigation */}
      <div className="flex gap-4 mb-8">
        <a href="#endpoints" className="text-[var(--accent)] hover:underline text-sm">API接口</a>
        <a href="#badges" className="text-[var(--accent)] hover:underline text-sm">徽章</a>
        <a href="#scoring" className="text-[var(--accent)] hover:underline text-sm">健康评分</a>
        <a href="#ai-agents" className="text-[var(--accent)] hover:underline text-sm">AI助手</a>
      </div>

      <h2 id="endpoints" className="text-2xl font-bold mb-6">API接口</h2>
      <div className="space-y-8">
        {endpoints.map((ep, i) => (
          <div key={i} className="card p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className={`px-2 py-1 text-xs font-bold rounded ${
                ep.method === "GET" ? "bg-green-500/20 text-green-400" : "bg-blue-500/20 text-blue-400"
              }`}>
                {ep.method}
              </span>
              <code className="text-[var(--accent)]">{ep.path}</code>
            </div>
            <p className="text-[var(--text-dim)] text-sm mb-4">{ep.desc}</p>
            {ep.params.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-[var(--text-dim)] mb-2 uppercase tracking-wide">参数</p>
                {ep.params.map((p, j) => (
                  <div key={j} className="flex gap-4 text-sm py-1">
                    <code className="text-[var(--accent)] w-24">{p.name}</code>
                    <span className="text-[var(--text-dim)] w-24">{p.type}</span>
                    <span>{p.desc}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="bg-[var(--bg)] rounded-lg p-3">
              <code className="text-xs text-[var(--text-dim)] break-all">{ep.example}</code>
            </div>
          </div>
        ))}
      </div>

      {/* Badges Section */}
      <h2 id="badges" className="text-2xl font-bold mt-12 mb-6">徽章</h2>
      <p className="text-[var(--text-dim)] text-sm mb-6">
        在您的README、文档或网站中嵌入健康评分徽章。返回带有颜色编码评分的SVG图片。
      </p>
      <div className="space-y-8">
        {badgeEndpoints.map((ep, i) => (
          <div key={i} className="card p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2 py-1 text-xs font-bold rounded bg-purple-500/20 text-purple-400">
                {ep.method}
              </span>
              <code className="text-[var(--accent)]">{ep.path}</code>
            </div>
            <p className="text-[var(--text-dim)] text-sm mb-4">{ep.desc}</p>
            <div className="space-y-3">
              <div className="bg-[var(--bg)] rounded-lg p-3">
                <p className="text-xs text-[var(--text-dim)] mb-1">curl:</p>
                <code className="text-xs text-[var(--text-dim)] break-all">{ep.example}</code>
              </div>
              <div className="bg-[var(--bg)] rounded-lg p-3">
                <p className="text-xs text-[var(--text-dim)] mb-1">Markdown (README):</p>
                <code className="text-xs text-[var(--text-dim)] break-all">{ep.embedExample}</code>
              </div>
              <div className="bg-[var(--bg)] rounded-lg p-3">
                <p className="text-xs text-[var(--text-dim)] mb-1">HTML:</p>
                <code className="text-xs text-[var(--text-dim)] break-all">{ep.htmlExample}</code>
              </div>
            </div>
          </div>
        ))}

        <div className="card p-6">
          <h3 className="text-lg font-bold mb-3">徽章颜色</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="p-3 bg-[var(--bg)] rounded-lg">
              <div className="text-lg font-bold text-green-400">80-100</div>
              <div className="text-xs text-[var(--text-dim)]">绿色</div>
            </div>
            <div className="p-3 bg-[var(--bg)] rounded-lg">
              <div className="text-lg font-bold text-yellow-400">60-79</div>
              <div className="text-xs text-[var(--text-dim)]">黄色</div>
            </div>
            <div className="p-3 bg-[var(--bg)] rounded-lg">
              <div className="text-lg font-bold text-orange-400">40-59</div>
              <div className="text-xs text-[var(--text-dim)]">橙色</div>
            </div>
            <div className="p-3 bg-[var(--bg)] rounded-lg">
              <div className="text-lg font-bold text-red-400">0-39</div>
              <div className="text-xs text-[var(--text-dim)]">红色</div>
            </div>
          </div>
        </div>
      </div>

      <div id="scoring" className="mt-12 card p-6">
        <h2 className="text-xl font-bold mb-4">健康评分详解</h2>
        <p className="text-sm text-[var(--text-dim)] mb-4">
          健康评分（0-100）通过多个信号算法计算：
        </p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
          <div className="p-3 bg-[var(--bg)] rounded-lg">
            <div className="text-lg font-bold text-[var(--accent)]">25</div>
            <div className="text-xs text-[var(--text-dim)]">维护度</div>
            <div className="text-xs text-[var(--text-dim)]">最新发布时间</div>
          </div>
          <div className="p-3 bg-[var(--bg)] rounded-lg">
            <div className="text-lg font-bold text-[var(--accent)]">25</div>
            <div className="text-xs text-[var(--text-dim)]">安全性</div>
            <div className="text-xs text-[var(--text-dim)]">已知CVE</div>
          </div>
          <div className="p-3 bg-[var(--bg)] rounded-lg">
            <div className="text-lg font-bold text-[var(--accent)]">20</div>
            <div className="text-xs text-[var(--text-dim)]">流行度</div>
            <div className="text-xs text-[var(--text-dim)]">每周下载量</div>
          </div>
          <div className="p-3 bg-[var(--bg)] rounded-lg">
            <div className="text-lg font-bold text-[var(--accent)]">15</div>
            <div className="text-xs text-[var(--text-dim)]">成熟度</div>
            <div className="text-xs text-[var(--text-dim)]">版本数量</div>
          </div>
          <div className="p-3 bg-[var(--bg)] rounded-lg">
            <div className="text-lg font-bold text-[var(--accent)]">15</div>
            <div className="text-xs text-[var(--text-dim)]">社区</div>
            <div className="text-xs text-[var(--text-dim)]">维护者数量</div>
          </div>
        </div>
      </div>

      <div id="ai-agents" className="mt-12 card p-6">
        <h2 className="text-xl font-bold mb-4">AI助手集成</h2>
        <p className="text-sm text-[var(--text-dim)] mb-4">
          DepScope专为AI编程助手设计，在建议安装任何软件包前调用。
          API返回任何AI助手都能解析的结构化JSON。
        </p>
        <div className="space-y-3">
          <div className="bg-[var(--bg)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-dim)] mb-1">ChatGPT / OpenAI Actions:</p>
            <code className="text-sm text-[var(--accent)]">https://depscope.dev/.well-known/ai-plugin.json</code>
          </div>
          <div className="bg-[var(--bg)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-dim)] mb-1">OpenAPI规范:</p>
            <code className="text-sm text-[var(--accent)]">https://depscope.dev/openapi.json</code>
          </div>
          <div className="bg-[var(--bg)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-dim)] mb-1">交互式文档 (Swagger):</p>
            <code className="text-sm text-[var(--accent)]">https://depscope.dev/docs</code>
          </div>
        </div>
      </div>

      <footer className="mt-12 border-t border-[var(--border)] py-8 text-center text-sm text-[var(--text-dim)]">
        DepScope — AI编程助手的免费软件包智能检测。 <a href="/zh" className="text-[var(--accent)] hover:underline">首页</a> | <a href="/" className="text-[var(--accent)] hover:underline">English</a>
      </footer>
    </div>
  );
}
