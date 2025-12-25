"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { DoodlePhase } from "./MagicCanvasBackground";

const STICKERS = [
  { bg: "bg-[#BFA2FF]", ring: "ring-[#5C3DDE]" },
  { bg: "bg-[#9EE7B2]", ring: "ring-[#1C8B43]" },
  { bg: "bg-[#9DD8FF]", ring: "ring-[#1D6FE2]" },
  { bg: "bg-[#FFB3C7]", ring: "ring-[#E72D6A]" },
];

function SurfaceTexture() {
  const patternId = React.useId();
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.25]"
    >
      <defs>
        <pattern
          id={patternId}
          width="18"
          height="16"
          patternUnits="userSpaceOnUse"
        >
          <circle cx="4" cy="4" r="1.15" fill="rgba(0,0,0,0.22)" />
          <circle cx="13" cy="12" r="1.15" fill="rgba(0,0,0,0.22)" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${patternId})`} />
    </svg>
  );
}

function Stylus() {
  return (
    <svg width="54" height="280" viewBox="0 0 54 280" fill="none" aria-hidden>
      <path
        d="M27 10c8 0 14 6 14 14v190c0 12-6 24-14 24s-14-12-14-24V24c0-8 6-14 14-14z"
        fill="rgba(255,255,255,0.92)"
      />
      <path
        d="M27 10c8 0 14 6 14 14v190c0 12-6 24-14 24s-14-12-14-24V24c0-8 6-14 14-14z"
        stroke="rgba(0,0,0,0.08)"
      />
      <path
        d="M16 44h22"
        stroke="rgba(0,0,0,0.08)"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <path
        d="M19 246c2.7 5.4 9 12 8 18-.8 4.7-4.5 6-8 6s-7.2-1.3-8-6c-1-6 5.3-12.6 8-18z"
        fill="rgba(0,0,0,0.08)"
      />
    </svg>
  );
}

function ToyStylusAnimator(props: {
  phase?: DoodlePhase;
  reducedMotion: boolean;
}) {
  const { phase, reducedMotion } = props;

  if (reducedMotion) return null;

  const active = Boolean(phase && phase !== "idle");
  const looping = phase === "queued" || phase === "sketch" || phase === "color";
  const anim = React.useMemo(() => {
    if (!looping) {
      return {
        left: "82%",
        top: "62%",
        rotate: 18,
      };
    }
    return {
      left: ["86%", "44%", "70%", "52%", "78%"],
      top: ["56%", "38%", "68%", "54%", "34%"],
      rotate: [18, 6, 24, 10, 22],
    };
  }, [looping]);

  return (
    <AnimatePresence>
      {active ? (
        <motion.div
          key="toy-stylus"
          className="absolute left-0 top-0 z-30"
          initial={{ opacity: 0, scale: 0.96, left: "112%", top: "74%" }}
          animate={{
            opacity: 1,
            scale: 1,
            ...anim,
          }}
          exit={{ opacity: 0, scale: 0.98, left: "118%", top: "70%" }}
          transition={{
            duration: looping ? 1.9 : 0.55,
            ease: "easeInOut",
            repeat: looping ? Infinity : 0,
          }}
          style={{
            width: 52,
            transform: "translate(-50%, -22%)",
            filter: "drop-shadow(0 18px 22px rgba(0,0,0,0.18))",
          }}
        >
          <Stylus />
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export default function BoardStage(props: {
  imageUrl?: string;
  caption?: string;
  className?: string;
  overlay?: React.ReactNode;
  phase?: DoodlePhase;
  reducedMotion?: boolean;
}) {
  const { imageUrl, caption, className, overlay, phase, reducedMotion = false } =
    props;
  const drawingActive = Boolean(phase && phase !== "idle");

  return (
    <div className={cn("relative w-full", className)}>
      <div className="toy-board-frame">
        <div className="grid grid-cols-[56px_minmax(0,1fr)_56px] gap-3 sm:grid-cols-[72px_minmax(0,1fr)_72px] sm:gap-4">
          <div className="flex flex-col items-center justify-center gap-3 sm:gap-4">
            {STICKERS.map((s, idx) => (
              <button
                // biome-ignore lint/suspicious/noArrayIndexKey: decorative, stable order
                key={idx}
                type="button"
                className={cn(
                  "toy-board-sticker",
                  s.bg,
                  "ring-2 ring-offset-2 ring-offset-transparent",
                  s.ring
                )}
                aria-label="Sticker button"
              >
                <span className="toy-board-sticker__shine" aria-hidden />
              </button>
            ))}
          </div>

          <div className="toy-board-bezel">
            <div className="relative overflow-hidden toy-board-screen">
              <SurfaceTexture />
              <div className="pointer-events-none absolute inset-0 doodle-board-grid opacity-20" />

              <div className="relative flex min-h-[50vh] items-center justify-center p-4 sm:min-h-[58vh] sm:p-6">
                <AnimatePresence mode="wait">
                  {imageUrl ? (
                    <motion.div
                      key={imageUrl}
                      className="relative w-full max-w-[min(720px,94%)]"
                      initial={{ opacity: 0, y: 10, rotate: -0.6, scale: 0.985 }}
                      animate={{ opacity: 1, y: 0, rotate: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.98 }}
                      transition={{ duration: 0.32, ease: "easeOut" }}
                    >
                      <div className="rounded-[22px] border border-black/10 bg-white/55 p-2 shadow-[0_18px_45px_rgba(32,16,8,0.16)] backdrop-blur-sm">
                        <img
                          src={imageUrl}
                          alt={caption ?? "doodle"}
                          className="max-h-[64vh] w-full rounded-[16px] object-contain"
                        />
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="empty"
                      className="max-w-[58ch] text-center"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 8 }}
                      transition={{ duration: 0.25 }}
                    >
                      <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/70 px-4 py-2 text-sm text-foreground shadow-sm backdrop-blur-sm">
                        <span className="inline-block h-2 w-2 rounded-full bg-[#F97316]" />
                        Say it out loud or type a prompt to start doodling.
                      </div>
                      <p className="mt-4 text-balance text-muted-foreground text-sm">
                        Your latest creation shows up here—like a magnetic doodle board.
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="pointer-events-none absolute inset-0">
                {overlay}
                <ToyStylusAnimator phase={phase} reducedMotion={reducedMotion} />
              </div>
            </div>
          </div>

          <div className="toy-board-pen-slot">
            <div className="toy-board-pen-slot__well">
              <div className="toy-board-pen-slot__cord" aria-hidden />
              <div
                className={cn(
                  "toy-board-pen-slot__stylus transition-opacity duration-200",
                  drawingActive ? "opacity-0" : "opacity-100"
                )}
              >
                <Stylus />
              </div>
            </div>
          </div>
        </div>

        <div className="toy-board-bottom">
          <div className="toy-board-bottom__rail" aria-hidden />
          <div className="toy-board-bottom__knob" aria-hidden />
        </div>
      </div>
    </div>
  );
}
