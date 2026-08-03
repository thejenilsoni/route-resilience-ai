import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RouteShield | Urban Mobility Resilience",
  description: "Occlusion-robust road extraction and graph-theoretic route resilience analysis.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
