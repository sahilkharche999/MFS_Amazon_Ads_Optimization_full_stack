import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

function ChartTooltip({ active, payload, label }) {
    const theme = useTheme();
    const dark = theme.palette.mode === "dark";

    if (!active || !payload?.length) return null;

    return (
        <Box
            sx={{
                background: dark ? "#1a2236" : "#fff",
                border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid #e2e8f0",
                borderRadius: "10px",
                p: "10px 16px",
                boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
                minWidth: 160,
            }}
        >
            <Typography sx={{ fontSize: 11, color: "text.secondary", mb: 0.5, fontWeight: 600 }}>
                {label}
            </Typography>
            {payload.map((p, i) => (
                <Box key={i} sx={{ display: "flex", justifyContent: "space-between", gap: 3 }}>
                    <Typography sx={{ fontSize: 12, color: p.color, fontWeight: 600 }}>{p.name}</Typography>
                    <Typography sx={{ fontSize: 12, color: "text.primary", fontWeight: 700 }}>
                        {Number(p.value).toLocaleString()}
                    </Typography>
                </Box>
            ))}
        </Box>
    );
}

export default ChartTooltip;
