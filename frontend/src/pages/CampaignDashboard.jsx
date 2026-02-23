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
  const theme = useTheme();

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
  


  useEffect(() => {
    // const today = new Date();
    // const endDate = today.toISOString().split("T")[0];

    // const start = new Date();
    // start.setDate(today.getDate() - 14);
    // const startDate = start.toISOString().split("T")[0];

    
    // Demo period (Fixed 14-day window)
    const endDate = "2026-02-16";
    const startDate = "2026-02-02";

    api.get(`/campaign/${campaignId}/dashboard`, {
      params: { start_date: startDate, end_date: endDate }
    })
    .then(res => {
      setCampaignName(res.data.campaign_name);
      setType(res.data.type);
      setData(res.data.data);
      setSummary(res.data.summary || {});
      setTrendData(res.data.trend || []);

      console.log("Fetched campaign dashboard data:", res.data);
    })
    .catch(err => console.error(err));

  }, [campaignId]);

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
      renderCell: (params) => {
        if (params.value === null || params.value === undefined) {
          return "-";
        }
        return `$${Number(params.value).toFixed(2)}`;
      }
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
        sx={{
          opacity: 0.7,
          fontWeight: 400,
          letterSpacing: 0.3
        }}
      >
        {type} Campaign – Last 14 Days
      </Typography>
    )}


      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {kpis.map((item, index) => (
          <Grid item xs={12} md={2} key={index}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 1,
                height: 90,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                backdropFilter: "blur(8px)",
                background:
                  theme.palette.mode === "dark"
                    ? "rgba(255,255,255,0.04)"
                    : "rgba(0,0,0,0.03)",
                border:
                  theme.palette.mode === "dark"
                    ? "1px solid rgba(255,255,255,0.08)"
                    : "1px solid rgba(0,0,0,0.06)",
                transition: "all 0.25s ease",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow:
                    theme.palette.mode === "dark"
                      ? "0px 6px 24px rgba(0,0,0,0.4)"
                      : "0px 6px 20px rgba(0,0,0,0.08)"
                }
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ color: item.color }}>
                  {item.icon}
                </Box>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ fontWeight: 500 }}
                >
                  {item.label}
                </Typography>
              </Box>

              <Typography variant="h5" fontWeight="bold" sx={{ mt: 0.5 }}>
                {item.value}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

        
      {/* 14 day trend */}
      <Paper sx={{ p: 3, mb: 4, borderRadius: 3 }}>
        <Typography variant="h6" gutterBottom>
          14 Day Campaign Trend
        </Typography>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trendData}>
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
      </Paper>

      {/* Targets report */}
      <Paper sx={{ height: 650, borderRadius: 1 }}>
        <DataGrid
          sx={{
            border: "none",
          
            "& .MuiDataGrid-columnHeaders": {
              background:
                theme =>
                  theme.palette.mode === "dark"
                    ? "rgba(255,255,255,0.03)"
                    : "rgba(0,0,0,0.03)",
              backdropFilter: "blur(6px)",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              fontWeight: 600,
              letterSpacing: "0.4px",
              fontSize: "13px"
            },
          
            "& .MuiDataGrid-cell": {
              borderBottom: "1px solid rgba(255,255,255,0.05)",
              paddingTop: "10px",
              paddingBottom: "10px"
            },

            "& .MuiDataGrid-columnSeparator": {
              opacity: 0.2
            },
          
            "& .MuiDataGrid-row:hover": {
              background:
                theme =>
                  theme.palette.mode === "dark"
                    ? "rgba(255,255,255,0.02)"
                    : "rgba(0,0,0,0.02)"
            }
          }}
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
