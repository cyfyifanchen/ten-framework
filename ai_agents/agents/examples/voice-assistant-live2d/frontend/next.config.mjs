/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static export for Netlify
  basePath: '/live2d',
  reactStrictMode: false, // Disable strict mode to prevent double mounting issues with PIXI
  images: {
    unoptimized: true, // Required for static export
  },
  async rewrites() {
    // Note: rewrites don't work in static export mode
    // Model loading is handled by Netlify redirects instead
    return [];
  },
  webpack: (config, { webpack }) => {
    // Provide PIXI as a global variable for pixi-live2d-display
    config.plugins.push(
      new webpack.ProvidePlugin({
        PIXI: 'pixi.js',
      })
    );

    return config;
  },
};

export default nextConfig;
