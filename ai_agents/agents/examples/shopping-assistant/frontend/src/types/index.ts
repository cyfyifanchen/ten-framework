export type Language = "en-US" | "zh-CN" | "ja-JP" | "ko-KR";
export type VoiceType = "male" | "female";

export interface IOptions {
  channel: string;
  userName: string;
  userId: number;
  appId: string;
  token: string;
}

export enum EMessageType {
  AGENT = "agent",
  USER = "user",
}

export enum EMessageDataType {
  TEXT = "text",
  REASON = "reason",
  IMAGE = "image",
  PRODUCT = "product",
  PRODUCT_LIST = "product_list",
}

export interface IProduct {
  itemId: string;
  title: string;
  price: string;
  currency: string;
  image: string;
  condition?: string;
  seller?: string;
  itemWebUrl?: string;
}

export interface IChatItem {
  userId: number | string;
  userName?: string;
  text: string;
  data_type: EMessageDataType;
  type: EMessageType;
  isFinal?: boolean;
  time: number;
  products?: IProduct[];
}

export enum ERTMTextType {
  TRANSCRIBE = "transcribe",
  TRANSLATE = "translate",
  INPUT_TEXT = "input_text",
  INPUT_IMAGE = "input_image",
  INPUT_AUDIO = "input_audio",
  INPUT_FILE = "input_file",
}

export interface IRTMTextItem {
  is_final: boolean;
  type: ERTMTextType;
  ts: number;
  text: string;
  stream_id: string;
}
