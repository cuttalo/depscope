import type { Metadata } from "next";
import "../globals.css";
import Tracker from "../tracker";
import CookieBannerZh from "./cookie-banner-zh";

export const metadata: Metadata = {
  metadataBase: new URL("https://depscope.dev"),
  title: {
    default: "DepScope — AI编程助手的软件包健康检测工具",
    template: "%s | DepScope",
  },
  description: "节省令牌和能源，发布更安全的代码。免费API检查17个生态系统（npm、PyPI、Cargo、Go、Maven、NuGet等）软件包的健康状态、漏洞和依赖分析。专为AI代理打造。",
  keywords: [
    "npm安全检查", "PyPI漏洞扫描", "软件包健康评分",
    "AI编程工具", "依赖管理", "供应链安全",
  ],
  openGraph: {
    title: "DepScope — AI编程助手的软件包健康检测工具",
    description: "节省令牌和能源，发布更安全的代码。免费API检查17个生态系统（npm、PyPI、Cargo、Go、Maven、NuGet等）软件包的健康状态、漏洞和依赖分析。专为AI代理打造。",
    url: "https://depscope.dev/zh",
    siteName: "DepScope",
    type: "website",
    locale: "zh_CN",
    images: [{ url: "/zh/opengraph-image", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "DepScope — AI编程助手的软件包健康检测工具",
    description: "免费API检查17个生态系统（npm、PyPI、Cargo、Go、Maven等）软件包的健康状态、漏洞和版本信息。",
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
    },
  },
  alternates: {
    canonical: "https://depscope.dev/zh",
    languages: {
      "en": "https://depscope.dev/",
      "zh-CN": "https://depscope.dev/zh",
      "x-default": "https://depscope.dev/",
    },
  },
};

export default function ZhLayout({ children }: { children: React.ReactNode }) {
  const ld = {
    "@context": "https://schema.org",
    "@type": "WebAPI",
    "name": "DepScope",
    "description": "AI编程助手的软件包智能检测API。检查17个生态系统（npm、PyPI、Cargo、Go、Maven、NuGet等）软件包的健康状态、漏洞和版本信息。免费，无需认证。",
    "url": "https://depscope.dev/zh",
    "inLanguage": "zh-CN",
    "documentation": "https://depscope.dev/zh/api-docs",
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
      "description": "免费: 每分钟200请求，完整数据访问，无需认证",
    },
  };
  return (
    <html lang="zh-CN">
      <head>
        <link rel="alternate" hrefLang="en" href="https://depscope.dev/" />
        <link rel="alternate" hrefLang="zh-CN" href="https://depscope.dev/zh" />
        <link rel="alternate" hrefLang="x-default" href="https://depscope.dev/" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }} />
      </head>
      <body className="antialiased">
        {children}
        <Tracker />
        <CookieBannerZh />
      </body>
    </html>
  );
}
