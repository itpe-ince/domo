import type { Metadata } from "next";
import { AdminShell } from "@/components/AdminShell";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Domo Lounge Admin",
  description: "Domo Lounge management console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <AdminShell>{children}</AdminShell>
      </body>
    </html>
  );
}
