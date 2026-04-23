import type { NextConfig } from "next";

// Security headers applied to every response (HSTS, CSP, frame, etc.)
// CSP is permissive for images/fonts/styles (Tailwind uses inline styles);
// tighten once we migrate any inline <style> to stylesheets.
const securityHeaders = [
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    key: "X-Frame-Options",
    value: "SAMEORIGIN",
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), interest-cohort=(), " +
      "payment=(), usb=(), autoplay=(), fullscreen=(self)",
  },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      // allow self + inline scripts from Next.js runtime + structured-data scripts
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https: blob:",
      "font-src 'self' data:",
      "connect-src 'self' https://api.depscope.dev https://mcp.depscope.dev https://plausible.io",
      "frame-ancestors 'self'",
      "base-uri 'self'",
      "form-action 'self'",
      "object-src 'none'",
      "upgrade-insecure-requests",
    ].join("; "),
  },
];

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/.well-known/:path*",
        destination: "http://127.0.0.1:8000/.well-known/:path*",
      },
    ];
  },
};

export default nextConfig;
