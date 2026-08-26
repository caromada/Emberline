/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // dev StrictMode double-mounts the GL map (create/destroy/create), which
  // churns WebGL contexts and worker pools for no benefit here
  reactStrictMode: false,
  basePath: process.env.BASE_PATH || "",
  images: { unoptimized: true },
};

export default nextConfig;
