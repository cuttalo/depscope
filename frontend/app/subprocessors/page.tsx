import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Sub-processors — DepScope",
  description:
    "List of third-party sub-processors used by DepScope and their role. Updated as the list changes.",
  alternates: {
    canonical: "https://depscope.dev/subprocessors",
    languages: {
      en: "https://depscope.dev/subprocessors",
      "zh-CN": "https://depscope.dev/zh/subprocessors",
      "x-default": "https://depscope.dev/subprocessors",
    },
  },
};

const ROWS = [
  {
    name: "Stripe Payments Europe, Ltd.",
    purpose: "Payment processing, subscription billing",
    data: "Email, Stripe customer ID, billing address, VAT ID, card metadata",
    location: "Ireland (EU) + US affiliates",
    safeguards: "EU–US DPF + SCC 2021/914 Module 2",
    link: "https://stripe.com/privacy",
  },
  {
    name: "Cloudflare, Inc.",
    purpose: "CDN, DDoS mitigation, DNS, bot management",
    data: "IP address, HTTP metadata, User-Agent",
    location: "US (HQ); EU PoPs for traffic",
    safeguards: "EU–US DPF + SCC 2021/914 Module 2",
    link: "https://www.cloudflare.com/privacypolicy/",
  },
  {
    name: "OVHcloud (OVH SAS)",
    purpose: "Off-site encrypted backups (S3-compatible object storage)",
    data: "Encrypted backup archives containing account, usage, and billing data",
    location: "France (EU)",
    safeguards: "EU-based; encryption at rest",
    link: "https://www.ovhcloud.com/en/privacy/",
  },
  {
    name: "Self-hosted SMTP (Cuttalo infrastructure)",
    purpose: "Transactional email (magic-link, receipts, alerts)",
    data: "Email address, message content",
    location: "EU (Cuttalo own infrastructure)",
    safeguards: "Operated directly by Cuttalo srl",
    link: "/privacy",
  },
];

export default function SubprocessorsPage() {
  return (
    <LegalLayout title="Sub-processors" updated="April 19, 2026">
      <Sec id="intro" title="1. Purpose">
        <p>
          This page lists the third parties that may process personal data
          on behalf of Cuttalo srl in the course of operating DepScope, pursuant
          to art. 28 GDPR. Adequate contractual safeguards (DPAs, SCCs) are in
          place with each. The list is kept current as the set changes.
        </p>
      </Sec>

      <Sec id="list" title="2. Current sub-processors">
        <div className="overflow-x-auto -mx-4 md:mx-0 mt-2">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="py-2 pr-3">Provider</th>
                <th className="py-2 pr-3">Purpose</th>
                <th className="py-2 pr-3">Data</th>
                <th className="py-2 pr-3">Location</th>
                <th className="py-2 pr-3">Safeguards</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr
                  key={r.name}
                  className="border-b border-[var(--border)] align-top"
                >
                  <td className="py-2 pr-3">
                    <A href={r.link}>{r.name}</A>
                  </td>
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

      <Sec id="changes" title="3. Change notifications">
        <p>
          Enterprise customers with a signed DPA receive at least{" "}
          <Strong>30 days&apos; advance notice</Strong> before adding or
          replacing a sub-processor. To subscribe to change notifications,
          email <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>.
          You may object to a new sub-processor for reasonable data-protection
          grounds; if a workable alternative is not possible, you may terminate
          the affected service.
        </p>
      </Sec>

      <Sec id="dpa" title="4. DPA">
        <p>
          A Data Processing Addendum is available to Pro and Team customers on
          request at <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>.
        </p>
      </Sec>
    </LegalLayout>
  );
}
