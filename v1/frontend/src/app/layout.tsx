import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import { CookieConsent } from "@/components/CookieConsent";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Domo — Art Social Network",
  description: "Global SNS, sponsorship and auction platform for emerging artists",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <AppShell>{children}</AppShell>
        <CookieConsent />
      </body>
    </html>
  );
}
