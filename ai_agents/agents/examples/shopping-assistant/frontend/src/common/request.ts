import axios from "axios";
import type { Language } from "@/types";
import { genUUID } from "./utils";

interface StartRequestConfig {
  channel: string;
  userId: number;
  graphName: string;
  language: Language;
  voiceType: "male" | "female";
}

interface GenAgoraDataConfig {
  userId: string | number;
  channel: string;
}

export const apiGenAgoraData = async (config: GenAgoraDataConfig) => {
  const url = `/api/token/generate`;
  const { userId, channel } = config;
  const data = {
    request_id: genUUID(),
    uid: userId,
    channel_name: channel,
  };
  let resp: any = await axios.post(url, data);
  resp = resp.data || {};
  return resp;
};

export const apiStartService = async (
  config: StartRequestConfig
): Promise<any> => {
  const url = `/api/agents/start`;
  const { channel, userId, graphName, language, voiceType } = config;
  const data = {
    request_id: genUUID(),
    channel_name: channel,
    user_uid: userId,
    graph_name: graphName,
    language,
    voice_type: voiceType,
  };
  let resp: any = await axios.post(url, data);
  resp = resp.data || {};
  return resp;
};

export const apiStopService = async (channel: string) => {
  const url = `/api/agents/stop`;
  const data = {
    request_id: genUUID(),
    channel_name: channel,
  };
  let resp: any = await axios.post(url, data);
  resp = resp.data || {};
  return resp;
};

export const apiPing = async (channel: string) => {
  const url = `/api/agents/ping`;
  const data = {
    request_id: genUUID(),
    channel_name: channel,
  };
  let resp: any = await axios.post(url, data);
  resp = resp.data || {};
  return resp;
};
