import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader, Section, Card, CardBody, Footer } from "../../../components/ui";

export const metadata: Metadata = {
  title: "法律 — DepScope",
  description: "DepScope 的所有法律、隐私、安全和署名文档。",
  alternates: {
    canonical: "https://depscope.dev/zh/legal",
    languages: {
      en: "https://depscope.dev/legal",
      "zh-CN": "https://depscope.dev/zh/legal",
    },
  },
};

const ITEMS = [
  { href: "/zh/privacy", title: "隐私政策", desc: "我们如何收集、使用和保护个人数据 — 符合 GDPR。" },
  { href: "/zh/terms", title: "服务条款", desc: "管理您使用 DepScope 的合同。" },
  { href: "/zh/aup", title: "可接受使用政策", desc: "服务上允许和禁止的行为。" },
  { href: "/zh/cookies", title: "Cookie 政策", desc: "我们使用的 Cookie、法律依据和偏好更改。" },
  { href: "/zh/attribution", title: "数据署名与许可", desc: "OSV.dev、GitHub Advisory Database 和注册中心的致谢。" },
  { href: "/zh/dpa", title: "数据处理附录", desc: "付费层客户的 GDPR 第 28 条条款。" },
  { href: "/zh/subprocessors", title: "子处理者", desc: "代表我们处理个人数据的第三方。" },
  { href: "/zh/security", title: "安全", desc: "基础设施、加密、访问控制、事件响应。" },
  { href: "/zh/security/disclosure", title: "负责任披露", desc: "如何报告漏洞。善意研究的安全港。" },
  { href: "/zh/imprint", title: "公司信息", desc: "公司详情（Cuttalo srl，意大利）— D.Lgs. 70/2003 第 7 条。" },
];

export default function LegalHubPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="法律"
          title="法律文档"
          description="隐私、条款、署名和安全 — 都在一处。"
        />
        <Section>
          <Card>
            <CardBody>
              <ul className="space-y-3">
                {ITEMS.map((it) => (
                  <li key={it.href} className="border-b border-[var(--border)] pb-3 last:border-0">
                    <Link href={it.href} className="text-[var(--text)] font-medium hover:text-[var(--accent)] transition">
                      {it.title}
                    </Link>
                    <p className="text-xs text-[var(--text-dim)] mt-0.5">{it.desc}</p>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        </Section>
        <p className="text-xs text-[var(--text-dim)] mt-4">
          需要签署的 DPA 或定制 MSA？发送邮件至{" "}
          <a href="mailto:legal@depscope.dev" className="text-[var(--accent)] hover:underline">legal@depscope.dev</a>。
        </p>
      </main>
      <Footer />
    </div>
  );
}
