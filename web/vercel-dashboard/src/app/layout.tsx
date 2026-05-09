import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nattome Daily Evidence Dashboard",
  description: "Private read-only dashboard for cloud-published Daily Evidence Runs."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
