import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "负责任披露 — DepScope",
  description: "如何报告 DepScope 中的安全漏洞、我们的承诺和善意研究的安全港。",
  alternates: {
    canonical: "https://depscope.dev/zh/security/disclosure",
    languages: {
      en: "https://depscope.dev/security/disclosure",
      "zh-CN": "https://depscope.dev/zh/security/disclosure",
    },
  },
};

export default function DisclosurePage() {
  return (
    <LegalLayoutZh eyebrow="安全" title="负责任披露" updated="2026年4月19日">
      <Sec id="scope" title="1. 范围">
        <p>
          <code>depscope.dev</code> 及其子域下的所有端点，包括 API、仪表板、MCP 服务器和
          我们发布的 npm 包 <code>depscope-mcp</code>。
          范围外：第三方服务（Stripe、Cloudflare、npm 注册中心等）和 DoS/负载测试。
        </p>
      </Sec>

      <Sec id="how" title="2. 如何报告">
        <ul className="list-disc ml-6 space-y-1">
          <li>发送邮件至 <A href="mailto:security@depscope.dev">security@depscope.dev</A>。</li>
          <li>提供清晰描述、概念验证、受影响 URL 和您首选的致谢方式。</li>
          <li>如愿意，使用 PGP — 密钥发布于 <A href="/.well-known/security.txt">/.well-known/security.txt</A>。</li>
        </ul>
      </Sec>

      <Sec id="commitments" title="3. 我们的承诺">
        <ul className="list-disc ml-6 space-y-1">
          <li>在 <Strong>3 个工作日</Strong> 内确认您的报告。</li>
          <li>通知您分诊进度和预计修复时间。</li>
          <li>修复部署后（经同意）公开致谢您。</li>
          <li>不对在下列范围内进行的善意研究追究法律责任。</li>
        </ul>
      </Sec>

      <Sec id="rules" title="4. 参与规则">
        <ul className="list-disc ml-6 space-y-1">
          <li>不访问或修改不属于您的数据。</li>
          <li>不运行自动扫描、DoS 或社会工程攻击。</li>
          <li>最小化概念验证的足迹。</li>
          <li>在发布修复之前不公开披露细节。</li>
          <li>遵守所有适用法律。</li>
        </ul>
      </Sec>

      <Sec id="reward" title="5. 奖励">
        <p>
          我们目前不运行付费漏洞赏金计划。我们提供公开致谢、周边产品（如有）以及
          对具有影响力的报告优先访问即将推出的付费层。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
