import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import CookieBanner from "./cookie-banner";
import Tracker from "./tracker";
import Nav from "./nav";
import CommandPalette from "../components/CommandPalette";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://depscope.dev"),
  title: {
    default: "DepScope — Package Intelligence for AI Agents",
    template: "%s | DepScope",
  },
  description:
    "Save tokens and energy while shipping safer code. Free API for package health, vulnerabilities, and dependency analysis across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, and more). Built for AI agents.",
  keywords: [
    "package health check", "npm security", "pypi vulnerabilities", "cargo crates audit", "go modules check", "composer php security", "maven java audit", "nuget dotnet check", "rubygems ruby security",
    "dependency check API", "AI agent tools", "MCP server", "software supply chain security",
    "package vulnerability scanner", "open source health score", "AI coding assistant",
    "depscope", "package intelligence",
  ],
  openGraph: {
    title: "DepScope — Free Package Intelligence for AI Agents",
    description: "Check any package before installing. Health score, vulnerabilities, versions. Free API, no auth. Built for AI agents.",
    url: "https://depscope.dev",
    siteName: "DepScope",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "DepScope — Package Intelligence for AI Agents",
    description: "Free API to check package health before installing. No auth. Built for AI.",
  },
  icons: {
    icon: [
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  alternates: {
    canonical: "https://depscope.dev/",
    languages: {
      en: "https://depscope.dev/",
      "zh-CN": "https://depscope.dev/zh",
      "x-default": "https://depscope.dev/",
    },
    types: {
      "application/rss+xml": "https://depscope.dev/feed.xml",
    },
  },
  verification: {
    // google: ""  // already verified via DNS TXT
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const ld = {
    webapi: {
      "@context": "https://schema.org",
      "@type": "WebAPI",
      "name": "DepScope",
      "description":
        "Package Intelligence API for AI Agents. Check health, vulnerabilities, and versions of packages across 17 ecosystems including npm, PyPI, Cargo, Go, Maven, NuGet, and more. Free, no authentication required.",
      "url": "https://depscope.dev",
      "documentation": "https://depscope.dev/api-docs",
      "termsOfService": "https://depscope.dev/contact",
      "provider": {
        "@type": "Organization",
        "name": "Cuttalo srl",
        "url": "https://cuttalo.com",
        "address": { "@type": "PostalAddress", "addressCountry": "IT" },
        "vatID": "IT03242390734",
      },
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "EUR",
        "description": "Free tier: 200 requests per minute, full data access, no authentication",
      },
    },
    website: {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "DepScope",
      "url": "https://depscope.dev",
      "description": "Package Intelligence for AI Agents.",
      "inLanguage": ["en", "zh-CN"],
      "publisher": { "@type": "Organization", "name": "Cuttalo srl", "url": "https://cuttalo.com" },
      "potentialAction": {
        "@type": "SearchAction",
        "target": {
          "@type": "EntryPoint",
          "urlTemplate": "https://depscope.dev/pkg/npm/{search_term_string}",
        },
        "query-input": "required name=search_term_string",
      },
    },
    organization: {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "Cuttalo srl",
      "url": "https://cuttalo.com",
      "logo": "https://depscope.dev/logo.png",
      "sameAs": ["https://depscope.dev"],
    },
    softwareApp: {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "DepScope",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Web",
      "url": "https://depscope.dev",
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "ratingCount": "1",
      },
    },
  };
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <link rel="alternate" hrefLang="en" href="https://depscope.dev/" />
        <link rel="alternate" hrefLang="zh-CN" href="https://depscope.dev/zh" />
        <link rel="alternate" hrefLang="x-default" href="https://depscope.dev/" />
        <link rel="preconnect" href="https://api.npmjs.org" />
        <link rel="preconnect" href="https://pypi.org" />
        <link rel="dns-prefetch" href="https://registry.npmjs.org" />
        <link rel="dns-prefetch" href="https://api.osv.dev" />
        <link
          rel="alternate"
          type="application/rss+xml"
          title="DepScope Trending Packages"
          href="/feed.xml"
        />
        <link
          rel="alternate"
          type="application/atom+xml"
          title="DepScope Trending Packages"
          href="/feed.xml"
        />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld.webapi) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld.website) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld.organization) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld.softwareApp) }} />
      </head>
      <body className="antialiased font-sans">
        <Nav />
        {children}
        <CommandPalette />
        <Tracker />
        <CookieBanner />
      </body>
    </html>
  );
}
