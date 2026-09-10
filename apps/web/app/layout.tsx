import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// §8.3's type spec named these three roles but nothing actually loaded a
// real font for them -- packages/ui/src/tokens.css's --font-display/-ui/-mono
// were plain font-family fallback stacks ("Instrument Serif", "Inter
// Variable", "JetBrains Mono", none of which are pre-installed on a
// visitor's machine), so every page silently rendered in the *fallback*
// (Georgia/system-ui/monospace), not the specified faces. next/font
// downloads and self-hosts the real files at build time -- no runtime
// fetch to Google's CDN, so this also respects apps/web/next.config.ts's
// CSP (docs/adr/0023-*.md) without adding an external font-src exception.
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CoolBlock",
  description: "Where should the next 40 trees go?",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
