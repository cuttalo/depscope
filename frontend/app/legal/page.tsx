import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader, Section, Card, CardBody, Footer } from "../../components/ui";

export const metadata: Metadata = {
  title: "Legal — DepScope",
  description:
    "All legal, privacy, security, and attribution documents for DepScope in one place.",
  alternates: {
    canonical: "https://depscope.dev/legal",
    languages: {
      en: "https://depscope.dev/legal",
      "zh-CN": "https://depscope.dev/zh/legal",
      "x-default": "https://depscope.dev/legal",
    },
  },
};

const ITEMS = [
  {
    href: "/privacy",
    title: "Privacy Policy",
    desc: "How we collect, use, and protect personal data — GDPR compliant.",
  },
  {
    href: "/terms",
    title: "Terms of Service",
    desc: "The contract governing your use of DepScope.",
  },
  {
    href: "/aup",
    title: "Acceptable Use Policy",
    desc: "What is allowed and prohibited on the Service.",
  },
  {
    href: "/cookies",
    title: "Cookie Policy",
    desc: "Cookies we use, legal basis, and how to change your preferences.",
  },
  {
    href: "/attribution",
    title: "Data Attribution & Licenses",
    desc: "Credits for OSV.dev, GitHub Advisory Database, and registries.",
  },
  {
    href: "/dpa",
    title: "Data Processing Addendum",
    desc: "GDPR art. 28 terms for paid-tier customers.",
  },
  {
    href: "/subprocessors",
    title: "Sub-processors",
    desc: "Third parties that process personal data on our behalf.",
  },
  {
    href: "/security",
    title: "Security",
    desc: "Infrastructure, encryption, access control, incident response.",
  },
  {
    href: "/security/disclosure",
    title: "Responsible Disclosure",
    desc: "How to report a vulnerability. Safe-harbour for good-faith research.",
  },
  {
    href: "/imprint",
    title: "Imprint",
    desc: "Company details (Cuttalo srl, Italy) — art. 7 D.Lgs. 70/2003.",
  },
];

export default function LegalHubPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Legal"
          title="Legal documents"
          description="Privacy, terms, attribution, and security — all in one place."
        />
        <Section>
          <Card>
            <CardBody>
              <ul className="space-y-3">
                {ITEMS.map((it) => (
                  <li
                    key={it.href}
                    className="border-b border-[var(--border)] pb-3 last:border-0"
                  >
                    <Link
                      href={it.href}
                      className="text-[var(--text)] font-medium hover:text-[var(--accent)] transition"
                    >
                      {it.title}
                    </Link>
                    <p className="text-xs text-[var(--text-dim)] mt-0.5">
                      {it.desc}
                    </p>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        </Section>
        <p className="text-xs text-[var(--text-dim)] mt-4">
          Need a signed DPA or a custom MSA? Email{" "}
          <a
            href="mailto:legal@depscope.dev"
            className="text-[var(--accent)] hover:underline"
          >
            legal@depscope.dev
          </a>
          .
        </p>
      </main>
      <Footer />
    </div>
  );
}
