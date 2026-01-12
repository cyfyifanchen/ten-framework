"use client";

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
  type IChatItem,
  type IOptions,
  type IProduct,
  EMessageType,
} from "@/types";

export interface IGlobalState {
  options: IOptions;
  roomConnected: boolean;
  rtmConnected: boolean;
  agentConnected: boolean;
  chatItems: IChatItem[];
  products: IProduct[];
  isMicOn: boolean;
  isConnecting: boolean;
}

const initialState: IGlobalState = {
  options: {
    channel: "",
    userName: "",
    userId: 0,
    appId: "",
    token: "",
  },
  roomConnected: false,
  rtmConnected: false,
  agentConnected: false,
  chatItems: [],
  products: [],
  isMicOn: false,
  isConnecting: false,
};

export const globalSlice = createSlice({
  name: "global",
  initialState,
  reducers: {
    setOptions: (state, action: PayloadAction<Partial<IOptions>>) => {
      state.options = { ...state.options, ...action.payload };
    },
    setRoomConnected: (state, action: PayloadAction<boolean>) => {
      state.roomConnected = action.payload;
    },
    setRtmConnected: (state, action: PayloadAction<boolean>) => {
      state.rtmConnected = action.payload;
    },
    setAgentConnected: (state, action: PayloadAction<boolean>) => {
      state.agentConnected = action.payload;
    },
    setMicOn: (state, action: PayloadAction<boolean>) => {
      state.isMicOn = action.payload;
    },
    setIsConnecting: (state, action: PayloadAction<boolean>) => {
      state.isConnecting = action.payload;
    },
    addChatItem: (state, action: PayloadAction<IChatItem>) => {
      const newItem = action.payload;
      const existingIndex = state.chatItems.findIndex(
        (item) =>
          item.userId === newItem.userId &&
          item.type === newItem.type &&
          !item.isFinal
      );

      if (existingIndex !== -1) {
        // Update existing non-final message
        if (newItem.isFinal) {
          state.chatItems[existingIndex] = newItem;
        } else {
          state.chatItems[existingIndex].text = newItem.text;
          state.chatItems[existingIndex].time = newItem.time;
        }
      } else {
        // Add new message
        state.chatItems.push(newItem);
      }
    },
    clearChatItems: (state) => {
      state.chatItems = [];
    },
    setProducts: (state, action: PayloadAction<IProduct[]>) => {
      state.products = action.payload;
    },
    addProducts: (state, action: PayloadAction<IProduct[]>) => {
      state.products = [...state.products, ...action.payload];
    },
    clearProducts: (state) => {
      state.products = [];
    },
    reset: (state) => {
      Object.assign(state, {
        ...initialState,
        options: state.options,
      });
    },
  },
});

export const {
  setOptions,
  setRoomConnected,
  setRtmConnected,
  setAgentConnected,
  setMicOn,
  setIsConnecting,
  addChatItem,
  clearChatItems,
  setProducts,
  addProducts,
  clearProducts,
  reset,
} = globalSlice.actions;

export default globalSlice.reducer;
