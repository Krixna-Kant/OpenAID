import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenAid Provisioner",
  description:
    "Humanitarian data provisioning agent for the Google Cloud Rapid Agent Hackathon",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
