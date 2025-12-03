/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  basePath: '/live2d',
  reactStrictMode: false, // Disable strict mode to prevent double mounting issues with PIXI
  async rewrites() {
    return [
      {
        source: '/live2d/models/:path*',
        destination: 'https://ten-framework-assets.s3.amazonaws.com/live2d-models/:path*',
      },
    ];
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
