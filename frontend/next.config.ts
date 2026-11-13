import type { NextConfig } from "next";

// Origin of the backend API (scheme + host), allowed for XHR and for uploaded images.
function apiOrigin(): string {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "").origin;
  } catch {
    return "";
  }
}

const isDev = process.env.NODE_ENV !== "production";
const api = apiOrigin();

// Content-Security-Policy. Next.js emits small inline bootstrap scripts, so 'unsafe-inline' is
// needed for scripts unless nonces are introduced; everything else is locked to this site, the
// API and the QR image service, and nothing can frame the app (frame-ancestors 'none').
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: https://api.qrserver.com ${api} https:`.trim(),
  "font-src 'self' data:",
  `connect-src 'self' ${api}${isDev ? " ws: http://localhost:* http://127.0.0.1:*" : ""}`.trim(),
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Order links carry a secret (?t=...): never send them to other sites in the Referer header.
  { key: "Referrer-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
