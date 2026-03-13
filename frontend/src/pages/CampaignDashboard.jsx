import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Typography,
  Grid,
  Paper,
  Box,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from "@mui/material";
import { DataGrid, useGridApiContext } from "@mui/x-data-grid";
import { useTheme } from "@mui/material/styles";
import VisibilityIcon from "@mui/icons-material/Visibility";
import MouseIcon from "@mui/icons-material/Mouse";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PercentIcon from "@mui/icons-material/Percent";
import PaidIcon from "@mui/icons-material/Paid";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";

import api from "../services/api";
import KPICard from "../components/KPICard";
import ChartTooltip from "../components/ChartTooltip";
import { getGridStyles, getMenuStyles } from "../constants/gridStyles";


// Main Component
function CampaignDashboard() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [campaignName, setCampaignName] = useState("");
  const [type, setType] = useState("UNKNOWN");
  const [summary, setSummary] = useState({ spend: 0, impressions: 0, clicks: 0, orders: 0, ctr: 0, cpo: 0 });
  const [trendData, setTrendData] = useState([]);

  // Date State
  const todayStr = dayjs().format("YYYY-MM-DD");
  const defaultStart = dayjs().subtract(13, "day").format("YYYY-MM-DD");
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(todayStr);

  // Dialog State
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [tempStart, setTempStart] = useState(dayjs(startDate));
  const [tempEnd, setTempEnd] = useState(dayjs(endDate));
  const [isRangeInvalid, setIsRangeInvalid] = useState(false);

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

    api.get(`/campaign/${campaignId}/dashboard`, {
      params: { start_date: startDate, end_date: endDate },
    })
      .then(res => {
        setCampaignName(res.data.campaign_name);
        setType(res.data.type);
        setData(res.data.data);
        setSummary(res.data.summary || {});

        // Data map for quick lookup
        const rawTrend = res.data.trend || [];
        const dataMap = {};
        rawTrend.forEach(item => {
          const dStr = dayjs(item.date).format("YYYY-MM-DD");
          dataMap[dStr] = item;
        });

        const fullRange = [];
        const start = dayjs(startDate);
        const end = dayjs(endDate);

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
        setTrendData(fullRange);
      })
      .catch(err => console.error(err));
  }, [campaignId, startDate, endDate, isRangeInvalid]);

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
      minWidth: 320, flex: 1.9,
      renderCell: p => (
        <Typography sx={{ fontSize: 13.5, fontWeight: 500 }}>{p.value}</Typography>
      ),
    },
    {
      field: "bid",
      headerName: "Bid ($)",
      minWidth: 150,
      flex: 0.7,
      renderCell: p =>
        p.value == null ? "—" : (
          <Typography sx={{ fontWeight: 600, color: dark ? "#94a3b8" : "#64748b", fontSize: 13.5 }}>
            ${Number(p.value).toFixed(2)}
          </Typography>
        ),
    },
    { field: "impressions", headerName: "Impressions", minWidth: 190, flex: 0.8 },
    { field: "clicks", headerName: "Clicks", minWidth: 170, flex: 0.65 },
    {
      field: "ctr_percent",
      headerName: "CTR %",
      minWidth: 150,
      flex: 0.75,
      renderCell: p => `${p.value || 0}%`,
    },
    {
      field: "ad_spend",
      headerName: "Ad Spend ($)",
      minWidth: 190,
      flex: 0.9,
      renderCell: p => (
        <Typography sx={{ fontWeight: 600, fontSize: 13.5 }}>
          ${Number(p.value || 0).toFixed(2)}
        </Typography>
      ),
    },
    { field: "purchases", headerName: "Purchases", minWidth: 180, flex: 0.7 },
    {
      field: "cost_per_order",
      headerName: "Cost / Order",
      minWidth: 200,
      flex: 0.9,
      renderCell: p =>
        p.value > 0 ? `$${Number(p.value).toFixed(2)}` : "$0.00",
    },
  ];

  // Custom funnel icon component that triggers the filter panel directly
  const FilterIconComponent = (props) => {
    const apiRef = useGridApiContext();
    return (
      <IconButton
        size="small"
        className="custom-filter-icon"
        onClick={(e) => {
          e.stopPropagation();
          // Open the filter panel specifically for this field
          apiRef.current.showFilterPanel(props.field);
        }}
      >
        <FilterAltIcon />
      </IconButton>
    );
  };

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
            {type} Campaign · {getDayDiff()} Days
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
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ mb: 0.25 }}>{getDayDiff()}-Day Campaign Trend</Typography>
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
              height: 260,
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
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trendData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
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
          components={{
            ColumnHeaderFilterIconButton: FilterIconComponent,
            ColumnMenuFilterItem: () => null,
          }}
          componentsProps={{
            columnMenu: {
              sx: getMenuStyles(dark)
            }
          }}
        />
      </Paper>
    </Box>
  );
}

export default CampaignDashboard;