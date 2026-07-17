import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FactoryPulse AI",
  description: "Supplier Risk Intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <header className="border-b border-gray-800 px-6 py-4 flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-blue-500 flex items-center justify-center text-sm font-bold">F</div>
          <span className="font-semibold tracking-tight text-white">FactoryPulse AI</span>
          <span className="text-gray-500 text-sm ml-1">· Supplier Intelligence</span>
        </header>
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
