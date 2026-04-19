import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Privacy Policy — DepScope",
  description:
    "How DepScope (Cuttalo srl) collects, uses, and protects personal data. GDPR-compliant, with art.6 legal bases, extra-EU transfers, and data retention.",
  alternates: {
    canonical: "https://depscope.dev/privacy",
    languages: {
      en: "https://depscope.dev/privacy",
      "zh-CN": "https://depscope.dev/zh/privacy",
      "x-default": "https://depscope.dev/privacy",
    },
  },
};

export default function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy" updated="April 19, 2026">
      <Sec id="controller" title="1. Data controller">
        <p>
          <Strong>Cuttalo srl</Strong>, a company incorporated in Italy,
          registered office in Italy, VAT / P.IVA <Strong>IT03242390734</Strong>
          , acts as the data controller (<em>titolare del trattamento</em>) for
          personal data processed through DepScope (depscope.dev and subdomains,
          the <Strong>&ldquo;Service&rdquo;</Strong>).
        </p>
        <p className="mt-2">
          Privacy contact: <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>.
          General contact: <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>.
        </p>
        <p className="mt-2">
          No Data Protection Officer (DPO) is appointed: DepScope does not
          perform large-scale monitoring of data subjects or process special
          categories of data (art. 37 GDPR). A <em>privacy referent</em> is
          available at the address above.
        </p>
      </Sec>

      <Sec id="data-collected" title="2. Data we collect">
        <p className="mb-2">
          <Strong>2.1 Anonymous API access (no account):</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            IP address (stored salted/hashed for rate limiting and abuse
            detection; raw IP not retained beyond 24 hours)
          </li>
          <li>User-Agent string</li>
          <li>Requested package name, ecosystem, endpoint, HTTP method/status</li>
          <li>Timestamp, response time, cache hit/miss</li>
        </ul>

        <p className="mt-3 mb-2">
          <Strong>2.2 Registered users (free / paid tier):</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>Email address (magic-link authentication — no password stored)</li>
          <li>API key fingerprints (SHA-256; never raw)</li>
          <li>Usage counters per API key</li>
          <li>Session cookies (first-party, strictly necessary)</li>
          <li>Stripe customer ID (paid tiers only; no card data stored by us)</li>
        </ul>

        <p className="mt-3 mb-2">
          <Strong>2.3 We do NOT collect:</Strong>
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>Passwords — magic-link authentication only</li>
          <li>Payment card details — handled entirely by Stripe</li>
          <li>Tracking / advertising cookies</li>
          <li>Data on minors under 16 (service not intended for minors)</li>
          <li>Sensitive/special categories of data (art. 9 GDPR)</li>
        </ul>
      </Sec>

      <Sec id="legal-basis" title="3. Legal basis (art. 6 GDPR)">
        <p className="mb-2">
          Each processing purpose maps to a specific legal basis:
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Contract</Strong> — art. 6(1)(b): providing the Service
            you request (API responses, authentication, paid-tier delivery).
          </li>
          <li>
            <Strong>Legitimate interest</Strong> — art. 6(1)(f): anti-abuse,
            rate-limit enforcement, fraud prevention, security logs,
            service-quality metrics. Balancing test documented; you can object
            (see &sect; 8).
          </li>
          <li>
            <Strong>Legal obligation</Strong> — art. 6(1)(c): tax and accounting
            records (art. 2220 Italian Civil Code — 10 years), fiscal invoices,
            AML obligations where applicable.
          </li>
          <li>
            <Strong>Consent</Strong> — art. 6(1)(a): marketing emails,
            non-essential cookies. Freely given, specific, revocable at any
            time.
          </li>
        </ul>
      </Sec>

      <Sec id="purposes" title="4. Purposes of processing">
        <ul className="list-disc ml-6 space-y-1">
          <li>Operate and deliver the Service (API, dashboard, MCP server)</li>
          <li>Enforce free-tier rate limits (200 req/min per IP)</li>
          <li>Detect and block abuse, scraping, denial-of-service</li>
          <li>
            Improve caching strategy based on aggregate request patterns (no
            user-level profiling)
          </li>
          <li>Bill paid tiers and issue invoices</li>
          <li>Send service-critical notifications (security, downtime)</li>
          <li>Send marketing emails — only with prior opt-in consent</li>
        </ul>
      </Sec>

      <Sec id="retention" title="5. Retention periods">
        <ul className="list-disc ml-6 space-y-1">
          <li>Raw IP addresses: <Strong>24 hours</Strong>, then hashed</li>
          <li>
            API access logs (hashed): <Strong>180 days</Strong>, then aggregated
            and anonymized
          </li>
          <li>Magic-link tokens: <Strong>15 minutes</Strong></li>
          <li>Session cookies: <Strong>30 days</Strong> or until logout</li>
          <li>
            Account data: until deletion requested; dormant accounts deleted
            after <Strong>24 months</Strong> of inactivity
          </li>
          <li>
            Invoices and tax records: <Strong>10 years</Strong> (art. 2220 c.c.
            Italy)
          </li>
          <li>Marketing consent records: <Strong>5 years</Strong> after withdrawal (evidence)</li>
          <li>Backups: <Strong>90 days</Strong> rolling, then overwritten</li>
        </ul>
      </Sec>

      <Sec id="sub-processors" title="6. Recipients and sub-processors">
        <p>
          We do not sell, rent, or trade personal data. We share data only with
          the sub-processors below. A current list is maintained at{" "}
          <A href="/subprocessors">/subprocessors</A>.
        </p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>
            <Strong>Stripe Payments Europe, Ltd.</Strong> (Ireland, with
            affiliates in the US) — payment processing, billing. See{" "}
            <A href="https://stripe.com/privacy">Stripe Privacy</A>.
          </li>
          <li>
            <Strong>Cloudflare, Inc.</Strong> (US, with EU PoPs) — CDN, DDoS
            protection, DNS. See{" "}
            <A href="https://www.cloudflare.com/privacypolicy/">
              Cloudflare Privacy
            </A>
            .
          </li>
          <li>
            <Strong>OVH / OVHcloud SAS</Strong> (France) — object storage (S3
            GRA) for encrypted off-site backups.
          </li>
          <li>
            <Strong>Self-hosted SMTP</Strong> (EU, our infrastructure) —
            transactional email (magic link, receipts).
          </li>
          <li>
            <Strong>Anthropic, PBC</Strong> (US) — only for the optional MCP
            integration if you connect DepScope tools to Claude; we do not
            initiate this transfer.
          </li>
        </ul>
      </Sec>

      <Sec id="extra-eu" title="7. Transfers outside the EEA">
        <p>
          Transfers to US providers (Stripe, Cloudflare) rely on both the{" "}
          <Strong>EU–US Data Privacy Framework</Strong> (adequacy decision of
          10 July 2023) and <Strong>Standard Contractual Clauses 2021/914</Strong>{" "}
          (Module 2), supplemented by the sub-processor&apos;s technical and
          organizational measures. You may request a copy of the SCCs by writing
          to <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>.
        </p>
      </Sec>

      <Sec id="rights" title="8. Your rights (GDPR arts. 15–22)">
        <ul className="list-disc ml-6 space-y-1">
          <li>Access — confirmation and copy of your data (art. 15)</li>
          <li>Rectification — correct inaccurate data (art. 16)</li>
          <li>Erasure — &ldquo;right to be forgotten&rdquo; (art. 17)</li>
          <li>Restriction — pause processing (art. 18)</li>
          <li>Portability — export in machine-readable format (art. 20)</li>
          <li>Object — oppose processing based on legitimate interest (art. 21)</li>
          <li>Withdraw consent — without affecting prior processing (art. 7)</li>
          <li>Not be subject to automated decision-making (art. 22) — we do none</li>
        </ul>
        <p className="mt-2">
          Write to{" "}
          <A href="mailto:privacy@depscope.dev">privacy@depscope.dev</A>. We
          respond within 30 days (extendable to 90 for complex requests — art.
          12 GDPR). Exercising rights is free; we may charge a reasonable fee
          only for manifestly unfounded or excessive requests.
        </p>
      </Sec>

      <Sec id="complaint" title="9. Right to lodge a complaint">
        <p>
          You may lodge a complaint with the Italian data protection authority
          (<Strong>Garante per la Protezione dei Dati Personali</Strong>, Piazza
          Venezia 11, 00187 Roma):{" "}
          <A href="https://www.garanteprivacy.it">garanteprivacy.it</A>. Users
          in other EEA states can contact their local supervisory authority.
        </p>
      </Sec>

      <Sec id="security" title="10. Security">
        <p>
          All traffic is served over HTTPS (TLS 1.2+). Passwords are never
          stored (magic-link auth). API keys are hashed with SHA-256 before
          storage. Database access is restricted to private network. Encrypted
          backups are stored off-site at OVH Gravelines (EU).
        </p>
        <p className="mt-2">
          To report a security issue, see{" "}
          <A href="/security/disclosure">/security/disclosure</A> or{" "}
          <A href="mailto:security@depscope.dev">security@depscope.dev</A>.
        </p>
      </Sec>

      <Sec id="cookies" title="11. Cookies">
        <p>
          We use only strictly necessary first-party cookies for session
          management and CSRF protection. Full cookie details, categories, and
          your choices are described at <A href="/cookies">/cookies</A>.
        </p>
      </Sec>

      <Sec id="changes" title="12. Changes to this policy">
        <p>
          We may update this policy. Material changes will be announced via
          email to registered users and a banner at the top of the site at
          least <Strong>30 days</Strong> before taking effect. The updated
          version will replace the current one with a new &ldquo;Last updated&rdquo; date.
        </p>
      </Sec>

      <Sec id="governing-law" title="13. Governing law and jurisdiction">
        <p>
          This policy is governed by the laws of the <Strong>Italian Republic</Strong>{" "}
          and applicable EU data-protection regulations. Exclusive jurisdiction
          for disputes is vested in the <Strong>Courts of Taranto, Italy</Strong>, save
          for mandatory consumer protection rules granting the consumer the
          right to sue in their place of domicile.
        </p>
      </Sec>
    </LegalLayout>
  );
}
