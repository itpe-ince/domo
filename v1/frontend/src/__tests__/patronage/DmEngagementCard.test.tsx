/**
 * DmEngagementCard.test.tsx — B'-5 Patronage Analytics
 *
 * Tests metric card rendering for DM engagement stats.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { DmEngagementCard } from "@/components/patronage/DmEngagementCard";
import type { DmEngagementData } from "@/lib/hooks/usePatronageAnalytics";

const SAMPLE: DmEngagementData = {
  first_message_rate: 34.5,
  avg_response_minutes: 90,
  total_threads: 150,
};

const LABELS = {
  title: "DM Engagement",
  firstMessageRate: "First-message rate",
  firstMessageHint: "New supporters who messaged",
  avgResponseTime: "Avg response time",
  avgResponseUnit: "Median artist reply",
  totalThreads: "Total threads",
  noData: "No DM data yet.",
  mockBadge: "sample",
};

describe("DmEngagementCard", () => {
  it("renders card title", () => {
    render(<DmEngagementCard data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("DM Engagement")).toBeTruthy();
  });

  it("renders first-message rate", () => {
    render(<DmEngagementCard data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("34.5%")).toBeTruthy();
  });

  it("renders avg response time formatted as hours and minutes", () => {
    render(<DmEngagementCard data={SAMPLE} labels={LABELS} />);
    // 90 minutes = 1h 30m
    expect(screen.getByText("1h 30m")).toBeTruthy();
  });

  it("renders total threads count", () => {
    render(<DmEngagementCard data={SAMPLE} labels={LABELS} />);
    expect(screen.getByText("150")).toBeTruthy();
  });

  it("renders no-data state when data is null and isMock=false", () => {
    render(<DmEngagementCard data={null} isMock={false} labels={LABELS} />);
    expect(screen.getByText("No DM data yet.")).toBeTruthy();
  });

  it("renders mock data when isMock=true and data is null", () => {
    render(<DmEngagementCard data={null} isMock={true} labels={LABELS} />);
    // MOCK_DATA has avg_response_minutes=42 → "42m"
    expect(screen.getByText("42m")).toBeTruthy();
    expect(screen.getByText("sample")).toBeTruthy();
  });

  it("renders loading skeleton when loading=true", () => {
    const { container } = render(<DmEngagementCard data={null} loading={true} labels={LABELS} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders minutes-only format for response times under 60 minutes", () => {
    render(<DmEngagementCard data={{ ...SAMPLE, avg_response_minutes: 42 }} labels={LABELS} />);
    expect(screen.getByText("42m")).toBeTruthy();
  });
});
