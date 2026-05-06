/**
 * CouponRedemptionStats.test.tsx — B'-5 Patronage Analytics
 *
 * Tests donut chart rendering for winback coupon lifecycle metrics.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { CouponRedemptionStats } from "@/components/patronage/CouponRedemptionStats";
import type { CouponRedemptionData } from "@/lib/hooks/usePatronageAnalytics";

const SAMPLE: CouponRedemptionData = {
  issued: 100,
  applied: 60,
  cancel_reverted: 30,
  expired: 40,
};

const LABELS = {
  title: "Coupon Redemption",
  issued: "Issued",
  applied: "Applied",
  cancelReverted: "Cancels reverted",
  expired: "Expired",
  redemptionRate: "Redemption",
  noData: "No coupon data yet.",
  mockBadge: "sample",
};

describe("CouponRedemptionStats", () => {
  it("renders title", () => {
    render(<CouponRedemptionStats data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Coupon Redemption")).toBeTruthy();
  });

  it("renders SVG donut chart", () => {
    const { container } = render(<CouponRedemptionStats data={SAMPLE} labels={LABELS} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("shows issued count in legend", () => {
    render(<CouponRedemptionStats data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Issued:")).toBeTruthy();
    // The issued count 100 appears as a span sibling
    expect(screen.getAllByText("100").length).toBeGreaterThan(0);
  });

  it("shows redemption rate percentage in SVG", () => {
    const { container } = render(<CouponRedemptionStats data={SAMPLE} labels={LABELS} />);
    // 60% of 100 = 60%
    const texts = Array.from(container.querySelectorAll("text")).map((el) => el.textContent);
    expect(texts.some((t) => t?.includes("60%"))).toBe(true);
  });

  it("renders no-data state when data is null and isMock=false", () => {
    render(<CouponRedemptionStats data={null} isMock={false} labels={LABELS} />);
    expect(screen.getByText("No coupon data yet.")).toBeTruthy();
  });

  it("renders loading skeleton when loading=true", () => {
    const { container } = render(<CouponRedemptionStats data={null} loading={true} labels={LABELS} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });
});
