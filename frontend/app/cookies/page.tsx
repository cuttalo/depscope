import type { Metadata } from "next";
import { LegalLayout, Sec, Strong, A } from "../../components/legal/LegalLayout";

export const metadata: Metadata = {
  title: "Cookie Policy — DepScope",
  description:
    "Which cookies DepScope uses, why, and how to change your preferences. Compliant with Italian Garante provvedimento of 10 June 2021.",
  alternates: {
    canonical: "https://depscope.dev/cookies",
    languages: {
      en: "https://depscope.dev/cookies",
      "zh-CN": "https://depscope.dev/zh/cookies",
      "x-default": "https://depscope.dev/cookies",
    },
  },
};

export default function CookiesPage() {
  return (
    <LegalLayout title="Cookie Policy" updated="April 19, 2026">
      <Sec id="what" title="1. What are cookies">
        <p>
          Cookies are small text files stored by your browser. Similar
          technologies (localStorage, sessionStorage) are treated here as
          &ldquo;cookies&rdquo; for simplicity. This policy is issued pursuant to art. 13
          GDPR, art. 122 D.Lgs. 196/2003 (Italian Privacy Code), and the Italian{" "}
          <Strong>Garante provvedimento of 10 June 2021</Strong>.
        </p>
      </Sec>

      <Sec id="categories" title="2. Categories of cookies used">
        <p className="mb-2">DepScope uses only first-party cookies, grouped as follows:</p>

        <div className="mt-3">
          <Strong>2.1 Strictly necessary (always on — no consent required)</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>
              <code>ds_session</code> — authenticated session token, HTTP-only,
              Secure, SameSite=Lax. Duration: 30 days.
            </li>
            <li>
              <code>ds_csrf</code> — CSRF protection token. Session lifetime.
            </li>
            <li>
              <code>ds_consent</code> — stores your cookie preferences and
              timestamp. Duration: 6 months (then consent banner re-shown per
              Garante guidance).
            </li>
          </ul>
          <p className="mt-1 text-xs">
            Legal basis: art. 122(1) D.Lgs. 196/2003 — technical cookies, no
            consent needed.
          </p>
        </div>

        <div className="mt-5">
          <Strong>2.2 Analytics (aggregated, privacy-preserving)</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>
              Not currently used. If introduced, they will be anonymized
              server-side (IP truncation, no fingerprinting) and used only with
              your consent via the banner. This policy will be updated and
              consent re-requested before activation.
            </li>
          </ul>
        </div>

        <div className="mt-5">
          <Strong>2.3 Marketing / profiling</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>
              <Strong>None.</Strong> DepScope does not use advertising,
              retargeting, or behavioural profiling cookies.
            </li>
          </ul>
        </div>

        <div className="mt-5">
          <Strong>2.4 Third-party cookies</Strong>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>
              <Strong>Stripe</Strong> — checkout pages may set Stripe cookies for
              fraud prevention and transaction integrity, only during an active
              payment session. See{" "}
              <A href="https://stripe.com/cookies-policy/legal">Stripe cookies</A>.
            </li>
            <li>
              <Strong>Cloudflare</Strong> — may set <code>__cf_bm</code> (bot
              management) as a strictly necessary security measure. Duration: 30
              minutes. See{" "}
              <A href="https://www.cloudflare.com/cookie-policy/">
                Cloudflare cookies
              </A>
              .
            </li>
          </ul>
        </div>
      </Sec>

      <Sec id="consent" title="3. Consent and your choices">
        <p>
          On first visit, a cookie banner appears with two equally-weighted
          buttons: <Strong>Accept all</Strong> and <Strong>Reject all</Strong>,
          plus a <Strong>Customize</Strong> option. Closing the banner (&ldquo;×&rdquo;)
          is treated as refusal. No non-essential cookie is set before you make
          a choice. Browsing, scrolling, or continued navigation does{" "}
          <Strong>not</Strong> imply consent.
        </p>
        <p className="mt-2">
          You can change your choice at any time by clicking{" "}
          <Strong>Cookie settings</Strong> in the footer, or by deleting the{" "}
          <code>ds_consent</code> cookie in your browser. We re-ask for consent
          every 6 months or whenever the set of cookies materially changes.
        </p>
      </Sec>

      <Sec id="browser" title="4. Managing cookies in your browser">
        <p>You can also manage cookies directly via your browser settings:</p>
        <ul className="list-disc ml-6 space-y-1 mt-2">
          <li>
            <A href="https://support.google.com/chrome/answer/95647">Chrome</A>
          </li>
          <li>
            <A href="https://support.mozilla.org/en-US/kb/cookies-information-websites-store-on-your-computer">
              Firefox
            </A>
          </li>
          <li>
            <A href="https://support.apple.com/en-us/HT201265">Safari</A>
          </li>
          <li>
            <A href="https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09">
              Edge
            </A>
          </li>
        </ul>
        <p className="mt-2 text-xs">
          Disabling strictly-necessary cookies will break login and security
          features.
        </p>
      </Sec>

      <Sec id="rights" title="5. Your rights">
        <p>
          You may exercise your GDPR rights on cookie-collected data at any
          time — see <A href="/privacy#rights">Privacy Policy &sect; 8</A>. You
          may also lodge a complaint with the{" "}
          <A href="https://www.garanteprivacy.it">Garante Privacy</A>.
        </p>
      </Sec>

      <Sec id="changes" title="6. Changes">
        <p>
          When we add or change cookies, we update this page and prompt you for
          a fresh choice before any new non-essential cookie is set.
        </p>
      </Sec>
    </LegalLayout>
  );
}
