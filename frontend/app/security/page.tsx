import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Security — DepScope",
  description:
    "DepScope trust and security overview: infrastructure, encryption, access control, incident response.",
  alternates: {
    canonical: "https://depscope.dev/security",
    languages: {
      en: "https://depscope.dev/security",
      "zh-CN": "https://depscope.dev/zh/security",
      "x-default": "https://depscope.dev/security",
    },
  },
};

export default function SecurityPage() {
  return (
    <LegalLayout eyebrow="Trust" title="Security" updated="April 19, 2026">
      <Sec id="posture" title="1. Our posture">
        <p>
          DepScope is designed to expose public package metadata. We do not
          ingest customer source code, secrets, or production data. This keeps
          our attack surface narrow and our blast radius predictable.
        </p>
      </Sec>

      <Sec id="infra" title="2. Infrastructure">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Primary hosting on Cuttalo-operated infrastructure in the EU.
          </li>
          <li>
            Cloudflare in front of all public endpoints: TLS termination, WAF,
            DDoS mitigation, bot scoring.
          </li>
          <li>Application and database on a private internal network.</li>
          <li>
            PostgreSQL 17 + Redis caching; writes go to a single primary.
          </li>
          <li>
            Off-site encrypted backups on OVHcloud (Gravelines, FR), 90-day
            rolling retention.
          </li>
        </ul>
      </Sec>

      <Sec id="access" title="3. Authentication and access control">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Magic-link authentication — no passwords are ever stored.
          </li>
          <li>
            API keys are generated with cryptographic randomness, stored as
            SHA-256 hashes only. We cannot recover a lost key.
          </li>
          <li>
            Administrative access to the production database and hosts is
            limited to Cuttalo staff, SSH key–only, over VPN.
          </li>
        </ul>
      </Sec>

      <Sec id="data" title="4. Data in transit and at rest">
        <ul className="list-disc ml-6 space-y-1">
          <li>All public traffic served over TLS 1.2+.</li>
          <li>
            Backups encrypted at rest with keys held separately from the
            storage provider.
          </li>
          <li>
            Secrets and API credentials held in dedicated files, chmod 600,
            outside webroot, never in environment variables that could leak
            via logs.
          </li>
        </ul>
      </Sec>

      <Sec id="monitoring" title="5. Monitoring and incident response">
        <ul className="list-disc ml-6 space-y-1">
          <li>Automated alerts every 6 hours for disk, RAM, CPU, DB, PM2.</li>
          <li>
            Hourly disk-usage monitor and preprocess health checks.
          </li>
          <li>
            Incident response: triage within 24 hours, remediation coordinated
            by Cuttalo, affected users notified without undue delay and in any
            case within 72 hours for personal-data breaches (art. 33 GDPR).
          </li>
        </ul>
      </Sec>

      <Sec id="supply-chain" title="6. Supply chain">
        <p>
          We dogfood DepScope internally: the service itself is audited through
          DepScope before dependencies are upgraded. CI runs on pinned
          versions; lockfiles are reviewed manually.
        </p>
      </Sec>

      <Sec id="disclosure" title="7. Reporting a vulnerability">
        <p>
          Please follow our{" "}
          <A href="/security/disclosure">responsible disclosure policy</A> and
          email <A href="mailto:security@depscope.dev">security@depscope.dev</A>{" "}
          before publicly sharing findings. We do not run a paid bug bounty,
          but we credit researchers in the project hall of fame on request.
        </p>
      </Sec>
    </LegalLayout>
  );
}
