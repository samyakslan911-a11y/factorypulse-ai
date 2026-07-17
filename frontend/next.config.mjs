/** @type {import('next').NextConfig} */
const nextConfig = {
  trailingSlash: false,
  async rewrites() {
    const backend = process.env.NODE_ENV === "production"
      ? "https://factorypulse-ai-production.up.railway.app"
      : "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
