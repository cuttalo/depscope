import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Terms of Service — DepScope",
  description:
    "Terms governing your use of the DepScope API, dashboard, and MCP server. Free tier, paid tiers, acceptable use, liability.",
  alternates: {
    canonical: "https://depscope.dev/terms",
    languages: {
      en: "https://depscope.dev/terms",
      "zh-CN": "https://depscope.dev/zh/terms",
      "x-default": "https://depscope.dev/terms",
    },
  },
};

export default function TermsPage() {
  return (
    <LegalLayout title="Terms of Service" updated="April 19, 2026">
      <Sec id="acceptance" title="1. Acceptance">
        <p>
          These Terms form a binding agreement between <Strong>Cuttalo srl</Strong>{" "}
          (Italy, VAT IT03242390734, &ldquo;DepScope&rdquo;, &ldquo;we&rdquo;) and you
          (&ldquo;Customer&rdquo;, &ldquo;you&rdquo;). By accessing depscope.dev, its APIs,
          dashboards, MCP server, or any related service (the &ldquo;Service&rdquo;), you
          accept these Terms, the <A href="/privacy">Privacy Policy</A>, the{" "}
          <A href="/aup">Acceptable Use Policy</A>, and the{" "}
          <A href="/cookies">Cookie Policy</A>. If you do not accept, do not use
          the Service.
        </p>
      </Sec>

      <Sec id="service" title="2. The Service">
        <p>
          DepScope is a package intelligence API that aggregates public data
          from software registries (npm, PyPI, Cargo, Go, Composer, Maven,
          NuGet, RubyGems, Pub, Hex, Swift, CocoaPods, CPAN, Hackage, CRAN,
          Conda, Homebrew) and security feeds (OSV.dev, GitHub Advisory
          Database) to help AI agents and developers evaluate packages before
          installing them. The Service does not host or distribute the
          packages themselves.
        </p>
      </Sec>

      <Sec id="tiers" title="3. Tiers, limits, metering">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Free tier</Strong>: up to 200 requests per minute per IP,
            no authentication required, no uptime commitment.
          </li>
          <li>
            <Strong>Paid tiers</Strong> (Pro, Team): higher quotas, API keys,
            priority support. Pricing is published at the point of purchase.
          </li>
          <li>
            We may change quotas, throttle, or temporarily suspend the Service
            at our sole discretion to protect system integrity.
          </li>
          <li>
            <Strong>Hard monthly cap</Strong> for a single customer is 5,000,000
            requests on free tier; beyond that, upgrade to paid tier or face
            suspension.
          </li>
        </ul>
      </Sec>

      <Sec id="accounts" title="4. Accounts and API keys">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Authentication is via magic link emailed to your address; no
            passwords are stored.
          </li>
          <li>
            You are responsible for keeping API keys (<code>ds_live_*</code> and{" "}
            <code>ds_test_*</code>) confidential. Rotate or revoke compromised
            keys via the dashboard.
          </li>
          <li>
            You must not share a single account or key across multiple unrelated
            organizations (no reselling the free tier).
          </li>
        </ul>
      </Sec>

      <Sec id="billing" title="5. Billing and refunds (paid tiers)">
        <ul className="list-disc ml-6 space-y-1">
          <li>Subscriptions bill monthly or annually, in EUR, via Stripe.</li>
          <li>
            <Strong>Auto-renewal</Strong>: subscriptions renew automatically
            until cancelled. You may cancel any time in the dashboard; access
            remains until the end of the paid period.
          </li>
          <li>
            <Strong>EU consumers</Strong> have a 14-day right of withdrawal
            (D.Lgs. 21/2014) starting from purchase. By using the Service
            during this period, you acknowledge that the right ceases once
            digital services are performed with your prior express consent.
          </li>
          <li>
            We may revise prices with at least 30 days&apos; notice for the next
            billing cycle.
          </li>
          <li>
            Taxes (VAT/IVA): displayed prices exclude VAT unless stated; VAT is
            applied per your billing country and EU rules. B2B customers with a
            valid VAT ID established outside Italy may be billed under reverse
            charge.
          </li>
        </ul>
      </Sec>

      <Sec id="acceptable-use" title="6. Acceptable Use">
        <p>
          Your use of the Service is governed by our{" "}
          <A href="/aup">Acceptable Use Policy</A>. Violations may result in
          throttling, suspension, or termination without prior notice. The AUP
          prohibits, among other things: scraping outside documented APIs,
          reverse engineering, circumventing rate limits via rotating keys or
          IPs, reselling the Service on the free tier, submitting unlawful or
          infringing queries, and loading the Service with automated tooling in
          ways that degrade availability for other users.
        </p>
      </Sec>

      <Sec id="data-disclaimers" title="7. No warranty on data">
        <p>
          DepScope relies on third-party sources. Vulnerability data, health
          scores, deprecation flags, and version information may be incomplete,
          delayed, or inaccurate.{" "}
          <Strong>
            The Service is provided &ldquo;AS IS&rdquo; and &ldquo;AS AVAILABLE&rdquo;, without
            warranties of any kind, whether express, implied, statutory, or
            otherwise, to the maximum extent permitted by law
          </Strong>
          , including merchantability, fitness for a particular purpose,
          non-infringement, and accuracy. You remain solely responsible for
          decisions made based on DepScope output, including which packages to
          install in your stack.
        </p>
      </Sec>

      <Sec id="ip" title="8. Intellectual property">
        <p>
          DepScope retains all rights in the Service&apos;s software, design,
          trademarks, documentation, and proprietary datasets (including the
          computed health scores). Third-party data (OSV.dev, GitHub Advisory
          Database, registries) remains the property of its respective owners
          and is subject to their licenses — see{" "}
          <A href="/attribution">/attribution</A>.
        </p>
        <p className="mt-2">
          You may not: (i) copy, modify, or create derivative works of the
          Service; (ii) decompile, disassemble, or reverse engineer it; (iii)
          use our name, logos, or trademarks without written permission; (iv)
          publish comparative benchmarks of the Service without our prior
          written consent.
        </p>
      </Sec>

      <Sec id="prohibited" title="9. Prohibited conduct">
        <ul className="list-disc ml-6 space-y-1">
          <li>Using the Service in violation of any applicable law or regulation</li>
          <li>
            Using the Service to distribute malware, phishing, or content
            infringing third-party IP
          </li>
          <li>
            Accessing the Service from jurisdictions sanctioned by the EU, UN,
            US OFAC, or UK HMT, or on behalf of a sanctioned person or entity
          </li>
          <li>
            Submitting personal data, credentials, or regulated data (PHI, card
            data, etc.) to the API — DepScope is not designed to process such
            data
          </li>
          <li>
            Attempting to gain unauthorized access, probe, scan, or disrupt the
            Service or related systems
          </li>
        </ul>
      </Sec>

      <Sec id="termination" title="10. Suspension and termination">
        <p>
          We may suspend or terminate your access — with or without notice — if
          you breach these Terms, the AUP, or applicable law, or if required
          by law or to protect the Service and its users. You may terminate at
          any time by closing your account in the dashboard or emailing{" "}
          <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>. On
          termination, you may export your account data for 30 days; thereafter
          data is deleted according to the retention schedule in the{" "}
          <A href="/privacy#retention">Privacy Policy</A>.
        </p>
      </Sec>

      <Sec id="liability" title="11. Limitation of liability">
        <p>
          To the maximum extent permitted by Italian law:
        </p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>
            DepScope will not be liable for any indirect, incidental,
            consequential, special, or exemplary damages, including lost
            profits, lost data, or business interruption.
          </li>
          <li>
            Our total aggregate liability for any claim arising out of or
            related to the Service shall not exceed the greater of (a){" "}
            <Strong>€50</Strong> or (b) the fees paid by you to DepScope in the{" "}
            <Strong>12 months</Strong> preceding the event giving rise to the
            claim.
          </li>
          <li>
            Nothing in these Terms limits liability for gross negligence, wilful
            misconduct (<em>dolo</em>), death or personal injury caused by
            negligence, or any other liability that cannot be excluded under
            art. 1229 of the Italian Civil Code or applicable consumer law.
          </li>
        </ul>
      </Sec>

      <Sec id="indemnity" title="12. Indemnification">
        <p>
          You agree to indemnify and hold harmless Cuttalo srl, its directors,
          employees, and agents, from any third-party claim arising out of your
          breach of these Terms, your misuse of the Service, or your violation
          of any law or third-party right.
        </p>
      </Sec>

      <Sec id="changes" title="13. Changes to these Terms">
        <p>
          We may update these Terms to reflect legal, technical, or business
          changes. Material changes will be announced via email (registered
          users) and a banner at least <Strong>30 days</Strong> in advance.
          Continued use after the effective date constitutes acceptance.
        </p>
      </Sec>

      <Sec id="misc" title="14. Miscellaneous">
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <Strong>Severability</Strong>: if any provision is unenforceable,
            the remainder continues in effect.
          </li>
          <li>
            <Strong>Assignment</Strong>: you may not assign these Terms without
            our written consent; we may assign them to an affiliate or successor
            in a corporate transaction.
          </li>
          <li>
            <Strong>No waiver</Strong>: failure to enforce a provision is not a
            waiver of our right to do so later.
          </li>
          <li>
            <Strong>Entire agreement</Strong>: these Terms, together with the
            documents linked, constitute the entire agreement between the
            parties.
          </li>
          <li>
            <Strong>Force majeure</Strong>: neither party is liable for delays
            or failures caused by events beyond reasonable control.
          </li>
        </ul>
      </Sec>

      <Sec id="law" title="15. Governing law and jurisdiction">
        <p>
          These Terms are governed by Italian law, excluding its conflict of
          laws rules and the UN Convention on Contracts for the International
          Sale of Goods. Exclusive jurisdiction for disputes is vested in the{" "}
          <Strong>Courts of Taranto, Italy</Strong>, save for mandatory consumer
          protection rules.
        </p>
      </Sec>

      <Sec id="contact" title="16. Contact">
        <p>
          Cuttalo srl — Italy — VAT IT03242390734 —{" "}
          <A href="mailto:depscope@cuttalo.com">depscope@cuttalo.com</A>.
        </p>
      </Sec>
    </LegalLayout>
  );
}
