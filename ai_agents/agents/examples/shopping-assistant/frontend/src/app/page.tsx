"use client";

import dynamic from "next/dynamic";
import { Header } from "@/components/Header";

// Dynamic imports to avoid SSR issues with Agora SDK
const Chat = dynamic(
  () => import("@/components/Chat").then((mod) => ({ default: mod.Chat })),
  { ssr: false }
);

const Products = dynamic(
  () =>
    import("@/components/Products").then((mod) => ({ default: mod.Products })),
  { ssr: false }
);

const VoiceInput = dynamic(
  () =>
    import("@/components/VoiceInput").then((mod) => ({
      default: mod.VoiceInput,
    })),
  { ssr: false }
);

export default function Home() {
  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 flex overflow-hidden">
        {/* Chat Section */}
        <div className="w-[400px] flex-shrink-0 border-r border-gray-100 flex flex-col bg-white">
          <div className="flex-1 overflow-hidden">
            <Chat />
          </div>
          {/* Voice Input */}
          <div className="p-4 border-t border-gray-100 flex justify-center">
            <VoiceInput />
          </div>
        </div>

        {/* Products Section */}
        <div className="flex-1 overflow-hidden p-4 bg-gray-50">
          <Products />
        </div>
      </main>
    </div>
  );
}
