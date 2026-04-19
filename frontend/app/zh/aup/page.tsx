import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "可接受使用政策 — DepScope",
  description: "使用 DepScope API、仪表板和 MCP 服务器时允许和禁止的行为。",
  alternates: {
    canonical: "https://depscope.dev/zh/aup",
    languages: {
      en: "https://depscope.dev/aup",
      "zh-CN": "https://depscope.dev/zh/aup",
    },
  },
};

export default function AUPPage() {
  return (
    <LegalLayoutZh title="可接受使用政策" updated="2026年4月19日">
      <Sec id="purpose" title="1. 目的">
        <p>
          本 AUP 补充我们的 <A href="/zh/terms">服务条款</A>，描述使用服务时禁止的行为。
          其存在是为了保护 DepScope 对所有用户的可靠性并确保合法合规。
        </p>
      </Sec>

      <Sec id="allowed" title="2. 允许的行为">
        <ul className="list-disc ml-6 space-y-1">
          <li>查询公开 API 获取软件包健康、漏洞、版本及相关元数据。</li>
          <li>将 DepScope 集成到您的 AI 代理、IDE、CI/CD 流程、MCP 客户端或开发者工作流中。</li>
          <li>在服务上构建产品（符合速率限制、署名和下列数据使用规则）。</li>
          <li>在响应标头指定的缓存 TTL 内在您端缓存查询结果。</li>
        </ul>
      </Sec>

      <Sec id="prohibited" title="3. 禁止的行为">
        <ul className="list-disc ml-6 space-y-1">
          <li><Strong>批量镜像 / 再分发</Strong> DepScope 数据集（超出用户临时缓存范围）。</li>
          <li><Strong>抓取</Strong> 站点、仪表板或记录的公开 API 以外的任何端点。</li>
          <li><Strong>逆向工程</Strong>、反编译或尝试提取服务源代码或健康分算法。</li>
          <li><Strong>绕过速率限制</Strong>：轮换 IP、跨多账户分发同一用例、生成密钥以拆分工作负载。</li>
          <li><Strong>转售</Strong>免费层，或未与我们签订商业协议即将服务打包进付费产品。</li>
          <li><Strong>竞品基准</Strong> 未经我们事先书面同意即发布。</li>
          <li>提交旨在利用、探测或攻击服务的查询；提交恶意软件、钓鱼或非法内容；尝试未经授权访问。</li>
          <li>将个人数据、凭证、PHI、支付卡数据或任何受监管数据作为包名或查询参数提交。</li>
          <li>使用服务侵犯第三方知识产权。</li>
          <li>从受欧盟、联合国、美国 OFAC 或英国 HMT 制裁的国家/实体使用服务。</li>
        </ul>
      </Sec>

      <Sec id="fair-use" title="4. 免费层合理使用">
        <ul className="list-disc ml-6 space-y-1">
          <li>每 IP 每分钟 200 个请求（突发 50）。</li>
          <li>每个标识符每月 500 万请求的硬上限。</li>
          <li>过度负载或滥用模式可能触发限流或暂停，与上述数值无关。</li>
        </ul>
      </Sec>

      <Sec id="enforcement" title="5. 执行">
        <p>
          我们可在无事先通知的情况下全权决定限流、暂停或终止违反本 AUP 的账户、密钥或 IP 范围。
          严重违规可能被报告给主管部门。
        </p>
      </Sec>

      <Sec id="report" title="6. 举报滥用">
        <p>
          举报服务滥用或其他用户的滥用：
          <A href="mailto:abuse@depscope.dev">abuse@depscope.dev</A>（附日志、时间戳、端点）。
          安全漏洞见 <A href="/zh/security/disclosure">/zh/security/disclosure</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
