import { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import {
  Container,
  Typography,
  Grid,
  Paper,
  Box
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useTheme } from "@mui/material/styles";
import VisibilityIcon from "@mui/icons-material/Visibility";
import MouseIcon from "@mui/icons-material/Mouse";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PercentIcon from "@mui/icons-material/Percent";
import PaidIcon from "@mui/icons-material/Paid";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";

import api from "../services/api";

function CampaignDashboard() {
  const { campaignId } = useParams();
  const theme = useTheme();

  const [data, setData] = useState([]);
  const [campaignName, setCampaignName] = useState("");
  const [type, setType] = useState("UNKNOWN");
  const [summary, setSummary] = useState({
    spend: 0,
    impressions: 0,
    clicks: 0,
    orders: 0,
    ctr: 0,
    cpo: 0
  });
  const [trendData, setTrendData] = useState([]);

  // ===============================
  // Generate 14 Day Base Template
  // ===============================
    const generateLast14Days = () => {
      const days = [];
      const start = new Date("2026-02-03");
      const end = new Date("2026-02-16");
    
      const current = new Date(start);
    
      while (current <= end) {
        days.push({
          date: current.toISOString().split("T")[0],
          impressions: 0,
          clicks: 0,
          spend: 0,
          orders: 0
        });
    
        current.setDate(current.getDate() + 1);
      }
      return days;
    };


  // const generateLast14Days = () => {
  //   const days = [];
  //   const today = new Date();

  //   for (let i = 13; i >= 0; i--) {
  //     const d = new Date();
  //     d.setDate(today.getDate() - i);

  //     days.push({
  //       date: d.toISOString().split("T")[0],
  //       impressions: 0,
  //       clicks: 0,
  //       spend: 0,
  //       orders: 0
  //     });
  //   }

  //   return days;
  // };

  // ===============================
  // Normalize Trend Data
  // ===============================
  const normalizedTrendData = useMemo(() => {
    const base = generateLast14Days();

    if (!trendData || trendData.length === 0) {
      return base;
    }

    return base.map(day => {
      const found = trendData.find(d => d.date === day.date);

      return found
        ? {
            ...day,
            impressions: found.impressions || 0,
            clicks: found.clicks || 0,
            spend: found.spend || 0,
            orders: found.orders || 0
          }
        : day;
    });
  }, [trendData]);

  const isAllZero = normalizedTrendData.every(
    d =>
      d.impressions === 0 &&
      d.clicks === 0 &&
      d.spend === 0 &&
      d.orders === 0
  );

  // ===============================
  // Fetch Data
  // ===============================
  useEffect(() => {
    const endDate = "2026-02-16";
    const startDate = "2026-02-03";

    api.get(`/campaign/${campaignId}/dashboard`, {
      params: { start_date: startDate, end_date: endDate }
    })
      .then(res => {
        setCampaignName(res.data.campaign_name);
        setType(res.data.type);
        setData(res.data.data);
        setSummary(res.data.summary || {});
        setTrendData(res.data.trend || []);
      })
      .catch(err => console.error(err));
  }, [campaignId]);

  /* =========================================================
   FUTURE: ENABLE ROLLING LAST 14 DAYS

      useEffect(() => {
        const today = new Date();

        const end = new Date();
        end.setDate(today.getDate() - 1);

        const start = new Date(end);
        start.setDate(end.getDate() - 13);

        const endDate = end.toISOString().split("T")[0];
        const startDate = start.toISOString().split("T")[0];

        api.get(`/campaign/${campaignId}/dashboard`, {
          params: { start_date: startDate, end_date: endDate }
        })
          .then(res => {
            setCampaignName(res.data.campaign_name);
            setType(res.data.type);
            setData(res.data.data);
            setSummary(res.data.summary || {});
            setTrendData(res.data.trend || []);
          })
          .catch(err => console.error(err));

      }, [campaignId]);

  ========================================================= */


  // ===============================
  // KPI Cards
  // ===============================
  const kpis = [
    {
      label: "Spend",
      value: `$${Number(summary?.spend ?? 0).toFixed(2)}`,
      icon: <AttachMoneyIcon />,
      color: "#ed6c02"
    },
    {
      label: "Impressions",
      value: Number(summary?.impressions ?? 0),
      icon: <VisibilityIcon />,
      color: "#1976d2"
    },
    {
      label: "Clicks",
      value: Number(summary?.clicks ?? 0),
      icon: <MouseIcon />,
      color: "#2e7d32"
    },
    {
      label: "Orders",
      value: Number(summary?.orders ?? 0),
      icon: <ShoppingCartIcon />,
      color: "#9c27b0"
    },
    {
      label: "CTR %",
      value: Number(summary?.ctr ?? 0),
      icon: <PercentIcon />,
      color: "#d32f2f"
    },
    {
      label: "Cost / Order",
      value: `$${Number(summary?.cpo ?? 0).toFixed(2)}`,
      icon: <PaidIcon />,
      color: "#0288d1"
    }
  ];

  // ===============================
  // Table Columns
  // ===============================
  const columns = [
    {
      field: "entityText",
      headerName:
        type === "KEY"
          ? "Keyword"
          : type === "AUTO"
          ? "Auto Target"
          : type === "PROD"
          ? "Product Target"
          : "Entity",
      flex: 1.5
    },
    {
      field: "bid",
      headerName: "Bid ($)",
      flex: 0.7,
      renderCell: (params) =>
        params.value !== null && params.value !== undefined
          ? `$${Number(params.value).toFixed(2)}`
          : "-"
    },
    { field: "impressions", headerName: "Impressions", flex: 0.8 },
    { field: "clicks", headerName: "Clicks", flex: 0.7 },
    {
      field: "ctr_percent",
      headerName: "Click Through %",
      flex: 0.8,
      renderCell: (params) => `${params.value || 0}%`
    },
    {
      field: "ad_spend",
      headerName: "Ad Spend ($)",
      flex: 0.9,
      renderCell: (params) =>
        `$${Number(params.value || 0).toFixed(2)}`
    },
    { field: "purchases", headerName: "Purchases", flex: 0.7 },
    {
      field: "cost_per_order",
      headerName: "Cost per Order",
      flex: 0.9,
      renderCell: (params) =>
        params.value > 0
          ? `$${Number(params.value).toFixed(2)}`
          : "$0.00"
    }
  ];

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        {campaignName}
      </Typography>

      {type && (
        <Typography
          variant="subtitle1"
          gutterBottom
          sx={{ opacity: 0.7, fontWeight: 400 }}
        >
          {type} Campaign – Last 14 Days
        </Typography>
      )}

      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {kpis.map((item, index) => (
          <Grid item xs={12} md={2} key={index}>
            <Paper sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ color: item.color }}>{item.icon}</Box>
                <Typography variant="caption">
                  {item.label}
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight="bold">
                {item.value}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Trend Chart */}
      <Paper sx={{ p: 3, mb: 4, borderRadius: 3, position: "relative" }}>
        <Typography variant="h6" gutterBottom>
          14 Day Campaign Trend
        </Typography>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={normalizedTrendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="impressions" stroke="#1976d2" />
            <Line type="monotone" dataKey="clicks" stroke="#2e7d32" />
            <Line type="monotone" dataKey="spend" stroke="#ed6c02" />
            <Line type="monotone" dataKey="orders" stroke="#9c27b0" />
          </LineChart>
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

      {/* Targets Table */}
      <Paper sx={{ height: 650 }}>
        <DataGrid
          rows={data}
          columns={columns}
          getRowId={(row) => row.entityId}
          pageSizeOptions={[10]}
        />
      </Paper>
    </Container>
  );
}

export default CampaignDashboard;