import { Card, CardBody, PageHeader, Section, Footer } from "../../components/ui";

export default function ContactPage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Contact"
          title="Get in touch"
          description="Support, partnerships, or enterprise inquiries."
        />

        <div className="space-y-4">
          <Section>
            <Card>
              <CardBody>
                <h2 className="text-sm font-semibold mb-3">Email</h2>
                <a
                  href="mailto:depscope@cuttalo.com"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded bg-[var(--accent)] text-black hover:bg-[var(--accent-dim)] font-medium text-sm transition"
                >
                  depscope@cuttalo.com
                </a>
              </CardBody>
            </Card>
          </Section>

          <Section title="Company">
            <Card>
              <CardBody>
                <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
                  <dt className="text-[var(--text-dim)]">Name</dt>
                  <dd className="text-[var(--text)]">Cuttalo srl</dd>
                  <dt className="text-[var(--text-dim)]">VAT</dt>
                  <dd className="font-mono tabular-nums text-[var(--text)]">IT03242390734</dd>
                  <dt className="text-[var(--text-dim)]">SDI</dt>
                  <dd className="font-mono tabular-nums text-[var(--text)]">M5UXCR1</dd>
                  <dt className="text-[var(--text-dim)]">Email</dt>
                  <dd>
                    <a href="mailto:depscope@cuttalo.com" className="text-[var(--accent)] hover:underline">
                      depscope@cuttalo.com
                    </a>
                  </dd>
                </dl>
              </CardBody>
            </Card>
          </Section>

          <Section title="Terms">
            <Card>
              <CardBody>
                <div className="text-sm text-[var(--text-dim)] space-y-3 leading-relaxed">
                  <p>
                    DepScope is a free service provided by Cuttalo srl. The API is provided as-is with no guarantees of uptime or accuracy.
                  </p>
                  <p>
                    Data is sourced from public package registries (npm, PyPI, crates.io) and vulnerability databases (OSV, NVD). We do not store personal data beyond what is necessary for rate limiting.
                  </p>
                  <p>
                    By using the API, you agree to fair usage (max 200 requests/minute). Automated abuse will be rate-limited.
                  </p>
                </div>
              </CardBody>
            </Card>
          </Section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
