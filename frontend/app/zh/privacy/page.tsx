import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "隐私政策 — DepScope",
  description:
    "DepScope（Cuttalo srl）如何收集、使用和保护个人数据。符合GDPR，包含第6条法律依据、欧盟外传输和数据保留期。",
  alternates: {
    canonical: "https://depscope.dev/zh/privacy",
    languages: {
      en: "https://depscope.dev/privacy",
      "zh-CN": "https://depscope.dev/zh/privacy",
    },
  },
};

export default function PrivacyPage() {
  return (
    <LegalLayoutZh title="隐私政策" updated="2026年4月19日">
      <Sec id="controller" title="1. 数据控制者">
        <p>
          <Strong>Cuttalo srl</Strong>，一家在意大利注册的公司，注册办事处位于意大利，
          增值税号 / P.IVA <Strong>IT03242390734</Strong>，
          为通过 DepScope（depscope.dev 及其子域，以下称<Strong>&ldquo;服务&rdquo;</Strong>）
          处理的个人数据的数据控制者（<em>titolare del trattamento</em>）。
        </p>
        <p className="mt-2">
          隐私联系：<A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>。
          一般联系：<A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>。
        </p>
        <p className="mt-2">
          未指定数据保护官 (DPO)：DepScope 不对数据主体进行大规模监控，也不处理特殊类别数据（GDPR 第 37 条）。
          可通过上述邮箱联系<em>隐私代表</em>。
        </p>
      </Sec>

      <Sec id="data-collected" title="2. 我们收集的数据">
        <p className="mb-2">
          <Strong>2.1 匿名 API 访问（无需账户）：</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>IP 地址（经盐化/哈希存储用于速率限制和滥用检测；原始 IP 保留不超过 24 小时）</li>
          <li>User-Agent 字符串</li>
          <li>请求的包名、生态系统、端点、HTTP 方法/状态</li>
          <li>时间戳、响应时间、缓存命中/未命中</li>
        </ul>

        <p className="mt-3 mb-2">
          <Strong>2.2 注册用户（免费 / 付费层）：</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>电子邮件地址（魔术链接认证 — 不存储密码）</li>
          <li>API 密钥指纹（SHA-256；不存原始值）</li>
          <li>每个 API 密钥的用量计数</li>
          <li>会话 Cookie（第一方、严格必要）</li>
          <li>Stripe 客户 ID（仅付费层；我们不存储卡号）</li>
        </ul>

        <p className="mt-3 mb-2">
          <Strong>2.3 我们不收集：</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>密码 — 仅使用魔术链接认证</li>
          <li>支付卡详情 — 完全由 Stripe 处理</li>
          <li>追踪 / 广告 Cookie</li>
          <li>16 岁以下未成年人的数据（本服务不面向未成年人）</li>
          <li>GDPR 第 9 条规定的敏感/特殊类别数据</li>
        </ul>
      </Sec>

      <Sec id="legal-basis" title="3. 法律依据（GDPR 第 6 条）">
        <p className="mb-2">每种处理目的对应特定的法律依据：</p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>合同</Strong> — 第 6(1)(b) 条：提供您请求的服务（API 响应、身份验证、付费层交付）。
          </li>
          <li>
            <Strong>合法利益</Strong> — 第 6(1)(f) 条：反滥用、速率限制、欺诈预防、安全日志、服务质量指标。
            已记录平衡测试；您可反对（参见第 8 条）。
          </li>
          <li>
            <Strong>法律义务</Strong> — 第 6(1)(c) 条：税务和会计记录（意大利民法典第 2220 条 — 10 年）、税务发票。
          </li>
          <li>
            <Strong>同意</Strong> — 第 6(1)(a) 条：营销邮件、非必要 Cookie。可自由给予、具体且可随时撤回。
          </li>
        </ul>
      </Sec>

      <Sec id="retention" title="4. 数据保留期">
        <ul className="list-disc ml-6 space-y-1">
          <li>原始 IP 地址：<Strong>24 小时</Strong>，然后哈希化</li>
          <li>API 访问日志（哈希）：<Strong>180 天</Strong>，然后聚合并匿名化</li>
          <li>魔术链接令牌：<Strong>15 分钟</Strong></li>
          <li>会话 Cookie：<Strong>30 天</Strong> 或直到登出</li>
          <li>账户数据：直到请求删除；不活跃账户在 <Strong>24 个月</Strong> 后删除</li>
          <li>发票和税务记录：<Strong>10 年</Strong>（意大利民法典第 2220 条）</li>
          <li>营销同意记录：撤回后 <Strong>5 年</Strong>（证据）</li>
          <li>备份：<Strong>90 天</Strong> 滚动，然后覆盖</li>
        </ul>
      </Sec>

      <Sec id="sub-processors" title="5. 接收方和子处理者">
        <p>
          我们不出售、出租或交易个人数据。仅与下列子处理者共享数据。
          当前列表位于 <A href="/zh/subprocessors">/zh/subprocessors</A>。
        </p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li><Strong>Stripe Payments Europe, Ltd.</Strong>（爱尔兰，美国附属公司）— 支付处理。</li>
          <li><Strong>Cloudflare, Inc.</Strong>（美国，欧盟 PoP）— CDN、DDoS 防护、DNS。</li>
          <li><Strong>OVHcloud</Strong>（法国）— 加密异地备份。</li>
          <li><Strong>自托管 SMTP</Strong>（欧盟）— 事务性邮件。</li>
        </ul>
      </Sec>

      <Sec id="extra-eu" title="6. 欧洲经济区以外的传输">
        <p>
          向美国供应商（Stripe、Cloudflare）的传输依赖于<Strong>欧盟-美国数据隐私框架</Strong>
          （2023 年 7 月 10 日充分性决定）和<Strong>标准合同条款 2021/914</Strong>（模块 2）。
          如需 SCC 副本，请联系 <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>。
        </p>
      </Sec>

      <Sec id="rights" title="7. 您的权利（GDPR 第 15-22 条）">
        <ul className="list-disc ml-6 space-y-1">
          <li>访问（第 15 条）</li>
          <li>更正（第 16 条）</li>
          <li>删除 — &ldquo;被遗忘权&rdquo;（第 17 条）</li>
          <li>限制处理（第 18 条）</li>
          <li>可移植性（第 20 条）</li>
          <li>反对处理（第 21 条）</li>
          <li>撤回同意（第 7 条）</li>
          <li>不受自动化决策影响（第 22 条 — 我们不进行自动化决策）</li>
        </ul>
        <p className="mt-2">
          请写信至 <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>。
          我们在 30 天内回复（复杂请求可延长至 90 天 — GDPR 第 12 条）。
        </p>
      </Sec>

      <Sec id="complaint" title="8. 投诉权">
        <p>
          您可向意大利数据保护机构（<Strong>Garante per la Protezione dei Dati Personali</Strong>）
          提出投诉：<A href="https://www.garanteprivacy.it">garanteprivacy.it</A>。
        </p>
      </Sec>

      <Sec id="security" title="9. 安全">
        <p>
          所有流量通过 HTTPS（TLS 1.2+）传输。从不存储密码（魔术链接认证）。
          API 密钥在存储前使用 SHA-256 哈希化。详情见 <A href="/zh/security">/zh/security</A>。
        </p>
      </Sec>

      <Sec id="cookies" title="10. Cookie">
        <p>
          我们仅使用严格必要的第一方 Cookie。
          详情和选项见 <A href="/zh/cookies">/zh/cookies</A>。
        </p>
      </Sec>

      <Sec id="changes" title="11. 政策变更">
        <p>
          我们可能更新本政策。重大变更将通过邮件（注册用户）和站点横幅至少在生效前
          <Strong>30 天</Strong> 宣布。
        </p>
      </Sec>

      <Sec id="governing-law" title="12. 适用法律和管辖权">
        <p>
          本政策受<Strong>意大利共和国</Strong>法律及适用的欧盟数据保护法规管辖。
          争议的专属管辖权归属于<Strong>意大利塔兰托法院</Strong>，消费者保护强制规定除外。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
