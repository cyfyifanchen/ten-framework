import type { Metadata } from "next";
import { StoreProvider } from "@/store/StoreProvider";
import "./global.css";

export const metadata: Metadata = {
  title: "Shopping Assistant | TEN Framework",
  description: "AI-powered voice shopping assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
