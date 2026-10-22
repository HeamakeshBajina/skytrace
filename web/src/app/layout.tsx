import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SKYTRACE | Space Intelligence",
  description:
    "A satellite screening and space situational awareness platform. Preview interface; live analysis integration is in progress.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}