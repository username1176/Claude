import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.supabase.co" },
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
    ],
  },
  // Allow server-side env to be used in Edge middleware
  serverExternalPackages: ["pdf-lib"],
};

export default nextConfig;
