"use client";

import { Bot, User } from "lucide-react";
import { EMessageType, EMessageDataType, type IChatItem } from "@/types";

interface MessageBubbleProps {
  message: IChatItem;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAgent = message.type === EMessageType.AGENT;
  const isReason = message.data_type === EMessageDataType.REASON;

  return (
    <div
      className={`flex gap-3 ${isAgent ? "flex-row" : "flex-row-reverse"}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isAgent ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
        }`}
      >
        {isAgent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      {/* Message content */}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl ${
          isAgent
            ? "bg-white border border-gray-100 text-gray-800"
            : "bg-blue-500 text-white"
        } ${isReason ? "opacity-70 italic text-sm" : ""} ${
          !message.isFinal ? "opacity-70" : ""
        }`}
      >
        {message.data_type === EMessageDataType.IMAGE ? (
          <img
            src={message.text}
            alt="Product"
            className="rounded-lg max-w-full"
          />
        ) : (
          <p className="whitespace-pre-wrap break-words leading-relaxed">
            {message.text}
          </p>
        )}
      </div>
    </div>
  );
}
