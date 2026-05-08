import type { Metadata } from "next";
import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";

export const metadata: Metadata = {
  title: "분석 대시보드 | Domo Admin",
};

export default function AnalyticsPage() {
  return <AnalyticsShell />;
}
