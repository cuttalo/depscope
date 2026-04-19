import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "安全 — DepScope",
  description: "DepScope 的安全概览：基础设施、加密、访问控制、事件响应。",
  alternates: {
    canonical: "https://depscope.dev/zh/security",
    languages: {
      en: "https://depscope.dev/security",
      "zh-CN": "https://depscope.dev/zh/security",
    },
  },
};

export default function SecurityPage() {
  return (
    <LegalLayoutZh eyebrow="信任" title="安全" updated="2026年4月19日">
      <Sec id="posture" title="1. 我们的立场">
        <p>
          DepScope 设计用于公开公开的软件包元数据。我们不接收客户源代码、密钥或生产数据。
          这使我们的攻击面狭窄，影响范围可预测。
        </p>
      </Sec>

      <Sec id="infra" title="2. 基础设施">
        <ul className="list-disc ml-6 space-y-1">
          <li>主机托管在位于欧盟的 Cuttalo 运营基础设施上。</li>
          <li>所有公开端点前置 Cloudflare：TLS 终止、WAF、DDoS 缓解、机器人评分。</li>
          <li>应用和数据库在私有内部网络中。</li>
          <li>PostgreSQL 17 + Redis 缓存。</li>
          <li>在 OVHcloud（法国 Gravelines）上进行异地加密备份，90 天滚动保留。</li>
        </ul>
      </Sec>

      <Sec id="access" title="3. 认证和访问控制">
        <ul className="list-disc ml-6 space-y-1">
          <li>魔术链接身份验证 — 从不存储密码。</li>
          <li>API 密钥使用加密随机性生成，仅存储为 SHA-256 哈希。</li>
          <li>生产数据库和主机的管理访问仅限 Cuttalo 员工，仅 SSH 密钥，通过 VPN。</li>
        </ul>
      </Sec>

      <Sec id="data" title="4. 传输和静态数据">
        <ul className="list-disc ml-6 space-y-1">
          <li>所有公开流量通过 TLS 1.2+ 传输。</li>
          <li>备份静态加密，密钥与存储提供商分开保管。</li>
          <li>密钥和 API 凭据存储在专用文件中，chmod 600，在 Web 根目录之外。</li>
        </ul>
      </Sec>

      <Sec id="monitoring" title="5. 监控和事件响应">
        <ul className="list-disc ml-6 space-y-1">
          <li>每 6 小时自动检查磁盘、RAM、CPU、数据库、PM2。</li>
          <li>每小时磁盘使用监控和预处理健康检查。</li>
          <li>
            事件响应：24 小时内分诊，Cuttalo 协调修复，在不迟延的情况下通知受影响用户，
            个人数据泄露在 72 小时内通知（GDPR 第 33 条）。
          </li>
        </ul>
      </Sec>

      <Sec id="disclosure" title="6. 报告漏洞">
        <p>
          请遵循我们的 <A href="/zh/security/disclosure">负责任披露政策</A>，
          在公开分享发现之前发送邮件至 <A href="mailto:security@depscope.dev">security@depscope.dev</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
