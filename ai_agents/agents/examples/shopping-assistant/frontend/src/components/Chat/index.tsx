"use client";

import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

export function Chat() {
  return (
    <div className="flex flex-col h-full bg-gray-50/50 rounded-2xl overflow-hidden">
      <MessageList />
      <ChatInput />
    </div>
  );
}
