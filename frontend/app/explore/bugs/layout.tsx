import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Known Bugs per Version | DepScope",
  description:
    "Find known bugs, regressions, and breaking changes per version across npm, PyPI, Cargo and 14 more ecosystems. Skip buggy releases before you install.",
  keywords: [
    "known bugs per version", "npm package bugs", "pypi package issues",
    "cargo crate regressions", "breaking changes package",
  ],
  openGraph: {
    title: "Known Bugs per Version | DepScope",
    description: "Skip buggy releases. Per-version bug database across 17 ecosystems.",
    url: "https://depscope.dev/explore/bugs",
    siteName: "DepScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Known Bugs per Version | DepScope",
    description: "Per-version bug database across 17 ecosystems.",
  },
  alternates: {
    canonical: "https://depscope.dev/explore/bugs",
  },
  robots: { index: true, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Known Bugs per Version",
    "url": "https://depscope.dev/explore/bugs",
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
