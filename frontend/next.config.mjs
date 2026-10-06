/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const rawBackendUrl = process.env.SOL_BACKEND_URL || 'http://51.20.40.103';
    const backendUrl = rawBackendUrl.replace(/\/+$/, '');
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
