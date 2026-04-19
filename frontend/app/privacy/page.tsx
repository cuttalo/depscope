import { Card, CardBody, PageHeader, Section, Footer } from "../../components/ui";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Legal"
          title="Privacy Policy"
          description="Last updated: April 16, 2026"
        />

        <Section>
          <Card>
            <CardBody>
              <div className="space-y-8 text-sm text-[var(--text-dim)] leading-relaxed">
                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">1. Who we are</h2>
                  <p>
                    DepScope is a service provided by <strong className="text-[var(--text)]">Cuttalo srl</strong>, Italy. VAT: IT03242390734. Contact: depscope@cuttalo.com
                  </p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">2. What data we collect</h2>
                  <p className="mb-1"><strong className="text-[var(--text)]">API Usage (no authentication required):</strong></p>
                  <ul className="list-disc ml-6 space-y-1">
                    <li>IP address (for rate limiting only, not stored permanently)</li>
                    <li>User-Agent header (to understand which AI agents use our service)</li>
                    <li>Package names queried (to improve our cache and pre-processing)</li>
                    <li>Timestamps of requests</li>
                  </ul>
                  <p className="mt-3 mb-1"><strong className="text-[var(--text)]">Registered users (optional):</strong></p>
                  <ul className="list-disc ml-6 space-y-1">
                    <li>Email address (for magic link authentication)</li>
                    <li>Session tokens (for maintaining login state)</li>
                  </ul>
                  <p className="mt-3">
                    <strong className="text-[var(--text)]">We do NOT collect:</strong> passwords (we use magic links), payment card details (handled by Stripe), personal browsing data, cookies for tracking.
                  </p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">3. How we use data</h2>
                  <ul className="list-disc ml-6 space-y-1">
                    <li>Rate limiting: IP addresses are used to enforce fair usage (200 req/min)</li>
                    <li>Service improvement: aggregate API usage data helps us decide which packages to pre-cache</li>
                    <li>Communication: email addresses are used only for login magic links and service notifications</li>
                    <li>Anonymized analytics: salted IP hashes, not raw IPs, no user-level profiling, no resale</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">4. Data sharing</h2>
                  <p>We do not sell, rent, or share personal data with third parties. The only exceptions:</p>
                  <ul className="list-disc ml-6 space-y-1 mt-2">
                    <li>
                      <strong className="text-[var(--text)]">Stripe</strong>: processes payments securely. See{" "}
                      <a href="https://stripe.com/privacy" className="text-[var(--accent)] hover:underline">Stripe Privacy Policy</a>
                    </li>
                    <li>
                      <strong className="text-[var(--text)]">Cloudflare</strong>: provides CDN and DDoS protection. See{" "}
                      <a href="https://www.cloudflare.com/privacypolicy/" className="text-[var(--accent)] hover:underline">Cloudflare Privacy Policy</a>
                    </li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">5. Data retention</h2>
                  <ul className="list-disc ml-6 space-y-1">
                    <li>API usage logs: retained for 90 days, then deleted</li>
                    <li>User accounts: retained until deletion is requested</li>
                    <li>Package data: public data from registries, cached and updated regularly</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">6. Your rights (GDPR)</h2>
                  <p>Under EU GDPR, you have the right to:</p>
                  <ul className="list-disc ml-6 space-y-1 mt-2">
                    <li>Access your personal data</li>
                    <li>Rectify inaccurate data</li>
                    <li>Delete your data (&ldquo;right to be forgotten&rdquo;)</li>
                    <li>Port your data to another service</li>
                    <li>Object to processing</li>
                  </ul>
                  <p className="mt-2">
                    To exercise these rights, email{" "}
                    <a href="mailto:depscope@cuttalo.com" className="text-[var(--accent)] hover:underline">depscope@cuttalo.com</a>
                  </p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">7. Cookies</h2>
                  <p>
                    We use only essential cookies for session management. We do not use tracking, analytics, or advertising cookies.
                  </p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">8. Security</h2>
                  <p>
                    All data is transmitted over HTTPS. Passwords are not stored (magic link auth). Payment processing is handled entirely by Stripe. Database access is restricted to internal network only.
                  </p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">9. Changes</h2>
                  <p>We may update this policy. Changes will be posted on this page with an updated date.</p>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-[var(--text)] mb-2">10. Contact</h2>
                  <p>
                    For privacy inquiries:{" "}
                    <a href="mailto:depscope@cuttalo.com" className="text-[var(--accent)] hover:underline">depscope@cuttalo.com</a>
                  </p>
                  <p>Cuttalo srl, Italy</p>
                </section>
              </div>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
