import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ZeroTax AI — Minimize Your Taxes to Zero, Legally",
    template: "%s | ZeroTax AI",
  },
  description:
    "AI-powered tax optimization platform for business owners. Get personalized IRC-cited strategies, exact dollar savings, and real-time law updates. Built for OBBBA 2025.",
  keywords: [
    "tax optimization",
    "tax strategy",
    "AI tax advisor",
    "LLC S-Corp",
    "QBI deduction",
    "QSBS",
    "bonus depreciation",
    "estate planning",
    "OBBBA 2025",
    "IRC",
  ],
  openGraph: {
    title: "ZeroTax AI — Minimize Your Taxes to Zero, Legally",
    description:
      "AI-powered tax optimization platform. Personalized IRC-cited strategies with exact dollar savings.",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "ZeroTax AI",
    description: "Minimize your taxes to zero, legally. AI-powered tax strategy platform.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: "#050d1a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className="antialiased min-h-screen"
        style={{ backgroundColor: "#050d1a", color: "#f8fafc" }}
      >
        {children}
      </body>
    </html>
  );
}
