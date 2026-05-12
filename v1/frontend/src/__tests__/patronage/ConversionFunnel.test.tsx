/**
 * ConversionFunnel.test.tsx — B'-5 Patronage Analytics
 *
 * Tests funnel chart rendering for sponsorship conversion steps.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { ConversionFunnel } from "@/components/patronage/ConversionFunnel";
import type { ConversionFunnelData } from "@/lib/hooks/usePatronageAnalytics";

const SAMPLE: ConversionFunnelData = {
  post_click: 2000,
  sponsor_start: 400,
  sponsor_success: 280,
  active_30d: 220,
};

const LABELS = {
  title: "Conversion Funnel",
  postClick: "Post click",
  sponsorStart: "Sponsor started",
  sponsorSuccess: "Sponsor success",
  active30d: "Active 30d",
  conversionRate: "Overall",
  noData: "No funnel data yet.",
  mockBadge: "sample",
};

describe("ConversionFunnel", () => {
  it("renders chart title", () => {
    render(<ConversionFunnel data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Conversion Funnel")).toBeTruthy();
  });

  it("renders all 4 step labels", () => {
    render(<ConversionFunnel data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Post click")).toBeTruthy();
    expect(screen.getByText("Sponsor started")).toBeTruthy();
    expect(screen.getByText("Sponsor success")).toBeTruthy();
    expect(screen.getByText("Active 30d")).toBeTruthy();
  });

  it("renders overall conversion rate", () => {
    render(<ConversionFunnel data={SAMPLE} labels={LABELS} />);
    // 220/2000 = 11.0%
    expect(screen.getByText(/11\.0%/)).toBeTruthy();
  });

  it("renders SVG element", () => {
    const { container } = render(<ConversionFunnel data={SAMPLE} labels={LABELS} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("renders no-data state when data is null and isMock=false", () => {
    render(<ConversionFunnel data={null} isMock={false} labels={LABELS} />);
    expect(screen.getByText("No funnel data yet.")).toBeTruthy();
  });

  it("renders loading skeleton when loading=true", () => {
    const { container } = render(<ConversionFunnel data={null} loading={true} labels={LABELS} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });
});
