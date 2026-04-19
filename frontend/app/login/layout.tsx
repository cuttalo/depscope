import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in — DepScope",
  description: "Sign in to DepScope. Free magic-link auth, no password required.",
  alternates: { canonical: "https://depscope.dev/login" },
  robots: { index: true, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
