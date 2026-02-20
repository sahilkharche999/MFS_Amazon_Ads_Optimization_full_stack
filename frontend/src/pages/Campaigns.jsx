import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Typography, Button, Box, Paper, Chip, Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import api from "../services/api";

function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [openOptimize, setOpenOptimize] = useState(false);
  const [optimizationRows, setOptimizationRows] = useState([]);
  const [loadingOptimize, setLoadingOptimize] = useState(false);
  const [selectedCampaignName, setSelectedCampaignName] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/campaigns")
      .then(res => setCampaigns(res.data))
      .catch(err => console.error(err));
  }, []);

  const columns = [
    { field: "name", headerName: "Campaign Name", flex: 1 },
    { field: "budget", headerName: "Budget", flex: 0.5 },
    { field: "startDate", headerName: "Start Date", flex: 0.6 },
    {
        field: "state",
        headerName: "Status",
        flex: 0.6,
        renderCell: (params) => (
          <Chip
            label={params.value}
            size="small"
            sx={{
              fontWeight: 500,
              letterSpacing: "0.3px",
              background:
                params.value === "ENABLED"
                  ? "rgba(46, 125, 50, 0.15)"
                  : "rgba(211,47,47,0.15)",
              color:
                params.value === "ENABLED"
                  ? "#4caf50"
                  : "#f44336"
            }}
          />
        )
      },
    {
        field: "actions",
        headerName: "Actions",
        flex: 1.4,
        renderCell: (params) => (
          <Box sx={{ display: "flex", gap: 1 }}>
      
            {/* View Targets Button */}
            <Button
              variant="contained"
              size="small"
              sx={{
                borderRadius: "20px",
                textTransform: "none",
                background: "linear-gradient(45deg, #6366f1, #8b5cf6)",
              }}
              onClick={() =>
                navigate(`/campaign/${params.row.campaignId}`)
              }
            >
              View Targets
            </Button>
      
            {/* Optimize Campaign Button */}
            <Button
              variant="outlined"
              size="small"
              color="secondary"
              disabled={loadingOptimize}
              sx={{
                borderRadius: "20px",
                textTransform: "none"
              }}
              onClick={async () => {
                if (loadingOptimize) return; 
              
                setSelectedCampaignName(params.row.name);
                setOpenOptimize(true);   
                setLoadingOptimize(true);
              
                try {
                  const res = await api.post(
                    `/campaign/${params.row.campaignId}/optimize`
                  );
              
                  setOptimizationRows(res.data.optimization || []);
                } catch (err) {
                  console.error(err);
                } finally {
                  setLoadingOptimize(false);
                }
              }}
            >
              {loadingOptimize ? "Optimizing..." : "Optimize"}
            </Button>
      
          </Box>
        ),
      },
  ];

  return (
    <Box sx={{ width: "100%"}}>
      <Typography
        variant="h4"
        gutterBottom
        sx={{
            fontWeight: 600,
            letterSpacing: "0.5px",
            mb: 2
        }}
        >
        Campaigns
     </Typography>
  
      <Paper
        elevation={3}
        sx={{
            width: "100%",
            height: 650,
            borderRadius: 1,
            overflow: "hidden",   
            position: "relative",
            maxWidth: "100%"
        }}
        >
        <DataGrid
          rows={campaigns}
          columns={columns}
          getRowId={(row) => row.campaignId}
          pageSizeOptions={[10]}
          initialState={{
            pagination: { paginationModel: { pageSize: 10, page: 0 } },
          }}
          sx={{
            border: "none",
            fontSize: "14px",
          
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
          
            "& .MuiDataGrid-columnHeaderTitle": {
              fontWeight: 600
            },
          
            "& .MuiDataGrid-cell": {
              borderBottom: "1px solid rgba(255,255,255,0.05)",
              paddingTop: "10px",
              paddingBottom: "10px"
            },
          
            "& .MuiDataGrid-row:hover": {
              background:
                theme =>
                  theme.palette.mode === "dark"
                    ? "rgba(255,255,255,0.02)"
                    : "rgba(0,0,0,0.02)"
            },
          
            "& .MuiDataGrid-sortIcon": {
              opacity: 0.5
            }
          }}
        />
      </Paper>

      {openOptimize && (
        <Dialog
        open={openOptimize}
        onClose={() => setOpenOptimize(false)}
        maxWidth="xl"
        fullWidth
        >
        <DialogTitle>
            AI Campaign Optimization — {selectedCampaignName}
        </DialogTitle>

        <DialogContent dividers sx={{ overflowX: "auto" }}>

            {loadingOptimize ? (
            <Box
                sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: 400,
                gap: 2
                }}
            >
                <CircularProgress size={60} thickness={4} />
                <Typography variant="body1">
                AI is analyzing campaign performance...
                </Typography>
                <Typography variant="caption" color="text.secondary">
                This may take a few seconds.
                </Typography>
            </Box>
            ) : (
            <Box sx={{ minWidth: 1200 }}>
                <DataGrid
                autoHeight
                getRowHeight={() => "auto"}
                rows={optimizationRows.map((row, index) => ({
                    id: index,
                    entity: row.entity,
                    current_bid: row.current_bid,
                    impressions: row.impressions,
                    clicks: row.clicks,
                    acos: row.acos,
                    roas: row.roas,
                    decision: row.decision,
                    suggested_bid: row.suggested_bid,
                    target_roas: row.target_roas,
                    confidence: row.confidence_score,
                    reasoning: row.reasoning
                }))}
                columns={[
                    {
                    field: "entity",
                    headerName: "Keyword / Target",
                    minWidth: 200
                    },

                    {
                    field: "current_bid",
                    headerName: "Current Bid",
                    minWidth: 130,
                    renderCell: (params) =>
                        params.value ? `$${params.value}` : "-"
                    },

                    {
                    field: "impressions",
                    headerName: "Impressions",
                    minWidth: 130
                    },

                    {
                    field: "clicks",
                    headerName: "Clicks",
                    minWidth: 110
                    },

                    {
                    field: "acos",
                    headerName: "ACoS",
                    minWidth: 110,
                    renderCell: (params) =>
                        params.value !== null && params.value !== undefined
                        ? params.value
                        : "-"
                    },

                    {
                    field: "roas",
                    headerName: "ROAS",
                    minWidth: 110,
                    renderCell: (params) =>
                        params.value !== null && params.value !== undefined
                        ? params.value
                        : "-"
                    },

                    {
                    field: "decision",
                    headerName: "Decision",
                    minWidth: 150,
                    renderCell: (params) => (
                        <Chip
                        label={params.value}
                        color={
                            params.value === "increase_bid"
                            ? "success"
                            : params.value === "decrease_bid"
                            ? "warning"
                            : params.value === "pause"
                            ? "error"
                            : "default"
                        }
                        />
                    )
                    },

                    {
                    field: "suggested_bid",
                    headerName: "Suggested Bid",
                    minWidth: 150,
                    renderCell: (params) =>
                        params.value ? `$${params.value}` : "-"
                    },

                    {
                    field: "target_roas",
                    headerName: "Target ROAS",
                    minWidth: 130
                    },

                    {
                    field: "confidence",
                    headerName: "Confidence %",
                    minWidth: 130
                    },

                    {
                    field: "reasoning",
                    headerName: "AI Reasoning",
                    minWidth: 400,
                    flex: 1,
                    renderCell: (params) => (
                        <Box
                        sx={{
                            whiteSpace: "normal",
                            wordBreak: "break-word",
                            lineHeight: 1.5,
                            py: 1
                        }}
                        >
                        {params.value}
                        </Box>
                    )
                    }
                ]}
                disableRowSelectionOnClick
                sx={{
                    "& .MuiDataGrid-cell": {
                    alignItems: "start"
                    }
                }}
                />
            </Box>
            )}

        </DialogContent>

        <DialogActions>
            <Button onClick={() => setOpenOptimize(false)}>
            Close
            </Button>
        </DialogActions>
        </Dialog>
    )}
    </Box>
  );
  
}

export default Campaigns;
