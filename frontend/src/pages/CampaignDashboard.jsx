import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Typography,
  Grid,
  Paper,
  Box,
  Button,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useTheme } from "@mui/material/styles";
import VisibilityIcon from "@mui/icons-material/Visibility";
import MouseIcon from "@mui/icons-material/Mouse";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PercentIcon from "@mui/icons-material/Percent";
import PaidIcon from "@mui/icons-material/Paid";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

import api from "../services/api";
import KPICard from "../components/KPICard";
import ChartTooltip from "../components/ChartTooltip";
import { getGridStyles } from "../constants/gridStyles";


// Main Component
function CampaignDashboard() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [campaignName, setCampaignName] = useState("");
  const [type, setType] = useState("UNKNOWN");
  const [summary, setSummary] = useState({ spend: 0, impressions: 0, clicks: 0, orders: 0, ctr: 0, cpo: 0 });
  const [trendData, setTrendData] = useState([]);
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";

  const kpis = [
    { label: "Spend", value: `$${Number(summary?.spend ?? 0).toFixed(2)}`, icon: <AttachMoneyIcon />, accent: "#f59e0b" },
    { label: "Impressions", value: Number(summary?.impressions ?? 0).toLocaleString(), icon: <VisibilityIcon />, accent: "#6366f1" },
    { label: "Clicks", value: Number(summary?.clicks ?? 0).toLocaleString(), icon: <MouseIcon />, accent: "#22c55e" },
    { label: "Orders", value: Number(summary?.orders ?? 0).toLocaleString(), icon: <ShoppingCartIcon />, accent: "#8b5cf6" },
    {
      label: "CTR %",
      value: summary.impressions > 0
        ? `${((summary.clicks / summary.impressions) * 100).toFixed(2)}%`
        : "0%",
      icon: <PercentIcon />,
      accent: "#ef4444"
    },
    {
      label: "Cost / Order",
      value: summary.orders > 0
        ? `$${(summary.spend / summary.orders).toFixed(2)}`
        : "$0.00",
      icon: <PaidIcon />,
      accent: "#0ea5e9"
    },
  ];

  useEffect(() => {
    const endDate = "2026-02-16";
    const startDate = "2026-02-02";

    api.get(`/campaign/${campaignId}/dashboard`, {
      params: { start_date: startDate, end_date: endDate },
    })
      .then(res => {
        setCampaignName(res.data.campaign_name);
        setType(res.data.type);
        setData(res.data.data);
        setSummary(res.data.summary || {});

        // If trend data is empty, generate placeholders for visibility
        if (!res.data.trend || res.data.trend.length === 0) {
          const placeholders = [];
          const start = new Date(startDate);
          const end = new Date(endDate);
          for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            placeholders.push({
              date: d.toISOString().split("T")[0],
              impressions: 0,
              clicks: 0,
              spend: 0,
              orders: 0
            });
          }
          setTrendData(placeholders);
        } else {
          setTrendData(res.data.trend);
        }
      })
      .catch(err => console.error(err));
  }, [campaignId]);

  //DataGrid shared sx
  const gridSx = getGridStyles(dark);

  // ── Targets/Keywords columns ────────────────────────────────────────────
  const columns = [
    {
      field: "entityText",
      headerName:
        type === "KEY" ? "Keyword" :
          type === "AUTO" ? "Auto Target" :
            type === "PROD" ? "Product Target" : "Entity",
      flex: 1.5,
      renderCell: p => (
        <Typography sx={{ fontSize: 13.5, fontWeight: 500 }}>{p.value}</Typography>
      ),
    },
    {
      field: "bid",
      headerName: "Bid ($)",
      flex: 0.7,
      renderCell: p =>
        p.value == null ? "—" : (
          <Typography sx={{ fontWeight: 600, color: dark ? "#94a3b8" : "#64748b", fontSize: 13.5 }}>
            ${Number(p.value).toFixed(2)}
          </Typography>
        ),
    },
    { field: "impressions", headerName: "Impressions", flex: 0.8 },
    { field: "clicks", headerName: "Clicks", flex: 0.65 },
    {
      field: "ctr_percent",
      headerName: "CTR %",
      flex: 0.75,
      renderCell: p => `${p.value || 0}%`,
    },
    {
      field: "ad_spend",
      headerName: "Ad Spend ($)",
      flex: 0.9,
      renderCell: p => (
        <Typography sx={{ fontWeight: 600, fontSize: 13.5 }}>
          ${Number(p.value || 0).toFixed(2)}
        </Typography>
      ),
    },
    { field: "purchases", headerName: "Purchases", flex: 0.7 },
    {
      field: "cost_per_order",
      headerName: "Cost / Order",
      flex: 0.9,
      renderCell: p =>
        p.value > 0 ? `$${Number(p.value).toFixed(2)}` : "$0.00",
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", p: "24px", backgroundColor: "background.default", color: "text.primary" }}>
      {/* ── Header ── */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="text"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/")}
          sx={{
            mb: 2,
            color: "text.secondary",
            fontWeight: 600,
            fontSize: "13px",
            "&:hover": {
              background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
              color: "primary.main",
            },
            padding: "4px 8px",
            marginLeft: "-8px",
          }}
        >
          Back to Dashboard
        </Button>
        <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.5px", mb: 0.25 }}>
          {campaignName || "Campaign Dashboard"}
        </Typography>
        {type && (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {type} Campaign · Last 14 Days
          </Typography>
        )}
      </Box>

      {/* ── KPI Cards ── */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {kpis.map((kpi, i) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={i}>
            <KPICard {...kpi} />
          </Grid>
        ))}
      </Grid>

      {/* ── Trend Chart ── */}
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
        <Typography variant="h6" sx={{ mb: 0.25 }}>14-Day Campaign Trend</Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 3 }}>
          Impressions · Clicks · Spend · Orders
        </Typography>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={normalizedTrendData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="cd_gImp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="cd_gClk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="cd_gSpd" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="cd_gOrd" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={dark ? 0.2 : 0.08} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 4" stroke={dark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.045)"} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: dark ? "#4b5e7a" : "#94a3b8" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: dark ? "#4b5e7a" : "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Area type="monotone" dataKey="impressions" stroke="#6366f1" strokeWidth={3} fill="url(#cd_gImp)" dot={false} name="Impressions" />
            <Area type="monotone" dataKey="clicks" stroke="#22c55e" strokeWidth={3} fill="url(#cd_gClk)" dot={false} name="Clicks" />
            <Area type="monotone" dataKey="spend" stroke="#f59e0b" strokeWidth={3} fill="url(#cd_gSpd)" dot={false} name="Spend" />
            <Area type="monotone" dataKey="orders" stroke="#8b5cf6" strokeWidth={3} fill="url(#cd_gOrd)" dot={false} name="Orders" />
          </AreaChart>
        </ResponsiveContainer>

        {isAllZero && (
          <Typography
            variant="body2"
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              color: "text.secondary"
            }}
          >
            No data available for this period
          </Typography>
        )}
      </Paper>

      {/* ── Targets / Keywords Table ── */}
      <Paper
        elevation={0}
        sx={{
          height: 620,
          borderRadius: "16px",
          overflow: "hidden",
          background: dark ? "#111827" : "#ffffff",
          border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
          boxShadow: dark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 6px 20px rgba(0,0,0,0.06)",
        }}
      >
        <DataGrid
          rows={data}
          columns={columns}
          getRowId={row => row.entityId}
          pageSizeOptions={[10]}
          sx={gridSx}
        />
      </Paper>
    </Box>
  );
}

export default CampaignDashboard;