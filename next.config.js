module.exports = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    serverComponentsExternalPackages: ['bullmq', 'ioredis'],
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.githubusercontent.com' },
      { protocol: 'https', hostname: '*.linkedin.com' },
      { protocol: 'https', hostname: '*.glassdoor.com' },
      { protocol: 'https', hostname: '*.indeed.com' },
    ],
  },
  redirects: async () => {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: true,
      },
    ];
  },
  rewrites: async () => {
    return [
      {
        source: '/api/health',
        destination: '/api/health-check',
      },
    ];
  },
  env: {
    MY_ENV_VARIABLE: process.env.MY_ENV_VARIABLE,
  },
};