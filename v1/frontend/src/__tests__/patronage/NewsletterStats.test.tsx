/**
 * NewsletterStats.test.tsx — B'-5 Patronage Analytics
 *
 * Tests bar chart rendering for newsletter open/click rate per issue.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { NewsletterStats } from "@/components/patronage/NewsletterStats";
import type { NewsletterIssueStats } from "@/lib/hooks/usePatronageAnalytics";

const SAMPLE: NewsletterIssueStats[] = [
  { issue: "#1", sent: 800, opened: 440, clicked: 132, open_rate: 55, click_rate: 16.5 },
  { issue: "#2", sent: 820, opened: 476, clicked: 148, open_rate: 58, click_rate: 18.0 },
];

const LABELS = {
  title: "Newsletter Stats",
  openRate: "Open rate",
  clickRate: "Click rate",
  noData: "No newsletter data yet.",
  mockBadge: "sample",
};

describe("NewsletterStats", () => {
  it("renders chart title", () => {
    render(<NewsletterStats data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Newsletter Stats")).toBeTruthy();
  });

  it("renders legend for open and click rates", () => {
    render(<NewsletterStats data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("Open rate")).toBeTruthy();
    expect(screen.getByText("Click rate")).toBeTruthy();
  });

  it("renders SVG chart", () => {
    const { container } = render(<NewsletterStats data={SAMPLE} labels={LABELS} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("renders issue labels on X axis", () => {
    render(<NewsletterStats data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("#1")).toBeTruthy();
    expect(screen.getByText("#2")).toBeTruthy();
  });

  it("renders no-data state when data is empty and isMock=false", () => {
    render(<NewsletterStats data={[]} isMock={false} labels={LABELS} />);
    expect(screen.getByText("No newsletter data yet.")).toBeTruthy();
  });

  it("uses mock data when isMock=true and data is empty", () => {
    const { container } = render(<NewsletterStats data={[]} isMock={true} labels={LABELS} />);
    // Should render SVG with mock bars
    expect(container.querySelector("svg")).toBeTruthy();
    expect(screen.getByText("sample")).toBeTruthy();
  });
});
