import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import { CookieConsent } from "@/components/CookieConsent";
import { I18nProvider } from "@/i18n";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Domo Lounge — Art Social Network",
  description: "Global SNS, sponsorship and auction platform for emerging artists",
  manifest: "/manifest.json",
  themeColor: "#A8D76E",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Domo Lounge",
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <I18nProvider>
          <AppShell>{children}</AppShell>
          <CookieConsent />
        </I18nProvider>
      </body>
    </html>
  );
}
