import { configureStore } from "@reduxjs/toolkit";
import gameReducer from "./gameSlice";
import authReducer from "./authSlice";


export const store = configureStore({
  reducer: {
    game: gameReducer,
    auth: authReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
