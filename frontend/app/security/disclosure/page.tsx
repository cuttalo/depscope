import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Responsible Disclosure — DepScope",
  description:
    "How to report a security vulnerability in DepScope, our commitments, and safe-harbour for good-faith research.",
  alternates: {
    canonical: "https://depscope.dev/security/disclosure",
    languages: {
      en: "https://depscope.dev/security/disclosure",
      "zh-CN": "https://depscope.dev/zh/security/disclosure",
      "x-default": "https://depscope.dev/security/disclosure",
    },
  },
};

export default function DisclosurePage() {
  return (
    <LegalLayout
      eyebrow="Security"
      title="Responsible Disclosure"
      updated="April 19, 2026"
    >
      <Sec id="scope" title="1. Scope">
        <p>
          All endpoints under <code>depscope.dev</code> and its subdomains,
          including the API, the dashboard, the MCP server, and our published
          npm package <code>depscope-mcp</code>. Out of scope: third-party
          services (Stripe, Cloudflare, npm registry, etc.) and DoS/load tests.
        </p>
      </Sec>

      <Sec id="how" title="2. How to report">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Email <A href="mailto:security@depscope.dev">security@depscope.dev</A>.
          </li>
          <li>
            Provide a clear description, proof-of-concept, affected URL, and
            your preferred credit (name, handle, or anonymous).
          </li>
          <li>
            Use PGP if you prefer — key published at{" "}
            <A href="/.well-known/security.txt">/.well-known/security.txt</A>.
          </li>
        </ul>
      </Sec>

      <Sec id="commitments" title="3. Our commitments">
        <ul className="list-disc ml-6 space-y-1">
          <li>Acknowledge your report within <Strong>3 business days</Strong>.</li>
          <li>
            Keep you informed of triage progress and expected fix timeline.
          </li>
          <li>
            Credit you publicly (with consent) once the fix is deployed.
          </li>
          <li>
            Not pursue legal action for good-faith research conducted within
            the bounds below.
          </li>
        </ul>
      </Sec>

      <Sec id="rules" title="4. Rules of engagement">
        <ul className="list-disc ml-6 space-y-1">
          <li>Do not access or modify data that is not your own.</li>
          <li>
            Do not run automated scans, DoS, or social-engineering attacks.
          </li>
          <li>Minimize the footprint of your proof-of-concept.</li>
          <li>Do not disclose details publicly before a fix is released.</li>
          <li>Comply with all applicable laws.</li>
        </ul>
      </Sec>

      <Sec id="reward" title="5. Reward">
        <p>
          We do not run a paid bug bounty at this time. We offer public
          credit, swag where available, and preferential access to upcoming
          paid tiers for impactful reports.
        </p>
      </Sec>
    </LegalLayout>
  );
}
