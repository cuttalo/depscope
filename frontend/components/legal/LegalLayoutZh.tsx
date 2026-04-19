import Link from "next/link";
import { PageHeader, Section, Card, CardBody, Footer } from "../../components/ui";

export function LegalLayoutZh({
  eyebrow = "法律",
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
          description={`最后更新: ${updated} · 即时生效`}
        />
        <Section>
          <Card>
            <CardBody>
              <div className="space-y-8 text-sm text-[var(--text-dim)] leading-relaxed">
                <div className="border border-[var(--border)] rounded-lg p-3 bg-[var(--bg-soft)] text-xs">
                  <strong className="text-[var(--text)]">语言说明：</strong>{" "}
                  本页为英文版本的中文翻译，仅供参考。如中英文版本存在差异，以
                  <Link
                    href={"/" + (eyebrow === "安全" ? "security" : "")}
                    className="text-[var(--accent)] hover:underline"
                  >
                    英文版本
                  </Link>
                  为准。
                </div>
                {children}
              </div>
            </CardBody>
          </Card>
        </Section>
        <div className="mt-6 text-xs text-[var(--text-dim)]">
          <Link
            href="/zh/legal"
            className="text-[var(--accent)] hover:underline"
          >
            ← 返回法律中心
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
