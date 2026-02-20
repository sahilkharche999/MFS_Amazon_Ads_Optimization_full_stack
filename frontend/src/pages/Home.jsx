import { useEffect, useState } from "react";
import {
  Container,
  Typography,
  Grid,
  Paper,
  Box,
  IconButton
} from "@mui/material";
// import { DataGrid } from "@mui/x-data-grid";
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
  ResponsiveContainer
} from "recharts";
import api from "../services/api";
import Campaigns from "./Campaigns";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import VisibilityIcon from "@mui/icons-material/Visibility";
import MouseIcon from "@mui/icons-material/Mouse";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PercentIcon from "@mui/icons-material/Percent";
import PaidIcon from "@mui/icons-material/Paid";


function Home() {
  const [summary, setSummary] = useState({});
  const [chartData, setChartData] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const theme = useTheme();
  const { toggleColorMode } = useContext(ColorModeContext);


  useEffect(() => {
    api.get("/dashboard/summary").then(res => {
      setSummary(res.data);
    });
  
    api.get("/dashboard/trend").then(res => {
      setChartData(res.data);
    });
  
    api.get("/campaigns").then(res => {  
      setCampaigns(res.data);
    //   console.log("Fetched campaigns:", res.data);
    });
  }, []);

  const kpis = [
    {
      label: "Impressions",
      value: summary.impressions || 0,
      icon: <VisibilityIcon />,
      color: "#1976d2"
    },
    {
      label: "Clicks",
      value: summary.clicks || 0,
      icon: <MouseIcon />,
      color: "#2e7d32"
    },
    {
      label: "Spend ($)",
      value: summary.spend?.toFixed(2) || "0.00",
      icon: <AttachMoneyIcon />,
      color: "#ed6c02"
    },
    {
      label: "Orders",
      value: summary.orders || 0,
      icon: <ShoppingCartIcon />,
      color: "#9c27b0"
    },
    {
      label: "Sales ($)",
      value: summary.sales?.toFixed(2) || "0.00",
      icon: <PaidIcon />,
      color: "#0288d1"
    },
    {
      label: "CTR %",
      value:
        summary.impressions > 0
          ? ((summary.clicks / summary.impressions) * 100).toFixed(2)
          : 0,
      icon: <PercentIcon />,
      color: "#d32f2f"
    }
  ];

  const columns = [
    { field: "name", headerName: "Campaign", flex: 1.2 },
    { field: "state", headerName: "Status", flex: 0.6 },
    { field: "budget", headerName: "Budget", flex: 0.6 },
  ];

  return (
    <Box
        sx={{
            height: "100vh",
            width: "100%",
            m: 0,
            p: 2,
            boxSizing: "border-box",
            backgroundColor: "background.default",
            color: "text.primary",
            transition: "all 0.3s ease"
        }}
    >

      <Typography variant="h4" sx={{
            fontWeight: 600,
            letterSpacing: "0.5px",
            // mb: 2
        }}>
        Amazon Ads Dashboard
      </Typography>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <IconButton
            onClick={toggleColorMode}
            sx={{
            backgroundColor: "background.paper",
            color: "text.primary",
            boxShadow: 2
            }}
        >
            {theme.palette.mode === "dark"
            ? <LightModeIcon />
            : <DarkModeIcon />}
        </IconButton>
      </Box>

      {/* KPI Cards */}
      <Box sx={{ px: 2, width: "100%", overflowX: "hidden" }}>
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
                    theme =>
                    theme.palette.mode === "dark"
                        ? "rgba(255,255,255,0.04)"
                        : "rgba(0,0,0,0.03)",
                border: theme =>
                    theme.palette.mode === "dark"
                    ? "1px solid rgba(255,255,255,0.08)"
                    : "1px solid rgba(0,0,0,0.06)",
                transition: "all 0.25s ease",
                "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: theme =>
                    theme.palette.mode === "dark"
                        ? "0px 6px 24px rgba(0,0,0,0.4)"
                        : "0px 6px 20px rgba(0,0,0,0.08)"
                }
                }}
            >
                {/* ICON + LABEL */}
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

                {/* VALUE */}
                <Typography
                variant="h5"
                fontWeight="bold"
                sx={{ mt: 0.5 }}
                >
                {item.value}
                </Typography>
            </Paper>
            </Grid>
        ))}
        </Grid>
        </Box>

      {/* Chart */}
      <Paper sx={{ p: 3, mb: 4, borderRadius: 3 }}>
        <Typography variant="h6" gutterBottom>
          14 Day Performance Trend
        </Typography>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
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

      {/* Campaign Table */}
      <Campaigns />

    </Box>
  );
}

export default Home;
