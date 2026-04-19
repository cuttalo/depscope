import type { Metadata } from "next";
import { LegalLayoutZh, Sec, Strong, A } from "../../../components/legal/LegalLayoutZh";

export const metadata: Metadata = {
  title: "子处理者 — DepScope",
  description: "DepScope 使用的第三方子处理者及其作用。",
  alternates: {
    canonical: "https://depscope.dev/zh/subprocessors",
    languages: {
      en: "https://depscope.dev/subprocessors",
      "zh-CN": "https://depscope.dev/zh/subprocessors",
    },
  },
};

const ROWS = [
  {
    name: "Stripe Payments Europe, Ltd.",
    purpose: "支付处理、订阅计费",
    data: "邮箱、Stripe 客户 ID、账单地址、增值税号、卡元数据",
    location: "爱尔兰（欧盟）+ 美国附属公司",
    safeguards: "欧盟-美国 DPF + SCC 2021/914 模块 2",
    link: "https://stripe.com/privacy",
  },
  {
    name: "Cloudflare, Inc.",
    purpose: "CDN、DDoS 缓解、DNS、机器人管理",
    data: "IP 地址、HTTP 元数据、User-Agent",
    location: "美国（总部）；欧盟 PoP",
    safeguards: "欧盟-美国 DPF + SCC 2021/914 模块 2",
    link: "https://www.cloudflare.com/privacypolicy/",
  },
  {
    name: "OVHcloud (OVH SAS)",
    purpose: "异地加密备份（S3 对象存储）",
    data: "加密备份档案（账户、用量、计费数据）",
    location: "法国（欧盟）",
    safeguards: "基于欧盟；静态加密",
    link: "https://www.ovhcloud.com/en/privacy/",
  },
  {
    name: "自托管 SMTP（Cuttalo 基础设施）",
    purpose: "事务性邮件（魔术链接、收据、警报）",
    data: "邮箱、消息内容",
    location: "欧盟（Cuttalo 自有基础设施）",
    safeguards: "Cuttalo srl 直接运营",
    link: "/zh/privacy",
  },
];

export default function SubprocessorsPage() {
  return (
    <LegalLayoutZh title="子处理者" updated="2026年4月19日">
      <Sec id="intro" title="1. 目的">
        <p>
          本页列出根据 GDPR 第 28 条可能代表 Cuttalo srl 处理个人数据的第三方。
          已与每方签署适当的合同保障（DPA、SCC）。
        </p>
      </Sec>

      <Sec id="list" title="2. 当前子处理者">
        <div className="overflow-x-auto -mx-4 md:mx-0 mt-2">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="py-2 pr-3">供应商</th>
                <th className="py-2 pr-3">目的</th>
                <th className="py-2 pr-3">数据</th>
                <th className="py-2 pr-3">位置</th>
                <th className="py-2 pr-3">保障</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr key={r.name} className="border-b border-[var(--border)] align-top">
                  <td className="py-2 pr-3"><A href={r.link}>{r.name}</A></td>
                  <td className="py-2 pr-3">{r.purpose}</td>
                  <td className="py-2 pr-3">{r.data}</td>
                  <td className="py-2 pr-3">{r.location}</td>
                  <td className="py-2 pr-3">{r.safeguards}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Sec>

      <Sec id="changes" title="3. 变更通知">
        <p>
          签署 DPA 的企业客户在新增或替换子处理者前至少 <Strong>30 天</Strong> 收到提前通知。
          订阅变更通知：<A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>。
        </p>
      </Sec>

      <Sec id="dpa" title="4. DPA">
        <p>
          Pro 和 Team 客户可应要求提供数据处理附录：
          <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>。
        </p>
      </Sec>
    </LegalLayoutZh>
  );
}
