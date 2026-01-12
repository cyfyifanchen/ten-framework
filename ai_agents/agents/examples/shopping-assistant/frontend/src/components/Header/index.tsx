"use client";

import { ShoppingBag, Wifi, WifiOff } from "lucide-react";
import { useAppSelector } from "@/store/hooks";

export function Header() {
  const { roomConnected, options } = useAppSelector((state) => state.global);

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-100">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
          <ShoppingBag className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Shopping Assistant
          </h1>
          <p className="text-xs text-gray-500">Powered by TEN Framework</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {roomConnected ? (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-600 rounded-full text-sm">
            <Wifi className="w-4 h-4" />
            <span>Connected</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 text-gray-500 rounded-full text-sm">
            <WifiOff className="w-4 h-4" />
            <span>Disconnected</span>
          </div>
        )}
      </div>
    </header>
  );
}
