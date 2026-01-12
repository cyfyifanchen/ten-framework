"use client";

import { configureStore } from "@reduxjs/toolkit";
import globalReducer from "./reducers/global";

export const store = configureStore({
  reducer: {
    global: globalReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
