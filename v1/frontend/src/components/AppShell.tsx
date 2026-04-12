"use client";

import { MobileTabBar } from "./MobileTabBar";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="flex min-h-screen">
        <Sidebar />
        {/* Main column has bottom padding on mobile so content isn't hidden
            behind the fixed MobileTabBar. */}
        <div className="flex-1 min-w-0 pb-16 md:pb-0">{children}</div>
      </div>
      <MobileTabBar />
    </>
  );
}
