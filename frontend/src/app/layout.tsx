import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ingest-insight-act",
  description: "Multi-tenant marketing ETL, insights, and actions platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <nav className="border-b bg-white px-6 py-3 flex items-center gap-6 text-sm font-medium">
          <span className="font-bold text-indigo-600">ingest-insight-act</span>
          <a href="/sources" className="hover:text-indigo-600">Sources</a>
          <a href="/insights" className="hover:text-indigo-600">Insights</a>
          <a href="/reports" className="hover:text-indigo-600">Reports</a>
          <a href="/campaigns" className="hover:text-indigo-600">Campaigns</a>
          <a href="/harness" className="hover:text-amber-600 text-amber-500 ml-auto">⚙ Harness</a>
        </nav>
        <main className="container mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
