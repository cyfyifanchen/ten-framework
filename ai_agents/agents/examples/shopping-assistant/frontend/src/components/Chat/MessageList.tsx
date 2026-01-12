"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { useAppSelector } from "@/store/hooks";
import { ShoppingBag } from "lucide-react";

export function MessageList() {
  const { chatItems, roomConnected } = useAppSelector((state) => state.global);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatItems]);

  if (!roomConnected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
        <div className="w-20 h-20 rounded-full bg-gray-50 flex items-center justify-center mb-4">
          <ShoppingBag className="w-10 h-10 text-gray-300" />
        </div>
        <p className="text-lg font-medium text-gray-500 mb-2">
          Shopping Assistant
        </p>
        <p className="text-sm text-center max-w-xs">
          Click the microphone button to connect and start shopping with voice
        </p>
      </div>
    );
  }

  if (chatItems.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
        <p className="text-sm">
          Say something like "Search for wireless headphones"
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {chatItems.map((item, index) => (
        <MessageBubble key={`${item.time}-${index}`} message={item} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
