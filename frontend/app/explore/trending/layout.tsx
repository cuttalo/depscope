import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Trending Packages — What AI Agents Install Now | DepScope",
  description:
    "Live trending packages across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, more). See weekly growth, rank changes, and what AI coding agents install right now.",
  keywords: [
    "trending npm packages", "trending python packages", "trending rust crates",
    "most installed packages this week", "ai agent popular packages",
  ],
  openGraph: {
    title: "Trending Packages — DepScope",
    description: "What AI agents install right now. Live rank across 17 ecosystems.",
    url: "https://depscope.dev/explore/trending",
    siteName: "DepScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Trending Packages — DepScope",
    description: "Live rank across 17 ecosystems.",
  },
  alternates: {
    canonical: "https://depscope.dev/explore/trending",
  },
  robots: { index: true, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Trending Packages",
    "description": "Top packages installed right now, measured by live AI-agent demand.",
    "url": "https://depscope.dev/explore/trending",
    "isPartOf": { "@type": "WebSite", "name": "DepScope", "url": "https://depscope.dev" },
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {children}
    </>
  );
}
