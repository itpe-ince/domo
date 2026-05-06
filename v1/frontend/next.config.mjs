import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",

  // lucide-react, date-fns 트리셰이킹 최적화 (G''-6)
  experimental: {
    optimizePackageImports: ["lucide-react", "date-fns"],
  },

  webpack(config, { isServer }) {
    // Konva ships a separate Node.js entry (konva/lib/index-node.js) that
    // requires the optional `canvas` npm package. That package is not
    // installed (and not needed — ImageEditor uses browser Canvas via
    // react-konva with ssr:false). Aliasing `canvas` to false tells
    // webpack to replace the require with an empty module for both the
    // server and client bundles, silencing the "Can't resolve 'canvas'"
    // build error without affecting runtime behaviour.
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };

    // 클라이언트 번들 vendor chunk 분리 (G''-6 번들 최종화)
    // 서버 번들에는 미적용 — SSR hydration mismatch 방지
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: "all",
        cacheGroups: {
          // React 코어 — 변경 빈도 낮음, 장기 캐시에 유리
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            name: "vendor-react",
            chunks: "all",
            priority: 40,
          },
          // Next.js 런타임
          next: {
            test: /[\\/]node_modules[\\/]next[\\/]/,
            name: "vendor-next",
            chunks: "all",
            priority: 30,
          },
          // PostHog — 분석 SDK, 결제 페이지 외 지연 로드 가능
          posthog: {
            test: /[\\/]node_modules[\\/]posthog-js[\\/]/,
            name: "vendor-posthog",
            chunks: "all",
            priority: 20,
          },
          // Stripe.js — 결제 페이지에서만 필요
          stripe: {
            test: /[\\/]node_modules[\\/](@stripe|stripe)[\\/]/,
            name: "vendor-stripe",
            chunks: "all",
            priority: 20,
          },
          // 기타 공통 vendor (2개 이상 페이지에서 사용)
          commons: {
            test: /[\\/]node_modules[\\/]/,
            name: "vendor-commons",
            chunks: "all",
            minChunks: 2,
            priority: 10,
          },
        },
      };
    }

    return config;
  },
};

export default withBundleAnalyzer(nextConfig);
