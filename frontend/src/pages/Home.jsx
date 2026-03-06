import { useEffect, useState } from "react";
import {
  Typography,
  Grid,
  Paper,
  Box,
  IconButton
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import { useContext } from "react";
import { ColorModeContext } from "../App";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import api from "../services/api";
import Campaigns from "./Campaigns";
import KPICard from "../components/KPICard";
import ChartTooltip from "../components/ChartTooltip";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import VisibilityIcon from "@mui/icons-material/Visibility";
import MouseIcon from "@mui/icons-material/Mouse";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PercentIcon from "@mui/icons-material/Percent";
import PaidIcon from "@mui/icons-material/Paid";


//Main Component 
function Home() {
  const [summary, setSummary] = useState({});
  const [chartData, setChartData] = useState([]);
  const theme = useTheme();
  const { toggleColorMode } = useContext(ColorModeContext);
  const dark = theme.palette.mode === "dark";

  useEffect(() => {
    api.get("/dashboard/summary")
      .then(res => setSummary(res.data))
      .catch(err => console.error("Summary fetch error:", err));

    api.get("/dashboard/trend")
      .then(res => {
        if (!res.data || res.data.length === 0) {
          const placeholders = [];
          const today = new Date();
          for (let i = 13; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            placeholders.push({
              date: d.toISOString().split("T")[0],
              impressions: 0,
              clicks: 0,
              spend: 0,
              orders: 0
            });
          }
          setChartData(placeholders);
        } else {
          setChartData(res.data);
        }
      })
      .catch(err => console.error("Trend fetch error:", err));
  }, []);

  const kpis = [
    { label: "Impressions", value: (summary.impressions || 0).toLocaleString(), icon: <VisibilityIcon />, accent: "#6366f1" },
    { label: "Clicks", value: (summary.clicks || 0).toLocaleString(), icon: <MouseIcon />, accent: "#22c55e" },
    { label: "Spend", value: `$${(summary.spend || 0).toFixed(2)}`, icon: <AttachMoneyIcon />, accent: "#f59e0b" },
    { label: "Orders", value: (summary.orders || 0).toLocaleString(), icon: <ShoppingCartIcon />, accent: "#8b5cf6" },
    { label: "Sales", value: `$${(summary.sales || 0).toFixed(2)}`, icon: <PaidIcon />, accent: "#0ea5e9" },
    {
      label: "CTR %",
      value: summary.impressions > 0
        ? `${((summary.clicks / summary.impressions) * 100).toFixed(2)}%`
        : "0%",
      icon: <PercentIcon />,
      accent: "#ef4444",
    },
  ];

  return (
    <Box
      sx={{
        minHeight: "100vh",
        width: "100%",
        p: "24px",
        boxSizing: "border-box",
        backgroundColor: "background.default",
        color: "text.primary",
        transition: "background-color 0.3s ease",
      }}
    >
      {/* ── Header ── */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.5px", mb: 0.25 }}>
            Amazon Ads Dashboard
          </Typography>
        </Box>
        <IconButton
          onClick={toggleColorMode}
          size="small"
          sx={{
            background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
            border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)",
            width: 36,
            height: 36,
            "&:hover": { background: dark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)" },
          }}
        >
          {dark ? <LightModeIcon sx={{ fontSize: 18 }} /> : <DarkModeIcon sx={{ fontSize: 18 }} />}
        </IconButton>
      </Box>

      {/* ── KPI Cards ── */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {kpis.map((kpi, i) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={i}>
            <KPICard {...kpi} />
          </Grid>
        ))}
      </Grid>

      {/* 14-Day Trend Chart  */}
      <Paper
        elevation={0}
        sx={{
          p: "28px 28px 24px",
          mb: 3,
          borderRadius: "20px",
          background: dark ? "#182235" : "#ffffff",
          border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
          boxShadow: dark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 6px 24px rgba(0,0,0,0.07)",
        }}
      >
        <Typography variant="h6" sx={{ mb: 0.25 }}>
          14-Day Performance Trend
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 3 }}>
          Impressions · Clicks · Spend · Orders
        </Typography>

        <ResponsiveContainer width="100%" height={290}>
          <AreaChart data={chartData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="gImpressions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gClicks" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gSpend" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gOrders" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke={dark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.045)"} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: dark ? "#4b5e7a" : "#94a3b8" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: dark ? "#4b5e7a" : "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Area type="monotone" dataKey="impressions" stroke="#6366f1" strokeWidth={3} fill="url(#gImpressions)" dot={false} name="Impressions" />
            <Area type="monotone" dataKey="clicks" stroke="#22c55e" strokeWidth={3} fill="url(#gClicks)" dot={false} name="Clicks" />
            <Area type="monotone" dataKey="spend" stroke="#f59e0b" strokeWidth={3} fill="url(#gSpend)" dot={false} name="Spend" />
            <Area type="monotone" dataKey="orders" stroke="#8b5cf6" strokeWidth={3} fill="url(#gOrders)" dot={false} name="Orders" />
          </AreaChart>
        </ResponsiveContainer>
      </Paper>

      {/* ── Campaigns Table ── */}
      <Campaigns />
    </Box>
  );
}

export default Home;
