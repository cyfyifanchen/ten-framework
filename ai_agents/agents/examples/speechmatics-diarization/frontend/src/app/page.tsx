"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type {
  IRemoteAudioTrack,
  IAgoraRTCClient,
  IMicrophoneAudioTrack,
  UID,
} from "agora-rtc-sdk-ng"
import {
  apiGenAgoraData,
  apiStartService,
  apiStopService,
} from "../common/request"
import RollingGallery from "../components/RollingGallery"
import type { GalleryItem } from "../components/RollingGallery"

type ChatItem = {
  id: string
  text: string
  speaker?: string
  isFinal: boolean
  role: "user" | "assistant"
  ts: number
}

type TextChunk = {
  message_id: string
  part_index: number
  total_parts: number
  content: string
}

const DEFAULT_CHANNEL = "ten_diarization"

const SPEAKER_REGEX = /^\[([^\]]+)\]\s*/

const KNOWN_SPEAKERS = ["Elliot", "Trump", "Musk"] as const

const SPEAKER_ACCENTS: Record<string, string> = {
  Elliot: "#38bdf8",
  Trump: "#f472b6",
  Musk: "#facc15",
}

const generateUserId = () => {
  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const array = new Uint32Array(1)
    window.crypto.getRandomValues(array)
    return 100000 + (array[0] % 900000)
  }
  const fallback = Date.now() % 900000
  return 100000 + fallback
}

export default function HomePage() {
  const [mounted, setMounted] = useState(false)
  const [channel, setChannel] = useState<string>(DEFAULT_CHANNEL)
  const [userId, setUserId] = useState<number>(0)
  const [joined, setJoined] = useState<boolean>(false)
  const [items, setItems] = useState<ChatItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<boolean>(false)
  const [micEnabled, setMicEnabled] = useState<boolean>(true)
  const [lastReplySpeaker, setLastReplySpeaker] = useState<string | null>(null)

  const clientRef = useRef<IAgoraRTCClient | null>(null)
  const audioRef = useRef<IMicrophoneAudioTrack | null>(null)
  const remoteTracksRef = useRef<Map<string, IRemoteAudioTrack>>(new Map())
  const cacheRef = useRef<Record<string, TextChunk[]>>({})
  const listEndRef = useRef<HTMLDivElement | null>(null)

  const appendOrUpdateItem = useCallback((incoming: ChatItem) => {
    setItems((prev) => {
      const idx = prev.findIndex((item) => item.id === incoming.id)
      if (idx === -1) {
        return [...prev, incoming].sort((a, b) => a.ts - b.ts)
      }
      const next = [...prev]
      next[idx] = { ...next[idx], ...incoming }
      return next.sort((a, b) => a.ts - b.ts)
    })

    if (incoming.role === "assistant" && incoming.isFinal && incoming.speaker) {
      setLastReplySpeaker(incoming.speaker)
    }
  }, [])

  const recognisedSpeakers = useMemo(() => {
    const names = new Set<string>()
    items.forEach((item) => {
      if (item.speaker) {
        names.add(item.speaker)
      }
    })
    return Array.from(names)
  }, [items])
  const lastSpeakerLines = useMemo(() => {
    const entries = new Map<string, string>()
    items.forEach((item) => {
      if (item.speaker && item.text) {
        entries.set(item.speaker, item.text)
      }
    })
    return entries
  }, [items])

  const gallerySpecs = useMemo(() => {
    return KNOWN_SPEAKERS.map((name) => {
      const recognised = recognisedSpeakers.includes(name)
      const accent = recognised ? SPEAKER_ACCENTS[name] || "#94a3b8" : "#94a3b8"
      const latest = lastSpeakerLines.get(name)
      const status = lastReplySpeaker === name ? ("active" as const) : (recognised ? "idle" : "idle")
      const tagline = lastReplySpeaker === name
        ? "Reply in progress"
        : recognised
          ? "Identified speaker"
          : "Not yet enrolled"
      const detail = recognised
        ? latest || "Listening for next utterance."
        : "Waiting for enrolment phrase."
      const cards: GalleryItem[] = Array.from({ length: 6 }, () => ({
        title: name,
        tagline,
        detail,
        accentColor: accent,
        status,
      }))
      return { name, cards }
    })
  }, [recognisedSpeakers, lastSpeakerLines, lastReplySpeaker])

  const handleStreamMessage = useCallback(
    (stream: ArrayBuffer) => {
      try {
        const ascii = String.fromCharCode(...new Uint8Array(stream))
        const [message_id, partIndexStr, totalPartsStr, content] =
          ascii.split("|")
        const part_index = parseInt(partIndexStr, 10)
        const total_parts =
          totalPartsStr === "???" ? -1 : parseInt(totalPartsStr, 10)
        if (Number.isNaN(part_index) || Number.isNaN(total_parts)) {
          return
        }
        if (total_parts === -1) {
          return
        }

        const chunk: TextChunk = {
          message_id,
          part_index,
          total_parts,
          content,
        }
        const cache = cacheRef.current
        if (!cache[message_id]) {
          cache[message_id] = []
        }
        cache[message_id].push(chunk)

        if (cache[message_id].length === total_parts) {
          const payloadRaw = reconstructMessage(cache[message_id])
          const payload = JSON.parse(base64ToUtf8(payloadRaw))
          const { text, is_final, text_ts, role } = payload
          if (text && String(text).trim().length > 0) {
            const parsed = extractSpeaker(text)
            appendOrUpdateItem({
              id: message_id,
              text: parsed.text,
              speaker: parsed.speaker,
              isFinal: !!is_final,
              role: role === "user" ? "user" : "assistant",
              ts: text_ts || Date.now(),
            })
          }
          delete cache[message_id]
        }
      } catch (e) {
        console.warn("[UI] Failed to parse stream-message", e)
      }
    },
    [appendOrUpdateItem],
  )

  const join = useCallback(async () => {
    if (joined || pending) return
    setPending(true)
    try {
      setError(null)
      const { ok, code, data, msg } = await apiGenAgoraData({
        channel,
        userId,
      })
      if (!ok || !data) {
        throw new Error(`Token error: ${String(msg)} (code=${String(code)})`)
      }

      const { default: AgoraRTC } = await import("agora-rtc-sdk-ng")
      const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" })
      clientRef.current = client

      client.on("stream-message", (_uid: UID, stream: ArrayBuffer) => {
        handleStreamMessage(stream)
      })

      client.on("user-published", async (user, mediaType) => {
        if (mediaType !== "audio") return
        await client.subscribe(user, mediaType)
        const track = user.audioTrack
        if (track) {
          track.play()
          remoteTracksRef.current.set(String(user.uid), track)
        }
      })

      client.on("user-unpublished", (user) => {
        const track = remoteTracksRef.current.get(String(user.uid))
        track?.stop()
        remoteTracksRef.current.delete(String(user.uid))
      })

      client.on("user-left", (user) => {
        const track = remoteTracksRef.current.get(String(user.uid))
        track?.stop()
        remoteTracksRef.current.delete(String(user.uid))
      })

      await client.join(data.appId, channel, data.token, userId)

      const micTrack = await AgoraRTC.createMicrophoneAudioTrack()
      audioRef.current = micTrack
      await client.publish([micTrack])
      setMicEnabled(true)
      setJoined(true)
    } catch (err: any) {
      console.error("[UI] join error", err)
      setError(err?.message || String(err))
      await stop() // ensure state is clean
      throw err
    } finally {
      setPending(false)
    }
  }, [channel, userId, joined, pending, handleStreamMessage])

  const start = useCallback(async () => {
    if (joined || pending) return
    setPending(true)
    try {
      const { ok, msg } = await apiStartService({
        channel,
        userId,
        graphName: "diarization_demo",
      })
      if (!ok) {
        throw new Error(msg || "Failed to start agent")
      }
      await join()
    } catch (err: any) {
      console.error("[UI] start error", err)
      setError(err?.message || "Unable to start session")
      setPending(false)
    } finally {
      setPending(false)
    }
  }, [channel, userId, join, joined, pending])

  const stop = useCallback(async () => {
    setPending(true)
    try {
      cacheRef.current = {}
      setItems([])
      setLastReplySpeaker(null)
      if (audioRef.current) {
        try {
          await audioRef.current.setEnabled(false)
        } catch {}
        audioRef.current.close()
        audioRef.current = null
      }
      remoteTracksRef.current.forEach((track) => track.stop())
      remoteTracksRef.current.clear()
      if (clientRef.current) {
        try {
          await clientRef.current.leave()
        } catch {}
        clientRef.current.removeAllListeners()
        clientRef.current = null
      }
      await apiStopService(channel)
    } catch (err: any) {
      console.warn("[UI] stop error", err)
    } finally {
      setJoined(false)
      setPending(false)
    }
  }, [channel])

  const toggleMic = useCallback(async () => {
    if (!audioRef.current) return
    const next = !micEnabled
    try {
      await audioRef.current.setEnabled(next)
      setMicEnabled(next)
    } catch (err) {
      console.warn("[UI] toggle mic error", err)
    }
  }, [micEnabled])

  useEffect(() => {
    setMounted(true)
    if (!userId) {
      const saved = Number(localStorage.getItem("diarization_uid") || "0")
      const id = saved || generateUserId()
      setUserId(id)
      localStorage.setItem("diarization_uid", String(id))
    }
  }, [userId])

  useEffect(() => {
    if (!joined) return
    listEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [items, joined])

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.close()
      }
      remoteTracksRef.current.forEach((track) => track.stop())
      remoteTracksRef.current.clear()
      if (clientRef.current) {
        clientRef.current.leave().catch(() => {})
        clientRef.current.removeAllListeners()
        clientRef.current = null
      }
    }
  }, [])

  if (!mounted) {
    return null
  }

  return (
    <div
      style={{
        maxWidth: 1080,
        margin: "28px auto",
        padding: 20,
        fontFamily: "Inter, system-ui, Arial",
        color: "#111",
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>
          Speechmatics Diarization Agent
        </h1>
        <p style={{ marginTop: 4, color: "#666", maxWidth: 720, fontSize: 14 }}>
          Launch the diarization graph, stream your microphone, and let the
          agent tailor responses to each enrolled speaker.
        </p>
      </header>

      {error && (
        <div
          style={{
            background: "#fdecea",
            color: "#b11",
            padding: "12px 16px",
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      <section
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 10,
          marginBottom: 14,
        }}
      >
        <div style={{ minWidth: 200, flex: "1 1 200px" }}>
          <label
            style={{ display: "block", fontSize: 11, color: "#666", letterSpacing: 0.1 }}
            htmlFor="channel"
          >
            Channel
          </label>
          <input
            id="channel"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            disabled={joined || pending}
            style={{
              width: "100%",
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #d0d0d0",
              marginTop: 3,
            }}
          />
        </div>
        <div style={{ minWidth: 120 }}>
          <label
            style={{ display: "block", fontSize: 11, color: "#666", letterSpacing: 0.1 }}
            htmlFor="userId"
          >
            User ID
          </label>
          <input
            id="userId"
            value={userId}
            disabled={pending}
            onChange={(e) =>
              setUserId(parseInt(e.target.value || "0", 10) || 0)
            }
            style={{
              width: "100%",
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #d0d0d0",
              marginTop: 3,
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 6,
            minWidth: 220,
          }}
        >
          {!joined ? (
            <button
              onClick={start}
              disabled={!userId || !channel || pending}
              style={primaryButtonStyle(!userId || !channel || pending)}
            >
              {pending ? "Connecting…" : "Start Session"}
            </button>
          ) : (
            <button onClick={stop} style={dangerButtonStyle(pending)}>
              {pending ? "Stopping…" : "Disconnect"}
            </button>
          )}
          <button
            onClick={toggleMic}
            disabled={!joined}
            style={secondaryButtonStyle(!joined)}
          >
            {micEnabled ? "Mute Mic" : "Unmute Mic"}
          </button>
        </div>
      </section>

      <section
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <StatusCard
          title="Status"
          value={joined ? "Connected" : "Idle"}
          tone={joined ? "positive" : "neutral"}
        />
        <StatusCard
          title="Mic"
          value={micEnabled && joined ? "Streaming" : "Muted"}
          tone={micEnabled && joined ? "positive" : "warning"}
        />
        <StatusCard
          title="Recognised Speakers"
          value={
            recognisedSpeakers.length > 0
              ? recognisedSpeakers.join(", ")
              : "Waiting…"
          }
          tone={recognisedSpeakers.length > 0 ? "neutral" : "muted"}
        />
      </section>

      <section
        style={{
          marginBottom: 28,
          borderRadius: 16,
          background:
            "linear-gradient(135deg, rgba(15,15,35,0.92), rgba(6,3,20,0.88))",
          border: "1px solid rgba(120, 119, 198, 0.18)",
          padding: "18px 18px 6px",
          boxShadow: "0 28px 60px rgba(6, 5, 24, 0.35)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 12,
            color: "#f8f9ff",
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
            Speaker Spotlight
          </h2>
          <span style={{ fontSize: 12, letterSpacing: 0.18, opacity: 0.7 }}>
            Drag to explore | auto-rotates when active
          </span>
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 18,
            padding: "6px 0 18px",
          }}
        >
          {gallerySpecs.map((spec) => (
            <div
              key={spec.name}
              style={{
                flex: "1 1 280px",
                maxWidth: 320,
                minWidth: 260,
              }}
            >
              <RollingGallery
                autoplay
                pauseOnHover
                items={spec.cards}
              />
            </div>
          ))}
        </div>
      </section>

      <section
        style={{
          border: "1px solid #e4e4e7",
          borderRadius: 12,
          padding: 16,
          minHeight: 260,
          background: "#fdfdfd",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 12,
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
            Transcript
          </h2>
          <span style={{ fontSize: 12, color: "#666" }}>
            Showing ASR + assistant turns
          </span>
        </div>

        <div style={{ maxHeight: 360, overflowY: "auto", paddingRight: 4 }}>
          {items.length === 0 && (
            <div style={{ color: "#888", fontSize: 14 }}>
              Say hello to start the enrollment flow for Elliot, Trump, and
              Musk.
            </div>
          )}

          {items.map((item) => (
            <TranscriptRow key={item.id} item={item} />
          ))}
          <div ref={listEndRef} />
        </div>
      </section>
    </div>
  )
}

function extractSpeaker(text: string): { speaker?: string; text: string } {
  const match = text.match(SPEAKER_REGEX)
  if (match?.[1]) {
    return { speaker: match[1], text: text.slice(match[0].length) }
  }
  return { text }
}

function TranscriptRow({ item }: { item: ChatItem }) {
  const timestamp = new Date(item.ts || Date.now()).toLocaleTimeString()
  const isAssistant = item.role === "assistant"
  return (
    <div
      style={{
        padding: "8px 0",
        borderBottom: "1px solid #f0f0f0",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "baseline" }}>
        <span style={{ fontSize: 11, color: "#999", minWidth: 80 }}>
          {timestamp}
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: isAssistant ? "#0f172a" : "#1f2937",
            textTransform: "uppercase",
            letterSpacing: 0.5,
          }}
        >
          {item.speaker
            ? `${isAssistant ? "AI →" : "User"} ${item.speaker}`
            : isAssistant
            ? "AI"
            : "User"}
        </span>
        {!item.isFinal && (
          <span style={{ fontSize: 11, color: "#9ca3af" }}>…listening</span>
        )}
      </div>
      <div style={{ marginLeft: 92, color: isAssistant ? "#0f0f0f" : "#374151" }}>
        {item.text}
      </div>
    </div>
  )
}

function StatusCard({
  title,
  value,
  tone = "neutral",
}: {
  title: string
  value: string
  tone?: "positive" | "neutral" | "warning" | "muted"
}) {
  const palette: Record<typeof tone, { bg: string; fg: string }> = {
    positive: { bg: "#ecfdf5", fg: "#047857" },
    neutral: { bg: "#f5f5f5", fg: "#1f2937" },
    warning: { bg: "#fff7ed", fg: "#d97706" },
    muted: { bg: "#f9fafb", fg: "#6b7280" },
  } as const

  const { bg, fg } = palette[tone]
  return (
    <div
      style={{
        flex: "1 1 180px",
        minWidth: 180,
        background: bg,
        color: fg,
        borderRadius: 12,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.35 }}>
        {title.toUpperCase()}
      </span>
      <span style={{ fontSize: 15, fontWeight: 600 }}>{value}</span>
    </div>
  )
}

function primaryButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: "10px 16px",
    borderRadius: 8,
    border: "none",
    background: disabled ? "#9ca3af" : "#111827",
    color: "#fff",
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    minWidth: 140,
  }
}

function dangerButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: "10px 16px",
    borderRadius: 8,
    border: "none",
    background: disabled ? "#f87171" : "#dc2626",
    color: "#fff",
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    minWidth: 140,
  }
}

function secondaryButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: "10px 16px",
    borderRadius: 8,
    border: "1px solid #d1d5db",
    background: disabled ? "#f9fafb" : "#fff",
    color: "#111827",
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    minWidth: 120,
  }
}

function reconstructMessage(chunks: TextChunk[]): string {
  const ordered = [...chunks].sort((a, b) => a.part_index - b.part_index)
  return ordered.map((chunk) => chunk.content).join("")
}

function base64ToUtf8(base64: string): string {
  const binaryString = atob(base64)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return new TextDecoder("utf-8").decode(bytes)
}
