import Link from "next/link";
import { PageHeader, Section, Card, CardBody, Footer } from "../../components/ui";

export function LegalLayout({
  eyebrow = "Legal",
  title,
  updated,
  children,
}: {
  eyebrow?: string;
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow={eyebrow}
          title={title}
          description={`Last updated: ${updated} · Effective immediately`}
        />
        <Section>
          <Card>
            <CardBody>
              <div className="space-y-8 text-sm text-[var(--text-dim)] leading-relaxed">
                {children}
              </div>
            </CardBody>
          </Card>
        </Section>
        <div className="mt-6 text-xs text-[var(--text-dim)]">
          <Link href="/legal" className="text-[var(--accent)] hover:underline">
            ← Back to Legal hub
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export function H({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-[var(--text)] mb-2 mt-6">
      {children}
    </h2>
  );
}

export function Sec({
  id,
  title,
  children,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id}>
      <H>{title}</H>
      {children}
    </section>
  );
}

export function Strong({ children }: { children: React.ReactNode }) {
  return <strong className="text-[var(--text)]">{children}</strong>;
}

export function A({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const external = href.startsWith("http") || href.startsWith("mailto:");
  if (external) {
    return (
      <a
        href={href}
        className="text-[var(--accent)] hover:underline"
        rel="noopener noreferrer"
        target={href.startsWith("mailto:") ? undefined : "_blank"}
      >
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className="text-[var(--accent)] hover:underline">
      {children}
    </Link>
  );
}
