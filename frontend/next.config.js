/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@radix-ui/react-slot', 'class-variance-authority'],
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['@radix-ui/react-slot', 'class-variance-authority']
  }
}

module.exports = nextConfig
