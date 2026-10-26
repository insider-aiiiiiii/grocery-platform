import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/lib/query/provider";

export const metadata: Metadata = {
  title: "DukaanQR - Hyperlocal Grocery Platform",
  description: "Next-generation multi-tenant grocery platform with real-time inventory and instant ordering",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased font-sans bg-slate-50 text-slate-900" suppressHydrationWarning>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
