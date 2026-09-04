import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoolBlock",
  description: "Where should the next 40 trees go?",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
