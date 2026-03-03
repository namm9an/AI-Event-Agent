import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Event Agent",
  description: "Nemotron-powered event and speaker intelligence"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="app-shell">{children}</body>
    </html>
  );
}
