import { useEffect, useState } from "react";
import {
  Typography,
  Grid,
  Paper,
  Box,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import { useContext } from "react";
import { ColorModeContext } from "../App";
import {
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

// MUI Date Pickers
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";


//Main Component 
function Home() {
  // Default to last 14 days
  const todayStr = dayjs().format("YYYY-MM-DD");
  const defaultStart = dayjs().subtract(13, "day").format("YYYY-MM-DD");

  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(todayStr);
  const [summary, setSummary] = useState({});
  const [chartData, setChartData] = useState([]);

  // Dialog State
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [tempStart, setTempStart] = useState(dayjs(startDate));
  const [tempEnd, setTempEnd] = useState(dayjs(endDate));
  const [isRangeInvalid, setIsRangeInvalid] = useState(false);

  const theme = useTheme();
  const { toggleColorMode } = useContext(ColorModeContext);
  const dark = theme.palette.mode === "dark";

  // Calculate day difference for title
  const getDayDiff = () => {
    const start = dayjs(startDate);
    const end = dayjs(endDate);
    return end.diff(start, "day") + 1;
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setIsRangeInvalid(false);
    setTempStart(dayjs(startDate));
    setTempEnd(dayjs(endDate));
  };

  const handleApplyDates = () => {
    if (tempEnd.isBefore(tempStart)) {
      setIsRangeInvalid(true);
      return;
    }
    setIsRangeInvalid(false);
    setStartDate(tempStart.format("YYYY-MM-DD"));
    setEndDate(tempEnd.format("YYYY-MM-DD"));
    setIsDialogOpen(false);
  };

  useEffect(() => {
    if (isRangeInvalid) return;

    const params = { start_date: startDate, end_date: endDate };

    api.get("/dashboard/summary", { params })
      .then(res => setSummary(res.data))
      .catch(err => console.error("Summary fetch error:", err));

    api.get("/dashboard/trend", { params })
      .then(res => {
        const rawData = res.data || [];
        const start = dayjs(startDate);
        const end = dayjs(endDate);
        const fullRange = [];

        // Data map for quick lookup
        const dataMap = {};
        rawData.forEach(item => {
          const dStr = dayjs(item.date).format("YYYY-MM-DD");
          dataMap[dStr] = item;
        });

        // Loop through EVERY day in the selected range
        for (let d = dayjs(start); d.isBefore(end) || d.isSame(end, "day"); d = d.add(1, "day")) {
          const dStr = d.format("YYYY-MM-DD");
          if (dataMap[dStr]) {
            fullRange.push(dataMap[dStr]);
          } else {
            fullRange.push({
              date: dStr,
              impressions: 0,
              clicks: 0,
              spend: 0,
              orders: 0
            });
          }
        }
        setChartData(fullRange);
      })
      .catch(err => console.error("Trend fetch error:", err));
  }, [startDate, endDate, isRangeInvalid]);

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

        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
      </Box>

      {/* ── KPI Cards ── */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {kpis.map((kpi, i) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={i}>
            <KPICard {...kpi} />
          </Grid>
        ))}
      </Grid>

      {/* Trend Chart  */}
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
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ mb: 0.25 }}>
              {getDayDiff()}-Day Performance Trend
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
              Impressions · Clicks · Spend · Orders
            </Typography>
          </Box>

          <Button
            variant="outlined"
            size="small"
            startIcon={<CalendarTodayIcon sx={{ fontSize: "16px !important" }} />}
            onClick={() => setIsDialogOpen(true)}
            sx={{
              textTransform: "none",
              borderRadius: "10px",
              fontWeight: 600,
              px: 2,
              py: 0.75,
              borderColor: dark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)",
              color: "text.primary",
              "&:hover": {
                borderColor: dark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)",
                background: dark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.02)"
              }
            }}
          >
            {startDate} - {endDate}
          </Button>
        </Box>

        {isRangeInvalid ? (
          <Box
            sx={{
              height: 290,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              background: dark ? "rgba(239, 68, 68, 0.05)" : "rgba(239, 68, 68, 0.02)",
              borderRadius: "12px",
              border: `1px dashed ${dark ? "rgba(239, 68, 68, 0.2)" : "rgba(239, 68, 68, 0.3)"}`,
            }}
          >
            <Typography variant="h6" sx={{ color: "#ef4444", fontWeight: 600, mb: 1 }}>
              Invalid Date Range
            </Typography>
            <Typography sx={{ color: "text.secondary", fontSize: 14 }}>
              End date cannot be before start date. Please select a valid range.
            </Typography>
          </Box>
        ) : (
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
        )}
      </Paper>

      {/* Date Range Dialog */}
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <Dialog
          open={isDialogOpen}
          onClose={handleCloseDialog}
          PaperProps={{
            sx: {
              borderRadius: "16px",
              background: dark ? "#1f2937" : "#fff",
              backgroundImage: "none",
              p: 1
            }
          }}
        >
          <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
            Select Custom Range
            {tempEnd.isBefore(tempStart) && (
              <Typography sx={{ color: "#ef4444", fontSize: "12px", fontWeight: 500, mt: 0.5 }}>
                End date cannot be before start date
              </Typography>
            )}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 2, minWidth: "320px" }}>
              <DatePicker
                label="Start Date"
                value={tempStart}
                onChange={(newValue) => setTempStart(newValue)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    sx: {
                      "& .MuiOutlinedInput-root": {
                        borderRadius: "10px",
                        background: dark ? "rgba(255,255,255,0.03)" : "#f9fafb"
                      }
                    }
                  }
                }}
              />
              <DatePicker
                label="End Date"
                value={tempEnd}
                onChange={(newValue) => setTempEnd(newValue)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    sx: {
                      "& .MuiOutlinedInput-root": {
                        borderRadius: "10px",
                        background: dark ? "rgba(255,255,255,0.03)" : "#f9fafb"
                      }
                    }
                  }
                }}
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 2, pt: 1 }}>
            <Button onClick={handleCloseDialog} sx={{ textTransform: "none", fontWeight: 600 }}>Cancel</Button>
            <Button
              onClick={handleApplyDates}
              variant="contained"
              sx={{
                textTransform: "none",
                borderRadius: "10px",
                fontWeight: 600,
                boxShadow: "none",
                px: 3
              }}
            >
              Apply Range
            </Button>
          </DialogActions>
        </Dialog>
      </LocalizationProvider>


      {/* ── Campaigns Table ── */}
      <Campaigns startDate={startDate} endDate={endDate} />
    </Box>
  );
}

export default Home;
