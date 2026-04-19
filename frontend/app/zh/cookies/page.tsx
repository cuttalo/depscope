import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "Cookie 政策 — DepScope",
  description: "DepScope 使用的 Cookie、原因，以及如何更改您的偏好。",
  alternates: {
    canonical: "https://depscope.dev/zh/cookies",
    languages: {
      en: "https://depscope.dev/cookies",
      "zh-CN": "https://depscope.dev/zh/cookies",
    },
  },
};

export default function CookiesPage() {
  return (
    <LegalLayoutZh title="Cookie 政策" updated="2026年4月19日">
      <Sec id="what" title="1. 什么是 Cookie">
        <p>
          Cookie 是浏览器存储的小型文本文件。
          本政策依据 GDPR 第 13 条、意大利数据保护法（D.Lgs. 196/2003）第 122 条及
          <Strong>2021 年 6 月 10 日意大利 Garante 条例</Strong>发布。
        </p>
      </Sec>

      <Sec id="categories" title="2. 使用的 Cookie 类别">
        <p className="mb-2">DepScope 仅使用第一方 Cookie：</p>

        <div className="mt-3">
          <Strong>2.1 严格必要（始终启用 — 无需同意）</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li><code>ds_session</code> — 身份验证会话令牌。时长：30 天。</li>
            <li><code>ds_csrf</code> — CSRF 保护令牌。会话期间。</li>
            <li><code>ds_consent</code> — 存储您的 Cookie 偏好和时间戳。时长：6 个月。</li>
          </ul>
        </div>

        <div className="mt-5">
          <Strong>2.2 分析（汇总，保护隐私）</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>目前不使用。如引入，将服务器端匿名化，仅在您通过横幅同意后使用。</li>
          </ul>
        </div>

        <div className="mt-5">
          <Strong>2.3 营销 / 画像</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li><Strong>无。</Strong> DepScope 不使用广告、再定向或行为画像 Cookie。</li>
          </ul>
        </div>

        <div className="mt-5">
          <Strong>2.4 第三方 Cookie</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li><Strong>Stripe</Strong> — 结账页面可能设置 Stripe Cookie 用于欺诈预防。</li>
            <li><Strong>Cloudflare</Strong> — 可能设置 <code>__cf_bm</code>（机器人管理）作为严格必要的安全措施。</li>
          </ul>
        </div>
      </Sec>

      <Sec id="consent" title="3. 同意和您的选择">
        <p>
          首次访问时会显示 Cookie 横幅，包含同等权重的两个按钮：
          <Strong>全部接受</Strong> 和 <Strong>全部拒绝</Strong>，加上 <Strong>自定义</Strong> 选项。
          关闭横幅（&ldquo;×&rdquo;）被视为拒绝。在您选择之前不设置任何非必要 Cookie。
          浏览、滚动或继续导航<Strong>不</Strong>视为同意。
        </p>
        <p className="mt-2">
          您可以随时通过页脚的 <Strong>Cookie 设置</Strong> 更改选择。每 6 个月或 Cookie 集发生重大变化时重新询问。
        </p>
      </Sec>

      <Sec id="browser" title="4. 在浏览器中管理 Cookie">
        <p>您也可通过浏览器设置直接管理 Cookie：Chrome、Firefox、Safari、Edge。</p>
      </Sec>

      <Sec id="rights" title="5. 您的权利">
        <p>
          您可随时行使 Cookie 收集数据的 GDPR 权利 — 见 <A href="/zh/privacy#rights">隐私政策 &sect; 7</A>。
          也可向 <A href="https://www.garanteprivacy.it">Garante Privacy</A> 提出投诉。
        </p>
      </Sec>

      <Sec id="changes" title="6. 变更">
        <p>当我们添加或更改 Cookie 时，我们会更新本页面并在设置任何新的非必要 Cookie 之前提示您重新选择。</p>
      </Sec>
    </LegalLayoutZh>
  );
}
