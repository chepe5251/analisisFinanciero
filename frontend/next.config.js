/** @type {import('next').NextConfig} */
const nextConfig = {
  // Reescribe /api/* al backend FastAPI para evitar CORS en desarrollo
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
