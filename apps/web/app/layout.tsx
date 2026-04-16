import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "SaaS Copilot",
  description: "Support and RevOps copilot for SaaS teams"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
