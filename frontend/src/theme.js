import { createTheme } from "@mui/material/styles";

export const getTheme = (mode) =>
  createTheme({
    palette: {
      mode,
      primary: {
        main: "#6366f1",
      },
      secondary: {
        main: "#8b5cf6",
      },
      background: {
        default: mode === "dark" ? "#0f172a" : "#f3f4f6",
        paper: mode === "dark" ? "#1e293b" : "#ffffff",
      },
    },
    shape: {
      borderRadius: 14
    }
  });
