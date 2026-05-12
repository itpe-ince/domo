/**
 * CohortRetentionChart.test.tsx — B'-5 Patronage Analytics
 *
 * Tests SVG line chart rendering with mock data.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { CohortRetentionChart } from "@/components/patronage/CohortRetentionChart";
import type { CohortRetentionData } from "@/lib/hooks/usePatronageAnalytics";

const SAMPLE: CohortRetentionData[] = [
  { week: "W1", d1: 72, d7: 48, d30: 22 },
  { week: "W2", d1: 68, d7: 44, d30: 20 },
  { week: "W3", d1: 70, d7: 46, d30: 21 },
];

const LABELS = {
  title: "Cohort Retention",
  d1: "Day 1",
  d7: "Day 7",
  d30: "Day 30",
  noData: "No retention data yet.",
  mockBadge: "sample",
};

describe("CohortRetentionChart", () => {
  it("renders chart title", () => {
    render(<CohortRetentionChart data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Cohort Retention")).toBeTruthy();
  });

  it("renders legend labels for D1, D7, D30", () => {
    render(<CohortRetentionChart data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Day 1")).toBeTruthy();
    expect(screen.getByText("Day 7")).toBeTruthy();
    expect(screen.getByText("Day 30")).toBeTruthy();
  });

  it("renders SVG chart when data is provided", () => {
    const { container } = render(<CohortRetentionChart data={SAMPLE} labels={LABELS} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute("role")).toBe("img");
  });

  it("renders no-data state when data array is empty and isMock=false", () => {
    render(<CohortRetentionChart data={[]} isMock={false} labels={LABELS} />);
    expect(screen.getByText("No retention data yet.")).toBeTruthy();
  });

  it("renders mock badge when isMock=true", () => {
    render(<CohortRetentionChart data={[]} isMock={true} labels={LABELS} />);
    // isMock with empty data uses MOCK_DATA internally — chart renders, not no-data
    const svg = document.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(screen.getByText("sample")).toBeTruthy();
  });

  it("renders loading skeleton when loading=true", () => {
    const { container } = render(<CohortRetentionChart data={[]} loading={true} labels={LABELS} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
    expect(container.querySelector("svg")).toBeFalsy();
  });
});
