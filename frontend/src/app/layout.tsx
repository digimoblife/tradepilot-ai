import type { Metadata } from "next";

import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Header } from "@/components/header";

export const metadata: Metadata = {
  title: "TradePilot AI",
  description:
    "AI trading workspace for following one trade from initial analysis to closing review.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "512x512" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <Header />
          <main className="flex flex-1 flex-col">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
