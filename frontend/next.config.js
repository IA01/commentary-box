/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@radix-ui/react-slot', 'class-variance-authority'],
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['@radix-ui/react-slot', 'class-variance-authority']
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.join(__dirname, 'src')
    }
    return config
  }
}

module.exports = nextConfig
