import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Stack Compatibility Matrix | DepScope",
  description:
    "Verify your package stack works before you install. React + Next.js + Tailwind? Django + Celery + Redis? Check verified and broken stacks across npm, PyPI, and more.",
  keywords: [
    "package compatibility matrix", "stack compatibility check",
    "react nextjs compatible versions", "django celery compatibility",
    "dependency resolver", "peer dependency check",
  ],
  openGraph: {
    title: "Stack Compatibility Matrix | DepScope",
    description: "Verified and broken package combinations — know before you install.",
    url: "https://depscope.dev/explore/compat",
    siteName: "DepScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Stack Compatibility Matrix | DepScope",
    description: "Verified and broken package combinations.",
  },
  alternates: {
    canonical: "https://depscope.dev/explore/compat",
  },
  robots: { index: true, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Stack Compatibility Matrix",
    "url": "https://depscope.dev/explore/compat",
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
