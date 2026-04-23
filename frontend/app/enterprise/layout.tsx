import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DepScope for Enterprise — private MCP, SSO, SLA, audit",
  description:
    "DepScope Enterprise (Q1 2027): private MCP server, SSO, audit export (CycloneDX/SPDX), 99.95% SLA, dedicated support. Waitlist open — first 50 teams get design-partner pricing.",
  alternates: { canonical: "https://depscope.dev/enterprise" },
  openGraph: {
    title: "DepScope for Enterprise",
    description:
      "Private MCP + SSO + SLA + audit export. Waitlist Q1 2027.",
    url: "https://depscope.dev/enterprise",
    type: "article",
  },
  robots: { index: true, follow: true },
};

export default function EnterpriseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
