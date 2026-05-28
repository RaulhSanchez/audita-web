import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",          // genera carpeta /out con HTML estático
  images: { unoptimized: true }, // GitHub Pages no tiene Image Optimization
  trailingSlash: true,       // evita 404s en rutas con sub-path en gh-pages
};

export default nextConfig;
