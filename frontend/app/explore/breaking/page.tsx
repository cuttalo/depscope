import { PageHeader, Section, Card, CardBody, Footer } from "../../../components/ui";
import BreakingClient, { type ChangeRow } from "./BreakingClient";

export const revalidate = 1800;

async function fetchSamples(): Promise<ChangeRow[]> {
  try {
    const r = await fetch("http://127.0.0.1:8000/api/breaking?limit=12", {
      next: { revalidate: 1800 },
    });
    if (!r.ok) return [];
    const d = await r.json();
    return (d.changes || []) as ChangeRow[];
  } catch {
    return [];
  }
}

export default async function BreakingPage() {
  const initialSamples = await fetchSamples();

  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore · Breaking"
          title="Breaking Changes per Major Version"
          description="Verified breaking changes between major versions, with migration hints. Call this before any major-version bump."
        />

        <BreakingClient initialSamples={initialSamples} />

        <Section className="mt-8">
          <Card>
            <CardBody>
              <h3 className="text-sm font-medium text-[var(--text)] mb-2">
                What we track
              </h3>
              <p className="text-sm text-[var(--text-dim)] leading-relaxed">
                Curated major-version transitions for packages that matter to AI coding agents:
                React, Next.js, Prisma, Express, Node, TypeScript, ESLint, Tailwind, Vite,
                Pydantic, SQLAlchemy, Django, Python, Rust editions, Rails, Laravel, Symfony,
                Spring Boot, Jakarta EE, .NET, Swift and more. Each entry links the breaking
                behaviour with a tested migration command or code pattern.
              </p>
            </CardBody>
          </Card>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
