"use client";

import React, { useEffect, useState } from "react";

// Force dynamic rendering
export const dynamic = "force-dynamic";

import dynamicImport from "next/dynamic";

// Dynamically import Live2D component to prevent SSR issues
const ClientOnlyLive2D = dynamicImport(
  () => import("@/components/ClientOnlyLive2D"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-white border-b-2"></div>
          <p className="text-white/70">Loading Live2D Model...</p>
        </div>
      </div>
    ),
  }
);

import { apiPing, apiStartService, apiStopService } from "@/lib/request";
import type { AgoraConfig, Live2DModel } from "@/types";

// Use Kei model with MotionSync support
const defaultModel: Live2DModel = {
  id: "kei",
  name: "Kei",
  path: "/models/kei_vowels_pro/kei_vowels_pro.model3.json",
  preview: "/models/kei_vowels_pro/preview.png",
};

export default function Home() {
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedModel, setSelectedModel] = useState<Live2DModel>(defaultModel);
  const [remoteAudioTrack, setRemoteAudioTrack] = useState<any>(null);
  const [agoraService, setAgoraService] = useState<any>(null);
  const [pingInterval, setPingInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Dynamically import Agora service only on client side
    if (typeof window !== "undefined") {
      import("@/services/agora").then((module) => {
        const service = module.agoraService;
        setAgoraService(service);

        // Set up callbacks for Agora service
        service.setOnConnectionStatusChange(handleConnectionChange);
        service.setOnRemoteAudioTrack(handleAudioTrackChange);
      });
    }

    // Cleanup ping interval on unmount
    return () => {
      stopPing();
    };
  }, []);

  const handleConnectionChange = (status: any) => {
    setIsConnected(status.rtc === "connected");
  };

  const handleAudioTrackChange = (track: any) => {
    setRemoteAudioTrack(track);
  };

  const startPing = () => {
    if (pingInterval) {
      stopPing();
    }
    const interval = setInterval(() => {
      apiPing("test-channel");
    }, 3000);
    setPingInterval(interval);
  };

  const stopPing = () => {
    if (pingInterval) {
      clearInterval(pingInterval);
      setPingInterval(null);
    }
  };

  const handleMicToggle = () => {
    if (agoraService) {
      try {
        if (isMuted) {
          agoraService.unmuteMicrophone();
          setIsMuted(false);
        } else {
          agoraService.muteMicrophone();
          setIsMuted(true);
        }
      } catch (error) {
        console.error("Error toggling microphone:", error);
      }
    }
  };

  const handleConnectToggle = async () => {
    if (agoraService) {
      try {
        if (isConnected) {
          setIsConnecting(true);
          // Stop the agent service first
          try {
            await apiStopService("test-channel");
            console.log("Agent stopped");
          } catch (error) {
            console.error("Failed to stop agent:", error);
          }

          await agoraService.disconnect();
          setIsConnected(false);
          stopPing(); // Stop ping when disconnecting
          setIsConnecting(false);
        } else {
          setIsConnecting(true);
          // Fetch Agora credentials from API server using the correct endpoint
          const response = await fetch("/api/token/generate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              request_id: Math.random().toString(36).substring(2, 15),
              uid: Math.floor(Math.random() * 100000),
              channel_name: "test-channel",
            }),
          });

          if (!response.ok) {
            throw new Error(
              `Failed to get Agora credentials: ${response.statusText}`
            );
          }

          const responseData = await response.json();

          // Handle the response structure from agent server
          const credentials = responseData.data || responseData;

          const agoraConfig: AgoraConfig = {
            appId: credentials.appId || credentials.app_id,
            channel: credentials.channel_name,
            token: credentials.token,
            uid: credentials.uid,
          };

          console.log("Agora config:", agoraConfig);
          const success = await agoraService.connect(agoraConfig);
          if (success) {
            setIsConnected(true);

            // Sync microphone state with Agora service
            setIsMuted(agoraService.isMicrophoneMuted());

            // Start the agent service
            try {
              const startResult = await apiStartService({
                channel: agoraConfig.channel,
                userId: agoraConfig.uid || 0,
                graphName: "voice_assistant_live2d",
                language: "en",
                voiceType: "female",
              });

              console.log("Agent started:", startResult);
              startPing(); // Start ping when agent is started
            } catch (error) {
              console.error("Failed to start agent:", error);
            }
          } else {
            console.error("Failed to connect to Agora");
          }
          setIsConnecting(false);
        }
      } catch (error) {
        console.error("Error toggling connection:", error);
        setIsConnecting(false);
      }
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#fff9fd] text-[#2f2d4b]">
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,#ffdff2_0%,transparent_55%),radial-gradient(circle_at_bottom,#d2e8ff_0%,transparent_65%)] opacity-70" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_25%,rgba(255,255,255,0.85),transparent_55%),radial-gradient(circle_at_78%_18%,rgba(255,244,213,0.7),transparent_50%)]" />
      </div>

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {Array.from({ length: 10 }).map((_, idx) => (
          <div
            key={idx}
            className="absolute text-[28px]"
            style={{
              top: `${8 + (idx % 5) * 16}%`,
              left: `${(idx * 11) % 100}%`,
              animation: `float${idx % 3} ${6 + (idx % 4)}s ease-in-out infinite`,
              filter: "drop-shadow(0 8px 16px rgba(255, 188, 218, 0.35))",
            }}
          >
            🌸
          </div>
        ))}
      </div>

      <div className="relative z-10 flex min-h-screen flex-col items-center gap-12 px-4 py-12 md:px-6">
        <header className="max-w-2xl space-y-4 text-center">
          <span className="inline-flex items-center rounded-full bg-white/70 px-4 py-1 font-semibold text-[#ff79a8] text-xs uppercase tracking-[0.25em] shadow-sm">
            Say hello to Kei
          </span>
          <h1 className="font-semibold text-4xl text-[#2f2d4b] tracking-tight md:text-5xl">
            Your charming, clever companion in the cloud
          </h1>
          <p className="text-[#6f6a92] text-base md:text-lg">
            Kei is a friendly guide who lights up every conversation. Connect
            with her for thoughtful answers, gentle encouragement, and a dash of
            anime sparkle whenever you need it.
          </p>
        </header>

        <main className="flex w-full max-w-5xl flex-col items-center gap-10">
          <div className="relative w-full max-w-3xl">
            <div className="-inset-6 absolute rounded-[48px] bg-gradient-to-br from-[#ffe1f1]/70 via-[#d8ecff]/70 to-[#fff6d9]/70 blur-3xl" />
            <div className="relative overflow-hidden rounded-[40px] border border-white/80 bg-white/80 px-6 pt-8 pb-10 shadow-[0_32px_80px_rgba(200,208,255,0.45)] backdrop-blur-xl md:px-10">
              <div className="flex w-full items-center justify-between font-semibold text-[#87a0ff] text-[0.65rem] uppercase tracking-[0.32em]">
                <span>Kei</span>
                <span className="flex items-center gap-2">
                  <span
                    className={`inline-flex h-2.5 w-2.5 rounded-full ${
                      isConnected ? "bg-[#7dd87d]" : "bg-[#ff9bae]"
                    }`}
                  />
                  {isConnected ? "Online" : "Waiting"}
                </span>
              </div>
              <ClientOnlyLive2D
                key={selectedModel.id}
                modelPath={selectedModel.path}
                audioTrack={remoteAudioTrack}
                className="mt-5 h-[34rem] w-full rounded-[32px] border border-white/70 bg-gradient-to-b from-white/60 to-[#f5e7ff]/40 md:h-[46rem]"
              />
              <p className="mt-6 text-center text-[#6f6a92] text-sm">
                “Hi! I’m Kei. Let me know how I can make your day easier.”
              </p>
            </div>
          </div>

          <div className="flex w-full max-w-3xl flex-col items-center gap-5">
            <div className="flex flex-wrap items-center justify-center gap-3 font-medium text-xs">
              <span
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 ${
                  isConnected
                    ? "bg-[#e6f8ff] text-[#236d94]"
                    : "bg-[#ffe8ef] text-[#b34f6a]"
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    isConnected ? "bg-[#38a8d8]" : "bg-[#f0708f]"
                  }`}
                />
                {isConnected ? "Connected to channel" : "Not connected"}
              </span>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 ${
                  isMuted
                    ? "bg-[#ffe8ef] text-[#b34f6a]"
                    : "bg-[#ecfce1] text-[#2f7d3e]"
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    isMuted ? "bg-[#f0708f]" : "bg-[#4cc073]"
                  }`}
                />
                {isMuted ? "Mic muted" : "Mic open"}
              </span>
            </div>

            <div className="flex items-center justify-center gap-6">
              <button
                onClick={handleMicToggle}
                disabled={!isConnected}
                className={`relative flex h-16 w-16 items-center justify-center rounded-2xl border text-xl shadow-lg transition-all duration-200 ${
                  !isConnected
                    ? "cursor-not-allowed border-[#e9e7f7] bg-white text-[#b7b4c9] opacity-60"
                    : isMuted
                      ? "border-[#ffcfe0] bg-[#ffe7f0] text-[#b44f6c] hover:bg-[#ffd9e8]"
                      : "border-[#cde5ff] bg-[#e7f3ff] text-[#2f63a1] hover:bg-[#d8ecff]"
                }`}
              >
                {isMuted ? (
                  <svg
                    className="h-7 w-7"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                    <path
                      d="M3 3l18 18"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeWidth="2"
                    />
                  </svg>
                ) : (
                  <svg
                    className="h-7 w-7"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                )}
              </button>

              <button
                onClick={handleConnectToggle}
                disabled={isConnecting}
                className={`relative flex h-16 w-48 items-center justify-center gap-3 rounded-2xl border px-6 font-semibold text-base shadow-lg transition-all duration-200 ${
                  isConnecting
                    ? "cursor-progress border-[#cde5ff] bg-[#e7f3ff] text-[#5a6a96]"
                    : isConnected
                      ? "border-[#ffcfe0] bg-[#ffe6f3] text-[#b44f6c] hover:bg-[#ffd9eb]"
                      : "border-[#cbeec4] bg-[#e7f8df] text-[#2f7036] hover:bg-[#def6d2]"
                }`}
              >
                {isConnecting ? (
                  <>
                    <svg
                      className="h-5 w-5 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Calling Kei...
                  </>
                ) : isConnected ? (
                  <>
                    <svg
                      className="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <rect x="6" y="6" width="12" height="12" rx="2" />
                    </svg>
                    End session
                  </>
                ) : (
                  <>
                    <svg
                      className="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M8 5v14l11-7z" />
                    </svg>
                    Connect with Kei
                  </>
                )}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
