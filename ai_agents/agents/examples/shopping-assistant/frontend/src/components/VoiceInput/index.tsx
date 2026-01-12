"use client";

import { useEffect, useState, useCallback } from "react";
import { VoiceButton } from "./VoiceButton";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setRoomConnected,
  setRtmConnected,
  setAgentConnected,
  setMicOn,
  setIsConnecting,
  setOptions,
  addChatItem,
  reset,
} from "@/store/reducers/global";
import { rtcManager } from "@/manager/rtc/rtc";
import { rtmManager } from "@/manager/rtm";
import { apiStartService, apiStopService, genRandomUserId, genRandomChannel } from "@/common";
import { EMessageType, EMessageDataType, ERTMTextType } from "@/types";
import type { IUserTracks } from "@/manager/rtc/types";

const GRAPH_NAME = "shopping_assistant";

export function VoiceInput() {
  const dispatch = useAppDispatch();
  const { roomConnected, isMicOn, isConnecting, options } = useAppSelector(
    (state) => state.global
  );
  const [audioTrack, setAudioTrack] = useState<IUserTracks["audioTrack"]>();

  const handleConnect = useCallback(async () => {
    dispatch(setIsConnecting(true));

    try {
      const userId = genRandomUserId();
      const channel = genRandomChannel();

      dispatch(setOptions({ userId, channel }));

      // Start agent service
      const startRes = await apiStartService({
        channel,
        userId,
        graphName: GRAPH_NAME,
        language: "en-US",
        voiceType: "female",
      });

      if (startRes.code !== 0) {
        throw new Error("Failed to start agent service");
      }

      // Join RTC
      await rtcManager.join({ channel, userId });
      await rtcManager.createMicrophoneAudioTrack();
      await rtcManager.publish();

      dispatch(
        setOptions({
          appId: rtcManager.appId || "",
          token: rtcManager.token || "",
        })
      );

      // Initialize RTM
      await rtmManager.init({
        channel,
        userId,
        appId: rtcManager.appId || "",
        token: rtcManager.token || "",
      });

      dispatch(setRoomConnected(true));
      dispatch(setRtmConnected(true));
      dispatch(setAgentConnected(true));
      dispatch(setMicOn(true));
    } catch (error) {
      console.error("Connection failed:", error);
      dispatch(reset());
    } finally {
      dispatch(setIsConnecting(false));
    }
  }, [dispatch]);

  const handleDisconnect = useCallback(async () => {
    try {
      await apiStopService(options.channel);
      await rtcManager.destroy();
      await rtmManager.destroy();
    } catch (error) {
      console.error("Disconnect error:", error);
    } finally {
      dispatch(reset());
    }
  }, [dispatch, options.channel]);

  const handleToggleMic = useCallback(async () => {
    const track = rtcManager.localTracks.audioTrack;
    if (track) {
      await track.setEnabled(!isMicOn);
      dispatch(setMicOn(!isMicOn));
    }
  }, [dispatch, isMicOn]);

  useEffect(() => {
    const onLocalTracksChanged = (tracks: IUserTracks) => {
      setAudioTrack(tracks.audioTrack);
    };

    const onTextChanged = (item: any) => {
      dispatch(addChatItem(item));
    };

    rtcManager.on("localTracksChanged", onLocalTracksChanged);
    rtcManager.on("textChanged", onTextChanged);

    rtmManager.on("rtmMessage", (msg) => {
      // Only handle user input messages from RTM
      if (msg.type === ERTMTextType.INPUT_TEXT && msg.stream_id === String(options.userId)) {
        dispatch(
          addChatItem({
            userId: msg.stream_id,
            text: msg.text,
            type: EMessageType.USER,
            data_type: EMessageDataType.TEXT,
            isFinal: msg.is_final,
            time: msg.ts,
          })
        );
      }
    });

    return () => {
      rtcManager.off("localTracksChanged", onLocalTracksChanged);
      rtcManager.off("textChanged", onTextChanged);
    };
  }, [dispatch, options.userId]);

  return (
    <VoiceButton
      isConnected={roomConnected}
      isConnecting={isConnecting}
      isMicOn={isMicOn}
      audioTrack={audioTrack}
      onConnect={handleConnect}
      onDisconnect={handleDisconnect}
      onToggleMic={handleToggleMic}
    />
  );
}
