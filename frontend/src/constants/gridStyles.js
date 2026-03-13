export const getGridStyles = (dark) => ({
    border: "none",
    fontSize: "13.5px",
    "& .MuiDataGrid-columnHeaders": {
        background: dark ? "#273449" : "#F9FAFB",
        borderBottom: `1px solid ${dark ? "rgba(255,255,255,0.07)" : "#E5E7EB"}`,
        fontSize: "11px",
        fontWeight: 700,
        letterSpacing: "0.6px",
        textTransform: "uppercase",
        minHeight: "44px !important",
    },
    "& .MuiDataGrid-row": {
        minHeight: "52px !important",
        maxHeight: "52px !important"
    },
    "& .MuiDataGrid-cell": {
        borderBottom: `1px solid ${dark ? "rgba(255,255,255,0.04)" : "#F1F5F9"}`,
        display: "flex",
        alignItems: "center",
        minHeight: "52px !important",
        maxHeight: "52px !important",
    },
    "& .MuiDataGrid-row:hover": {
        background: dark ? "rgba(99,102,241,0.07)" : "#EEF2FF",
    },
    "& .MuiDataGrid-columnSeparator": { opacity: 0.3 },

    // ======================================
    // HOVER FILTER ICON REFINEMENT
    // ======================================
    "& .MuiDataGrid-columnHeader": {
        "& .MuiDataGrid-iconButtonContainer": {
            visibility: "visible !important",
            width: "auto !important",
        },
        "& .MuiDataGrid-menuIcon": {
            width: "auto !important",
            visibility: "visible !important",
            order: 1,
            marginLeft: "0px",
        },
        // We will inject a custom button with this class
        "& .custom-filter-icon": {
            opacity: 0,
            transition: "opacity 0.2s ease, transform 0.2s ease",
            order: 0,
            marginRight: "2px",
            padding: "6px", // Larger clickable area
            minWidth: "auto",
            color: dark ? "#94A3B8" : "#64748B",
            "& svg": { fontSize: "20px" }, // Larger icon
            "&:hover": {
                background: dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.06)",
                color: dark ? "#818CF8" : "#4F46E5",
                transform: "scale(1.1)",
            }
        },
        "&:hover .custom-filter-icon": {
            opacity: 1,
        }
    },

    // ======================================
    // PREMIUM COLUMN MENU STYLING
    // ======================================
    "& .MuiDataGrid-footerContainer": {
        borderTop: `1px solid ${dark ? "rgba(255,255,255,0.06)" : "#E5E7EB"}`,
    },
});

// Styles for the actual Menu Portal (since DataGrid menus are portaled)
export const getMenuStyles = (dark) => ({
    "& .MuiPaper-root": {
        borderRadius: "18px",
        marginTop: "6px",
        minWidth: "340px",
        background: dark ? "rgba(15, 23, 42, 0.95)" : "rgba(255, 255, 255, 0.98)",
        backdropFilter: "blur(12px)",
        border: dark ? "1px solid rgba(99, 102, 241, 0.2)" : "1px solid #E2E8F0",
        boxShadow: dark ? "0 12px 32px rgba(0,0,0,0.5), 0 0 16px rgba(99,102,241,0.08)" : "0 8px 24px rgba(0,0,0,0.10)",
        padding: "8px",
    },
    "& .MuiMenuItem-root": {
        fontSize: "13px",
        fontWeight: 600,
        borderRadius: "8px",
        margin: "3px 0",
        padding: "10px 16px",
        color: dark ? "#F1F5F9" : "#334155",
        "& .MuiListItemIcon-root": {
            minWidth: "30px !important",
            color: dark ? "#94A3B8" : "#64748B",
            "& svg": { fontSize: "17px" }
        },
        "&:hover": {
            background: dark ? "rgba(99, 102, 241, 0.15)" : "#F1F5F9",
            color: dark ? "#A5B4FC" : "#4F46E5",
            "& .MuiListItemIcon-root": {
                color: dark ? "#A5B4FC" : "#4F46E5",
            }
        },
    },
});
