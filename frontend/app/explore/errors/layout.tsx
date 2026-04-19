import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Package Error Fix Database | DepScope",
  description:
    "Search error messages from npm, pip, cargo, go. Get the fix in one click. Cannot find module, ModuleNotFoundError, error[E0433] and thousands more — solved.",
  keywords: [
    "cannot find module fix", "modulenotfounderror solution", "npm error fix",
    "pip error troubleshoot", "cargo error fix", "package error database",
  ],
  openGraph: {
    title: "Error → Fix Database | DepScope",
    description: "Search any package error, get the fix instantly. Across npm, pip, cargo, go.",
    url: "https://depscope.dev/explore/errors",
    siteName: "DepScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Error → Fix Database | DepScope",
    description: "Search any package error, get the fix instantly.",
  },
  alternates: {
    canonical: "https://depscope.dev/explore/errors",
  },
  robots: { index: true, follow: true },
};

const FAQS = [
  {
    q: "What causes `Cannot find module` in Node.js?",
    a: "This happens when the package is not installed, the import path is wrong, or node_modules is out of sync. Run `npm install` again, verify the package name, and check if the module is in package.json dependencies.",
  },
  {
    q: "How do I fix `ModuleNotFoundError` in Python?",
    a: "Install the missing package via `pip install <name>` inside the correct virtual environment. Verify with `pip list`. If using a package manager like poetry or uv, use its install command and re-activate the env.",
  },
  {
    q: "What does Cargo `error[E0433]: failed to resolve` mean?",
    a: "A crate or module path is not found. Ensure the crate is listed in Cargo.toml dependencies, run `cargo build` to fetch it, and check you imported the correct path (e.g. `use serde::Deserialize`).",
  },
  {
    q: "Why does npm show `ERESOLVE unable to resolve dependency tree`?",
    a: "Peer dependency conflict. Try `npm install --legacy-peer-deps` or upgrade the conflicting package. Use DepScope compat matrix to find a working version combination.",
  },
  {
    q: "How to fix `ImportError: attempted relative import with no known parent package`?",
    a: "Run the script as a module: `python -m package.module` instead of `python package/module.py`. Alternatively convert to absolute imports.",
  },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": FAQS.map((f) => ({
      "@type": "Question",
      "name": f.q,
      "acceptedAnswer": { "@type": "Answer", "text": f.a },
    })),
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
