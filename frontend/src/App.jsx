import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { useState, createContext } from "react";

import { CssBaseline } from "@mui/material";

export const ColorModeContext = createContext();
import { getTheme } from "./theme";
import Home from "./pages/Home";
import Campaigns from "./pages/Campaigns";

import CampaignDashboard from "./pages/CampaignDashboard";

function App() {

  const [mode, setMode] = useState("dark");

  const toggleColorMode = () => {
    setMode(prev => (prev === "dark" ? "light" : "dark"));
  };
  return (
    <ColorModeContext.Provider value={{ toggleColorMode }}>
      <ThemeProvider theme={getTheme(mode)}>
        <CssBaseline />
        <Router>
          <Routes>
            {/* Dashboard */}
            <Route path="/" index element={<Home />} />

            {/* Campaigns */}
            <Route path="campaigns" element={<Campaigns />} />

            {/* Redirect /campaign (with or without trailing slash) to / */}
            <Route path="/campaign" element={<Navigate to="/" replace />} />
            <Route path="/campaign/" element={<Navigate to="/" replace />} />

            {/* Keywords */}
            <Route
              path="/campaign/:campaignId"
              element={<CampaignDashboard />}
            />

            {/* Catch-all: anything else redirects to / */}
            <Route path="*" element={<Navigate to="/" replace />} />

          </Routes>
        </Router>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}


export default App;
