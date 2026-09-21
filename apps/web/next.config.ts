import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.NEXT_PUBLIC_DEMO_MODE ? { output: "export" } : {}),
};

export default nextConfig;
