import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Typography,
  Button,
  Box,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  InputBase,
} from "@mui/material";
import { DataGrid, useGridApiContext } from "@mui/x-data-grid";
import { useTheme } from "@mui/material/styles";
import api from "../services/api";
import { getGridStyles, getMenuStyles } from "../constants/gridStyles";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import SearchIcon from "@mui/icons-material/Search";
import { IconButton } from "@mui/material";

function Campaigns({ startDate, endDate }) {
  const [campaigns, setCampaigns] = useState([]);
  const [openOptimize, setOpenOptimize] = useState(false);
  const [optimizationRows, setOptimizationRows] = useState([]);
  const [optimizationMessage, setOptimizationMessage] = useState("");
  const [optimizationError, setOptimizationError] = useState(null);
  const [loadingOptimize, setLoadingOptimize] = useState(false);
  const [selectedCampaignName, setSelectedCampaignName] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";

  useEffect(() => {
    api.get("/campaigns")
      .then(res => setCampaigns(res.data))
      .catch(err => console.error(err));
  }, []);

  // ── Client-side filtering ──────────────────────────────────────────────────
  const filteredCampaigns = campaigns.filter(c =>
    c.name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // ── Shared DataGrid sx ──────────────────────────────────────────────────
  const gridSx = getGridStyles(dark);

  // ── Columns ──────────────────────────────────────────────────────────────
  const columns = [
    {
      field: "name",
      headerName: "Campaign Name",
      flex: 1,
      renderCell: (p) => (
        <Typography sx={{ fontSize: 13.5, fontWeight: 500, color: "text.primary" }}>
          {p.value}
        </Typography>
      ),
    },
    {
      field: "budget",
      headerName: "Budget",
      flex: 0.5,
      renderCell: (p) => (
        <Typography sx={{ fontSize: 13.5, fontWeight: 600, color: dark ? "#94a3b8" : "#64748b" }}>
          ${p.value}
        </Typography>
      ),
    },
    {
      field: "startDate",
      headerName: "Start Date",
      flex: 0.6,
      renderCell: (p) => (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{p.value}</Typography>
      ),
    },
    {
      field: "state",
      headerName: "Status",
      flex: 0.55,
      renderCell: (p) => (
        <Chip
          label={p.value}
          size="small"
          sx={{
            height: 28,
            fontSize: "11.5px",
            fontWeight: 600,
            borderRadius: "999px",
            px: "4px",
            background:
              p.value === "ENABLED"
                ? dark ? "rgba(34,197,94,0.12)" : "rgba(34,197,94,0.1)"
                : dark ? "rgba(239,68,68,0.12)" : "rgba(239,68,68,0.08)",
            color:
              p.value === "ENABLED" ? "#22c55e" : "#ef4444",
          }}
        />
      ),
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1.3,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {/* View Targets */}
          <Button
            variant="contained"
            size="small"
            sx={{
              height: 32,
              px: "14px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "10px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              boxShadow: "none",
              "&:hover": {
                background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
                boxShadow: "0 4px 12px rgba(99,102,241,0.4)",
              },
            }}
            onClick={() => navigate(`/campaign/${p.row.campaignId}`)}
          >
            View Targets
          </Button>

          {/* Optimize */}
          <Button
            variant="contained"
            size="small"
            disabled={loadingOptimize}
            sx={{
              height: 32,
              px: "14px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "10px",
              background: dark ? "rgba(255,255,255,0.07)" : "#EEF2FF",
              color: dark ? "#f1f5f9" : "#4F46E5",
              boxShadow: "none",
              border: dark ? "1px solid rgba(255,255,255,0.1)" : "1px solid #C7D2FE",
              "&:hover": {
                background: dark ? "rgba(255,255,255,0.12)" : "#E0E7FF",
                boxShadow: "none",
              },
              "&:disabled": { opacity: 0.5 },
            }}
            onClick={async () => {
              if (loadingOptimize) return;
              setSelectedCampaignName(p.row.name);
              setOpenOptimize(true);
              setLoadingOptimize(true);
              setOptimizationRows([]);
              setOptimizationMessage("");
              setOptimizationError(null);
              try {
                const res = await api.post(`/campaign/${p.row.campaignId}/optimize`, null, {
                  params: { start_date: startDate, end_date: endDate }
                });
                console.log("Optimization API Response Data:", res.data);
                console.log("Optimization API Success:", {
                  status: res.status,
                  rowsReturned: res.data.optimization?.length || 0,
                  message: res.data.message
                });
                setOptimizationRows(res.data.optimization || []);
                setOptimizationMessage(res.data.message || "");
              } catch (err) {
                console.error("Optimization API Error:", err);
                const backendError = err.response?.data?.message || "Failed to analyze campaign. The server encountered an error.";
                setOptimizationError(backendError);
              } finally {
                setLoadingOptimize(false);
              }
            }}
          >
            {loadingOptimize ? "Optimizing…" : "Optimize"}
          </Button>
        </Box >
      ),
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

  // ── Optimize result columns ───────────────────────────────────────────────
  const optimizeColumns = [
    { field: "entity", headerName: "Keyword / Target", minWidth: 200, flex: 1 },
    { field: "current_bid", headerName: "Current Bid", minWidth: 120, renderCell: p => p.value ? `$${p.value}` : "—" },
    { field: "impressions", headerName: "Impressions", minWidth: 120 },
    { field: "clicks", headerName: "Clicks", minWidth: 100 },
    { field: "acos", headerName: "ACoS", minWidth: 100, renderCell: p => p.value ?? "—" },
    { field: "roas", headerName: "ROAS", minWidth: 100, renderCell: p => p.value ?? "—" },
    {
      field: "decision",
      headerName: "Decision",
      minWidth: 155,
      renderCell: (p) => {
        const colorMap = {
          increase_bid: { bg: "rgba(34,197,94,0.15)", color: "#22c55e" },
          decrease_bid: { bg: "rgba(245,158,11,0.15)", color: "#f59e0b" },
          pause: { bg: "rgba(239,68,68,0.15)", color: "#ef4444" },
          negative_target: { bg: "rgba(239,68,68,0.12)", color: "#ef4444" },
          scale: { bg: "rgba(99,102,241,0.15)", color: "#6366f1" },
          hold: { bg: "rgba(148,163,184,0.15)", color: "#94a3b8" },
        };
        const c = colorMap[p.value] || colorMap.hold;
        return (
          <Chip
            label={p.value?.replace("_", " ")}
            size="small"
            sx={{ background: c.bg, color: c.color, fontWeight: 600, height: 26, fontSize: "11px", borderRadius: "999px" }}
          />
        );
      },
    },
    { field: "suggested_bid", headerName: "Suggested Bid", minWidth: 140, renderCell: p => p.value ? `$${p.value}` : "—" },
    { field: "target_roas", headerName: "Target ROAS", minWidth: 120 },
    { field: "confidence", headerName: "Confidence %", minWidth: 125 },
    {
      field: "reasoning",
      headerName: "AI Reasoning",
      minWidth: 380,
      flex: 1,
      renderCell: (p) => (
        <Box sx={{ whiteSpace: "normal", wordBreak: "break-word", lineHeight: 1.55, py: 1, fontSize: 13 }}>
          {p.value}
        </Box>
      ),
    },
  ];

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography
          variant="h5"
          sx={{ fontWeight: 700, letterSpacing: "-0.3px" }}
        >
          Campaigns
        </Typography>

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            position: "relative",
            background: isSearchOpen ? (dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)") : "transparent",
            borderRadius: "12px",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            border: isSearchOpen ? (dark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)") : "1px solid transparent",
            width: isSearchOpen ? 240 : 40,
            height: 40,
          }}
        >
          <IconButton
            onClick={() => setIsSearchOpen(!isSearchOpen)}
            size="small"
            sx={{
              position: "absolute",
              right: 4,
              color: isSearchOpen ? (dark ? "#6366f1" : "#4F46E5") : "text.secondary",
              transition: "color 0.3s ease"
            }}
          >
            <SearchIcon sx={{ fontSize: 22 }} />
          </IconButton>

          <InputBase
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{
              ml: 1.5,
              flex: 1,
              fontSize: 14,
              opacity: isSearchOpen ? 1 : 0,
              width: isSearchOpen ? "calc(100% - 48px)" : 0,
              transition: "opacity 0.2s ease, width 0.3s ease",
              pointerEvents: isSearchOpen ? "auto" : "none",
            }}
          />
        </Box>
      </Box>

      <Paper
        elevation={0}
        sx={{
          width: "100%",
          height: 640,
          borderRadius: "16px",
          overflow: "hidden",
          background: dark ? "#111827" : "#ffffff",
          border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
          boxShadow: dark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 6px 20px rgba(0,0,0,0.06)",
        }}
      >
        <DataGrid
          rows={filteredCampaigns}
          columns={columns}
          getRowId={(row) => row.campaignId}
          pageSizeOptions={[10]}
          initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
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

      {/* ── AI Optimization Dialog ── */}
      {openOptimize && (
        <Dialog
          open={openOptimize}
          onClose={() => setOpenOptimize(false)}
          maxWidth="xl"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: "16px",
              background: dark ? "#141927" : "#ffffff",
              border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)",
              boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
            },
          }}
        >
          <DialogTitle sx={{ fontWeight: 700, fontSize: 18, pb: 1 }}>
            AI Campaign Optimization
            <Typography component="span" sx={{ fontWeight: 400, color: "text.secondary", ml: 1, fontSize: 15 }}>
              — {selectedCampaignName}
            </Typography>
          </DialogTitle>

          <DialogContent dividers sx={{ overflowX: "auto", p: 0 }}>
            {loadingOptimize ? (
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 400, gap: 2 }}>
                <CircularProgress size={52} thickness={4} sx={{ color: "#6366f1" }} />
                <Typography variant="body1" sx={{ fontWeight: 500 }}>AI is analysing campaign performance…</Typography>
                <Typography variant="caption" color="text.secondary">This may take a few seconds</Typography>
              </Box>
            ) : optimizationError ? (
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, color: "#ef4444" }}>
                  {optimizationError}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Please check your connection and try again.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ minWidth: 1200 }}>
                <DataGrid
                  autoHeight
                  getRowHeight={() => "auto"}
                  rows={optimizationRows.map((row, i) => ({ id: i, ...row, confidence: row.confidence_score }))}
                  columns={optimizeColumns}
                  disableRowSelectionOnClick
                  localeText={{
                    noRowsLabel: optimizationMessage || "No performance data found for this campaign within the selected date range."
                  }}
                  sx={{
                    ...gridSx,
                    "& .MuiDataGrid-cell": {
                      ...gridSx["& .MuiDataGrid-cell"],
                      minHeight: "auto !important",
                      maxHeight: "none !important",
                      alignItems: "flex-start",
                      py: 1,
                    },
                    "& .MuiDataGrid-row": {
                      minHeight: "auto !important",
                      maxHeight: "none !important",
                    },
                  }}
                  componentsProps={{
                    columnMenu: {
                      sx: getMenuStyles(dark)
                    }
                  }}
                />
              </Box>
            )}
          </DialogContent>

          <DialogActions sx={{ px: 3, py: 2 }}>
            <Button
              onClick={() => setOpenOptimize(false)}
              sx={{
                height: 36,
                px: 3,
                borderRadius: "10px",
                fontSize: "13px",
                fontWeight: 500,
                background: dark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)",
                color: "text.primary",
                "&:hover": { background: dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.09)" },
              }}
            >
              Close
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
}

export default Campaigns;
