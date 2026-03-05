import { Paper, Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

function KPICard({ label, value, icon, accent }) {
    const theme = useTheme();
    const dark = theme.palette.mode === "dark";

    return (
        <Paper
            elevation={0}
            sx={{
                p: "20px 24px",
                borderRadius: "16px",
                height: 104,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                background: dark ? "#111827" : "#ffffff",
                border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
                borderTop: dark ? "1px solid rgba(255,255,255,0.06)" : `3px solid ${accent}`,
                boxShadow: dark
                    ? "0 8px 30px rgba(0,0,0,0.4), inset 0 0 0 1px rgba(255,255,255,0.04)"
                    : "0 6px 20px rgba(0,0,0,0.06)",
                transition: "transform 0.2s ease, box-shadow 0.2s ease",
                "&:hover": {
                    transform: "translateY(-3px)",
                    boxShadow: dark
                        ? "0 12px 40px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(255,255,255,0.06)"
                        : "0 10px 30px rgba(0,0,0,0.1)",
                },
            }}
        >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ color: accent, display: "flex", alignItems: "center", "& svg": { fontSize: 16 } }}>
                    {icon}
                </Box>
                <Typography
                    variant="caption"
                    sx={{
                        color: "text.secondary",
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.6px",
                    }}
                >
                    {label}
                </Typography>
            </Box>
            <Typography
                sx={{ fontSize: "32px", fontWeight: 700, lineHeight: 1, color: "text.primary", letterSpacing: "-0.5px" }}
            >
                {value}
            </Typography>
        </Paper>
    );
}

export default KPICard;
