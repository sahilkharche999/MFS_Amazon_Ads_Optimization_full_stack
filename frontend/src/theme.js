import { createTheme } from "@mui/material/styles";

export const getTheme = (mode) =>
  createTheme({
    palette: {
      mode,
      primary: { main: "#6366f1", light: "#818cf8", dark: "#4f46e5" },
      secondary: { main: "#8b5cf6", light: "#a78bfa" },
      success: { main: "#22c55e", light: "#dcfce7" },
      error: { main: "#ef4444", light: "#fee2e2" },
      warning: { main: "#f59e0b", light: "#fef3c7" },
      background: {
        default: mode === "dark" ? "#0b1220" : "#F3F4F6",
        paper: mode === "dark" ? "#111827" : "#ffffff",
        card: mode === "dark" ? "#111827" : "#ffffff",
        table: mode === "dark" ? "#1F2937" : "#F9FAFB",
      },
      text: {
        primary: mode === "dark" ? "#f1f5f9" : "#0f172a",
        secondary: mode === "dark" ? "#94a3b8" : "#64748b",
        disabled: mode === "dark" ? "#475569" : "#cbd5e1",
      },
      divider: mode === "dark" ? "rgba(255,255,255,0.06)" : "#E5E7EB",
    },
    typography: {
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
      h4: { fontWeight: 700, letterSpacing: "-0.5px" },
      h5: { fontWeight: 700 },
      h6: { fontWeight: 600 },
      subtitle1: { fontWeight: 500 },
      caption: { fontWeight: 500, letterSpacing: "0.3px" },
    },
    shape: { borderRadius: 12 },
    components: {
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 500,
            fontSize: "13px",
            borderRadius: "10px",
            height: "32px",
            paddingLeft: "14px",
            paddingRight: "14px",
            boxShadow: "none",
            "&:hover": { boxShadow: "none" },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            height: "28px",
            fontSize: "12px",
            fontWeight: 600,
            borderRadius: "999px",
            paddingLeft: "4px",
            paddingRight: "4px",
          },
        },
      },
      MuiDataGrid: {
        styleOverrides: {
          root: { border: "none", fontSize: "13.5px" },
          columnHeaderTitle: {
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.6px",
          },
          cell: { display: "flex", alignItems: "center" },
          panel: {
            "& .MuiDataGrid-panelContent": {
              padding: "8px",
            },
            "& .MuiDataGrid-columnsPanelRow": {
              padding: "4px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              width: "100%",
              "&:hover": {
                background: mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)",
                borderRadius: "8px",
              },
              "& .MuiFormControlLabel-root": {
                width: "100%",
                margin: 0,
                display: "flex",
                flexDirection: "row-reverse",
                justifyContent: "space-between",
                "& .MuiTypography-root": {
                  fontSize: "13px",
                  fontWeight: 500,
                  flexGrow: 1,
                  textAlign: "left",
                },
              },
              "& .MuiSwitch-root": {
                marginRight: "-8px",
              },
            },
            "& .MuiDataGrid-panelFooter": {
              borderTop: `1px solid ${mode === "dark" ? "rgba(255,255,255,0.06)" : "#E5E7EB"}`,
              padding: "8px 12px",
              "& .MuiButton-root": {
                fontSize: "11px",
                height: "28px",
              }
            }
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: { backgroundImage: "none" },
        },
      },
    },
  });
