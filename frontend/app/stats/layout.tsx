import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DepScope Stats — API Usage, Packages, Ecosystems",
  description:
    "Live DepScope metrics: packages indexed, vulnerabilities tracked, trending queries, supported ecosystems. Real-time visibility into the package intelligence API.",
  openGraph: {
    title: "DepScope Stats — Live API Metrics",
    description: "Packages indexed, vulnerabilities tracked, trending queries. All live.",
    url: "https://depscope.dev/stats",
    siteName: "DepScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DepScope Stats",
    description: "Live metrics for the package intelligence API.",
  },
  alternates: { canonical: "https://depscope.dev/stats" },
  robots: { index: true, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
