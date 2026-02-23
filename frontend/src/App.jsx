import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
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

              {/* Keywords */}
              <Route
              path="/campaign/:campaignId"
              element={<CampaignDashboard />}
            />
          </Routes>
        </Router>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export default App;
