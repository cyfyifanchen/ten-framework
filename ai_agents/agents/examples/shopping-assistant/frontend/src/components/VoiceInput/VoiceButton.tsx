"use client";

import { Mic, MicOff, Loader2 } from "lucide-react";
import { AudioVisualizer } from "./AudioVisualizer";
import type { IMicrophoneAudioTrack } from "agora-rtc-sdk-ng";

interface VoiceButtonProps {
  isConnected: boolean;
  isConnecting: boolean;
  isMicOn: boolean;
  audioTrack?: IMicrophoneAudioTrack;
  onConnect: () => void;
  onDisconnect: () => void;
  onToggleMic: () => void;
}

export function VoiceButton({
  isConnected,
  isConnecting,
  isMicOn,
  audioTrack,
  onConnect,
  onDisconnect,
  onToggleMic,
}: VoiceButtonProps) {
  if (isConnecting) {
    return (
      <button
        disabled
        className="flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 text-gray-400 cursor-not-allowed"
      >
        <Loader2 className="w-6 h-6 animate-spin" />
      </button>
    );
  }

  if (!isConnected) {
    return (
      <button
        onClick={onConnect}
        className="flex items-center justify-center w-14 h-14 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors shadow-lg hover:shadow-xl"
      >
        <Mic className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onToggleMic}
        className={`flex items-center justify-center w-14 h-14 rounded-full transition-colors shadow-lg ${
          isMicOn
            ? "bg-blue-500 hover:bg-blue-600 text-white"
            : "bg-gray-200 hover:bg-gray-300 text-gray-600"
        }`}
      >
        {isMicOn ? (
          <AudioVisualizer audioTrack={audioTrack} isActive={isMicOn} />
        ) : (
          <MicOff className="w-6 h-6" />
        )}
      </button>
      <button
        onClick={onDisconnect}
        className="px-4 py-2 text-sm text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
      >
        Disconnect
      </button>
    </div>
  );
}
