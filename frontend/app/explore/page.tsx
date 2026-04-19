import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardBody, PageHeader, Footer } from "../../components/ui";

export const metadata: Metadata = {
  title: "Explore — Trending, Errors, Compat, Bugs, Breaking | DepScope",
  description:
    "Five dimensions of package intelligence for AI agents: trending packages, error → fix database, stack compatibility, known bugs per version, and major-version breaking changes with migration hints.",
  alternates: { canonical: "https://depscope.dev/explore" },
  robots: { index: true, follow: true },
};

const DIMENSIONS = [
  {
    href: "/explore/trending",
    eyebrow: "Trending",
    title: "What AI agents are searching right now",
    description:
      "Live rank, weekly growth, ecosystem breakdown. Discover what real agents install before they ship.",
  },
  {
    href: "/explore/errors",
    eyebrow: "Errors",
    title: "Error → Fix database",
    description:
      "Paste a stack trace. Get the exact fix from issues, docs, and maintainer answers across 17 ecosystems.",
  },
  {
    href: "/explore/compat",
    eyebrow: "Compat",
    title: "Stack compatibility checker",
    description:
      "Build a stack. Verify combinations like next@16 + react@19 + tailwind@4 before you start.",
  },
  {
    href: "/explore/bugs",
    eyebrow: "Bugs",
    title: "Known bugs per package & version",
    description:
      "Version-specific regressions tracked from GitHub issues, registries, and maintainer notes.",
  },
  {
    href: "/explore/breaking",
    eyebrow: "Breaking",
    title: "Breaking changes per major version",
    description:
      "React 18→19, Next 14→15, Prisma 5→6, Pydantic v1→v2 and dozens more — each with verified migration hints.",
  },
];

export default function ExplorePage() {
  return (
    <div className="min-h-screen">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <PageHeader
          eyebrow="Explore"
          title="More than package health"
          description="Four dimensions of package intelligence. All free, all open, all cached for every agent."
        />
        <div className="grid md:grid-cols-2 gap-4">
          {DIMENSIONS.map((d) => (
            <Link key={d.href} href={d.href} className="group">
              <Card className="h-full hover:border-[var(--accent)]/50 transition">
                <CardBody>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--accent)] mb-2">
                    {d.eyebrow}
                  </div>
                  <h2 className="text-lg font-semibold tracking-tight group-hover:text-[var(--accent)] transition">
                    {d.title}
                  </h2>
                  <p className="text-sm text-[var(--text-dim)] mt-1 leading-relaxed">
                    {d.description}
                  </p>
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
