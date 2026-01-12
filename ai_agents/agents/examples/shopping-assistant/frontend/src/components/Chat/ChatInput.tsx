"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { rtmManager } from "@/manager/rtm";
import { useAppSelector } from "@/store/hooks";

export function ChatInput() {
  const [message, setMessage] = useState("");
  const { roomConnected } = useAppSelector((state) => state.global);

  const handleSend = useCallback(async () => {
    if (!message.trim() || !roomConnected) return;

    try {
      await rtmManager.sendText(message.trim());
      setMessage("");
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  }, [message, roomConnected]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-center gap-3 p-4 border-t border-gray-100">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={
          roomConnected
            ? "Type a message or speak..."
            : "Connect to start chatting"
        }
        disabled={!roomConnected}
        className="flex-1 px-4 py-3 bg-gray-50 rounded-xl border-0 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 placeholder:text-gray-400"
      />
      <button
        onClick={handleSend}
        disabled={!message.trim() || !roomConnected}
        className="flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Send className="w-5 h-5" />
      </button>
    </div>
  );
}
