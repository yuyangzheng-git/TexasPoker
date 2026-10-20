import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./store";
import { LobbyPage } from "./pages/LobbyPage";
import { GamePage } from "./pages/GamePage";
import { ClubProvider } from "./components/club/Club";
import "./index.css";

// Guest-only app: every visitor plays straight from the lobby, no accounts.
const App: React.FC = () => (
  <Provider store={store}>
    <ClubProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LobbyPage />} />
          <Route path="/game/:gameId" element={<GamePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ClubProvider>
  </Provider>
);

export default App;
