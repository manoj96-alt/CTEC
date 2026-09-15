import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // AUTH-BUG-R1: an explicit, documented Next.js mechanism for injecting
  // this one build-time value, alongside (not instead of) the standard
  // NEXT_PUBLIC_* auto-inlining every other value here still relies on --
  // empirically, the automatic path was found unreliable for this
  // specific reference under the real ACR remote build agent's
  // constrained environment (see frontend/lib/auth/config.ts). This does
  // not change any value or any other environment variable's behavior.
  env: {
    NEXT_PUBLIC_OIDC_API_RESOURCE_URI:
      process.env.NEXT_PUBLIC_OIDC_API_RESOURCE_URI,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http://localhost:8000 http://localhost:8081 https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          { key: "Cache-Control", value: "no-store" },
        ],
      },
    ];
  },
};
export default nextConfig;
