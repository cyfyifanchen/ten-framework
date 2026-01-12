/** @type {import('next').NextConfig} */

import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const nextConfig = {
  output: "standalone",
  reactStrictMode: false,
  outputFileTracingRoot: path.join(__dirname, "./"),
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "i.ebayimg.com",
      },
      {
        protocol: "https",
        hostname: "**.ebay.com",
      },
    ],
  },
};

export default nextConfig;
