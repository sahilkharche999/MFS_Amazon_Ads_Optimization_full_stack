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
    "& .MuiDataGrid-footerContainer": {
        borderTop: `1px solid ${dark ? "rgba(255,255,255,0.06)" : "#E5E7EB"}`,
    },
});
