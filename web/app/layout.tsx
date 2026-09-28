import type { Metadata } from "next";
// Fonts are bundled from npm rather than fetched from Google at build time;
// the Google download intermittently failed and took whole deploys down.
import "@fontsource/archivo-narrow/500.css";
import "@fontsource/archivo-narrow/600.css";
import "@fontsource/archivo-narrow/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Emberline — live wildfire perimeter tracking",
  description:
    "Wildfire perimeters, growth, and spread derived from VIIRS thermal detections every 3 hours.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
