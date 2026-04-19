import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Acceptable Use Policy — DepScope",
  description:
    "What is and is not allowed when using the DepScope API, dashboard, and MCP server.",
  alternates: {
    canonical: "https://depscope.dev/aup",
    languages: {
      en: "https://depscope.dev/aup",
      "zh-CN": "https://depscope.dev/zh/aup",
      "x-default": "https://depscope.dev/aup",
    },
  },
};

export default function AUPPage() {
  return (
    <LegalLayout title="Acceptable Use Policy" updated="April 19, 2026">
      <Sec id="purpose" title="1. Purpose">
        <p>
          This AUP supplements our <A href="/terms">Terms of Service</A> and
          describes conduct that is prohibited when using the Service. It
          exists to protect the reliability of DepScope for all users and to
          ensure compliance with law.
        </p>
      </Sec>

      <Sec id="allowed" title="2. What is allowed">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Querying the public API for package health, vulnerabilities,
            versions, and related metadata.
          </li>
          <li>
            Integrating DepScope into your AI agent, IDE, CI/CD pipeline, MCP
            client, or developer workflow.
          </li>
          <li>
            Building a product on top of the Service, provided you comply with
            the rate limits, attribution, and data-use rules below.
          </li>
          <li>
            Caching individual query results on your side for up to the cache
            TTL we indicate in the response headers.
          </li>
        </ul>
      </Sec>

      <Sec id="prohibited" title="3. What is prohibited">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Bulk mirroring / redistribution</Strong> of DepScope&apos;s
            datasets (health scores, derived rankings, curated alternatives)
            beyond temporary cache of queries your users made.
          </li>
          <li>
            <Strong>Scraping</Strong> the site, dashboard, or any endpoint
            outside the documented public API.
          </li>
          <li>
            <Strong>Reverse engineering</Strong>, decompiling, or attempting to
            extract the source of the Service or the health-score algorithm.
          </li>
          <li>
            <Strong>Rate-limit circumvention</Strong>: rotating IP addresses,
            distributing a single use case across many accounts, generating
            keys to split a workload designed to stay under a quota.
          </li>
          <li>
            <Strong>Reselling</Strong> the free tier, or bundling the Service
            into a paid offering without a commercial agreement with us.
          </li>
          <li>
            <Strong>Competitor benchmarking</Strong> published without our
            prior written consent.
          </li>
          <li>
            Submitting queries designed to exploit, probe, or attack the
            Service or any related system; submitting malware, phishing, or
            illegal content; unauthorized access attempts.
          </li>
          <li>
            Submitting personal data, credentials, PHI, payment card data, or
            any regulated data as package names or query parameters.
          </li>
          <li>
            Using the Service to violate the intellectual-property rights of a
            third party.
          </li>
          <li>
            Using the Service from countries or on behalf of individuals/
            entities subject to EU, UN, US OFAC, or UK HMT sanctions.
          </li>
        </ul>
      </Sec>

      <Sec id="fair-use" title="4. Fair use on the free tier">
        <ul className="list-disc ml-6 space-y-1">
          <li>200 requests per minute per IP (burst: 50).</li>
          <li>Hard ceiling of 5,000,000 requests per month per identifier.</li>
          <li>
            Excessive load, abusive patterns, or costs disproportionate to
            our infrastructure may trigger throttling or suspension regardless
            of the numerical limits above.
          </li>
        </ul>
      </Sec>

      <Sec id="enforcement" title="5. Enforcement">
        <p>
          We may, at our sole discretion and without prior notice, throttle,
          suspend, or terminate accounts, keys, or IP ranges that violate this
          AUP. Serious violations may be reported to competent authorities.
        </p>
      </Sec>

      <Sec id="report" title="6. Reporting abuse">
        <p>
          To report abuse of the Service or of another user, email{" "}
          <A href="mailto:abuse@depscope.dev">abuse@depscope.dev</A> with
          evidence (logs, timestamps, endpoints). For security vulnerabilities
          see <A href="/security/disclosure">/security/disclosure</A>.
        </p>
      </Sec>
    </LegalLayout>
  );
}
