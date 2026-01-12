"use client";

import { useEffect, useRef } from "react";
import type { IMicrophoneAudioTrack } from "agora-rtc-sdk-ng";

interface AudioVisualizerProps {
  audioTrack?: IMicrophoneAudioTrack;
  isActive: boolean;
}

export function AudioVisualizer({ audioTrack, isActive }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const analyzerRef = useRef<AnalyserNode>();

  useEffect(() => {
    if (!audioTrack || !isActive || !canvasRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Get the media stream track and create analyzer
    const mediaStreamTrack = audioTrack.getMediaStreamTrack();
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(
      new MediaStream([mediaStreamTrack])
    );
    const analyzer = audioContext.createAnalyser();
    analyzer.fftSize = 64;
    source.connect(analyzer);
    analyzerRef.current = analyzer;

    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);

      analyzer.getByteFrequencyData(dataArray);

      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      const barCount = 5;
      const barWidth = 4;
      const gap = 3;
      const totalWidth = barCount * barWidth + (barCount - 1) * gap;
      const startX = (width - totalWidth) / 2;

      for (let i = 0; i < barCount; i++) {
        const dataIndex = Math.floor((i / barCount) * bufferLength);
        const value = dataArray[dataIndex];
        const barHeight = Math.max(4, (value / 255) * (height - 8));

        const x = startX + i * (barWidth + gap);
        const y = (height - barHeight) / 2;

        ctx.fillStyle = "#3b82f6";
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      audioContext.close();
    };
  }, [audioTrack, isActive]);

  if (!isActive) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      width={40}
      height={24}
      className="inline-block"
    />
  );
}
