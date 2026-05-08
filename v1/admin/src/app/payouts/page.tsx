import { Suspense } from "react";
import { PayoutsShell } from "@/components/payouts/PayoutsShell";

export default function PayoutsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-admin-muted text-sm">로딩 중...</div>}>
      <PayoutsShell />
    </Suspense>
  );
}
