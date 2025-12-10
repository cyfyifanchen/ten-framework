/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static export for Netlify
  // Remove basePath - serve from root and use Netlify redirects to map /live2d
  reactStrictMode: false, // Disable strict mode to prevent double mounting issues with PIXI
  images: {
    unoptimized: true, // Required for static export
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
