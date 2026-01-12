"use client";

import AgoraRTC, {
  type IAgoraRTCClient,
  type IMicrophoneAudioTrack,
  type IRemoteAudioTrack,
  type UID,
} from "agora-rtc-sdk-ng";
import { apiGenAgoraData } from "@/common/request";
import {
  EMessageDataType,
  EMessageType,
  type IChatItem,
} from "@/types";
import { AGEventEmitter } from "../events";
import type { IUserTracks, RtcEvents } from "./types";

const TIMEOUT_MS = 5000;

interface TextDataChunk {
  message_id: string;
  part_index: number;
  total_parts: number;
  content: string;
}

export class RtcManager extends AGEventEmitter<RtcEvents> {
  private _joined;
  client: IAgoraRTCClient;
  localTracks: IUserTracks;
  appId: string | null = null;
  token: string | null = null;
  userId: number | null = null;

  constructor() {
    super();
    this._joined = false;
    this.localTracks = {};
    this.client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
    this._listenRtcEvents();
  }

  async join({ channel, userId }: { channel: string; userId: number }) {
    if (!this._joined) {
      const res = await apiGenAgoraData({ channel, userId });
      const { code, data } = res;
      if (code != 0) {
        throw new Error("Failed to get Agora token");
      }
      const { appId, token } = data;
      this.appId = appId;
      this.token = token;
      this.userId = userId;
      await this.client?.join(appId, channel, token, userId);
      this._joined = true;
    }
  }

  async createMicrophoneAudioTrack() {
    try {
      const audioTrack = await AgoraRTC.createMicrophoneAudioTrack();
      this.localTracks.audioTrack = audioTrack;
    } catch (err) {
      console.error("Failed to create audio track", err);
    }
    this.emit("localTracksChanged", this.localTracks);
  }

  async publish() {
    const tracks = [];
    if (this.localTracks.audioTrack) {
      tracks.push(this.localTracks.audioTrack);
    }
    if (tracks.length) {
      await this.client.publish(tracks);
    }
  }

  async destroy() {
    this.localTracks?.audioTrack?.close();
    this.localTracks?.videoTrack?.close();
    if (this._joined) {
      await this.client?.leave();
    }
    this._resetData();
  }

  private _listenRtcEvents() {
    this.client.on("network-quality", (quality) => {
      this.emit("networkQuality", quality);
    });
    this.client.on("user-published", async (user, mediaType) => {
      await this.client.subscribe(user, mediaType);
      if (mediaType === "audio") {
        this._playAudio(user.audioTrack);
      }
      this.emit("remoteUserChanged", {
        userId: user.uid,
        audioTrack: user.audioTrack,
        videoTrack: user.videoTrack,
      });
    });
    this.client.on("user-unpublished", async (user, mediaType) => {
      await this.client.unsubscribe(user, mediaType);
      this.emit("remoteUserChanged", {
        userId: user.uid,
        audioTrack: user.audioTrack,
        videoTrack: user.videoTrack,
      });
    });
    this.client.on("stream-message", (uid: UID, stream: any) => {
      this._parseData(stream);
    });
  }

  private _parseData(data: any): void {
    const ascii = String.fromCharCode(...new Uint8Array(data));
    console.log("[RTC] textstream raw data", ascii);
    this.handleChunk(ascii);
  }

  private messageCache: { [key: string]: TextDataChunk[] } = {};

  handleChunk(formattedChunk: string) {
    try {
      const [message_id, partIndexStr, totalPartsStr, content] =
        formattedChunk.split("|");

      const part_index = parseInt(partIndexStr, 10);
      const total_parts =
        totalPartsStr === "???" ? -1 : parseInt(totalPartsStr, 10);

      if (total_parts === -1) {
        console.warn(
          `Total parts for message ${message_id} unknown, waiting for further parts.`
        );
        return;
      }

      const chunkData: TextDataChunk = {
        message_id,
        part_index,
        total_parts,
        content,
      };

      if (!this.messageCache[message_id]) {
        this.messageCache[message_id] = [];
        setTimeout(() => {
          if (this.messageCache[message_id]?.length !== total_parts) {
            console.warn(`Incomplete message with ID ${message_id} discarded`);
            delete this.messageCache[message_id];
          }
        }, TIMEOUT_MS);
      }

      this.messageCache[message_id].push(chunkData);

      if (this.messageCache[message_id].length === total_parts) {
        const completeMessage = this.reconstructMessage(
          this.messageCache[message_id]
        );
        const { stream_id, is_final, text, text_ts, data_type, role } =
          JSON.parse(this.base64ToUtf8(completeMessage));
        console.log(
          `[RTC] message_id: ${message_id} stream_id: ${stream_id}, text: ${text}, data_type: ${data_type}`
        );
        const isAgent = role === "assistant";
        let textItem: IChatItem = {
          type: isAgent ? EMessageType.AGENT : EMessageType.USER,
          time: text_ts,
          text: text,
          data_type: EMessageDataType.TEXT,
          userId: stream_id,
          isFinal: is_final,
        };

        if (data_type === "raw") {
          const { data, type } = JSON.parse(text);
          if (type === "image_url") {
            textItem = {
              ...textItem,
              data_type: EMessageDataType.IMAGE,
              text: data.image_url,
            };
          } else if (type === "reasoning") {
            textItem = {
              ...textItem,
              data_type: EMessageDataType.REASON,
              text: data.text,
            };
          } else if (type === "action") {
            const { action, data: actionData } = data;
            if (action === "browse_website") {
              console.log("Opening website", actionData.url);
              window.open(actionData.url, "_blank");
              return;
            }
          }
        }

        if (text.trim().length > 0) {
          this.emit("textChanged", textItem);
        }

        delete this.messageCache[message_id];
      }
    } catch (error) {
      console.error("Error processing chunk:", error);
    }
  }

  reconstructMessage(chunks: TextDataChunk[]): string {
    chunks.sort((a, b) => a.part_index - b.part_index);
    return chunks.map((chunk) => chunk.content).join("");
  }

  base64ToUtf8(base64: string): string {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return new TextDecoder("utf-8").decode(bytes);
  }

  _playAudio(
    audioTrack: IMicrophoneAudioTrack | IRemoteAudioTrack | undefined
  ) {
    if (audioTrack && !audioTrack.isPlaying) {
      audioTrack.play();
    }
  }

  private _resetData() {
    this.localTracks = {};
    this._joined = false;
  }
}

export const rtcManager = new RtcManager();
