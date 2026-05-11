import { useState, useEffect, useContext, useRef, memo } from "react";
import {
    Box,
    Typography,
    Paper,
    Button,
    LinearProgress,
    Grid,
    Tabs,
    Tab,
    Chip,
    Tooltip,
    IconButton,
    TextField,
    Alert,
    Divider,
    CircularProgress,
    Checkbox,
    FormControlLabel,
    FormGroup,
    Skeleton,
    Collapse,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Slider
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useNavigate } from "react-router-dom";

// Icons
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import DownloadIcon from "@mui/icons-material/Download";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import InstagramIcon from "@mui/icons-material/Instagram";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import FacebookIcon from "@mui/icons-material/Facebook";
import XIcon from "@mui/icons-material/X";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import CropLandscapeIcon from "@mui/icons-material/CropLandscape";
import CropPortraitIcon from "@mui/icons-material/CropPortrait";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import HistoryIcon from "@mui/icons-material/History";
import VisibilityIcon from "@mui/icons-material/Visibility";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import ChatIcon from "@mui/icons-material/Chat";

import { ColorModeContext } from "../App";
import api from "../services/api";

// ─────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────
const IMAGE_CATEGORIES = [
    { key: "all", label: "All Assets" },
    { key: "book_cover", label: "Book Cover" },
    { key: "available_now", label: "Available Now" },
    { key: "coming_soon", label: "Coming Soon" },
    { key: "quote", label: "Narrative Beats" },
];

const CAPTION_PLATFORMS = [
    { key: "instagram", label: "Instagram", icon: <InstagramIcon sx={{ fontSize: 18 }} />, color: "#E1306C" },
    { key: "linkedin", label: "LinkedIn", icon: <LinkedInIcon sx={{ fontSize: 18 }} />, color: "#0A66C2" },
    { key: "facebook", label: "Facebook", icon: <FacebookIcon sx={{ fontSize: 18 }} />, color: "#1877F2" },
    { key: "x", label: "X (Twitter)", icon: <XIcon sx={{ fontSize: 18 }} />, color: "#000000" },
];

const REVIEW_ITEMS = [
    "Factual accuracy — all claims match the manuscript",
    "Brand tone — authoritative, accessible, and clear",
    "Legal safety — no unverified quotes or attributed statements",
    "Accessibility — captions are screen-reader friendly",
    "Platform fit — format and length appropriate for each platform",
];

const PIPELINE_STEPS = [
    "Extracting manuscript text…",
    "Uploading data to FAL…",
    "Generating concepts & prompts…",
    "Generating images…",
    "Generating promotional video…",
    "Processing video outro…",
    "Writing high-conversion captions…",
    "Ready!",
];

// ─────────────────────────────────────────────────────────
// Helper: forceDownload (Fetch-based forceful download)
// ─────────────────────────────────────────────────────────
async function forceDownload(url, filename) {
    if (!url) return;
    try {
        // For external assets, route through the backend proxy to bypass CORS
        // Use absolute URL since there's no Vite proxy configured
        const backendBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
        const fetchUrl = url.startsWith('http')
            ? `${backendBase}/social-media/download?url=${encodeURIComponent(url)}`
            : url;

        const response = await fetch(fetchUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = filename || "asset";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(blobUrl);
    } catch (err) {
        console.error("Force download failed:", err);
        window.open(url, "_blank");
    }
}

// ─────────────────────────────────────────────────────────
// Helper: cropToSquare (Canvas-based local cropping)
// ─────────────────────────────────────────────────────────
function cropToSquare(imageUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = "anonymous";

        // If external, use our proxy to ensure same-origin for canvas
        if (imageUrl && imageUrl.startsWith('http')) {
            img.src = `/api/social-media/download?url=${encodeURIComponent(imageUrl)}`;
        } else {
            img.src = imageUrl;
        }

        img.onload = () => {
            const { naturalWidth: w, naturalHeight: h } = img;
            const outputSize = 1080;
            const canvas = document.createElement("canvas");
            canvas.width = outputSize;
            canvas.height = outputSize;
            const ctx = canvas.getContext("2d");

            // Fill background (neutral white)
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, outputSize, outputSize);

            // Calculate "contain" dimensions
            const ratio = Math.min(outputSize / w, outputSize / h);
            const nw = w * ratio;
            const nh = h * ratio;
            const nx = (outputSize - nw) / 2;
            const ny = (outputSize - nh) / 2;

            ctx.drawImage(img, nx, ny, nw, nh);
            resolve(canvas.toDataURL("image/png"));
        };
        img.onerror = (err) => reject(err);
    });
}

// ─────────────────────────────────────────────────────────
// Helper: CategoryChip
// ─────────────────────────────────────────────────────────
function CategoryChip({ category }) {
    const colors = {
        book_cover: { bg: "#6366f1", label: "Book Cover" },
        available_now: { bg: "#22c55e", label: "Available Now" },
        coming_soon: { bg: "#f59e0b", label: "Coming Soon" },
        quote: { bg: "#8b5cf6", label: "Quote" },
    };
    const c = colors[category] || { bg: "#64748b", label: category };
    return (
        <Chip
            label={c.label}
            size="small"
            sx={{
                backgroundColor: c.bg,
                color: "#fff",
                fontWeight: 700,
                fontSize: "10px",
                height: 20,
                borderRadius: "6px",
                boxShadow: "0 2px 4px rgba(0,0,0,0.2)"
            }}
        />
    );
}

// ─────────────────────────────────────────────────────────
// Helper: ImageCard (portrait/square toggle + collapsible caption)
// ─────────────────────────────────────────────────────────
const ImageCard = memo(({ img, idx, globalIdx, captions, bookTitle, dark, onPreview, onDelete }) => {
    const [displayFormat, setDisplayFormat] = useState("portrait");
    const [selectedPlat, setSelectedPlat] = useState("instagram");
    const [isHovered, setIsHovered] = useState(false);
    const [captionOpen, setCaptionOpen] = useState(false);
    const isPortrait = displayFormat === "portrait";

    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);

    // Build the correct URL — use relative path for local assets so Vite proxy handles CORS
    const getFinalUrl = (url) => {
        if (!url) return "";
        if (url.startsWith("http")) return url; // External FAL URL — use as-is
        return url; // Local /static/... — Vite proxy will forward to :8000
    };

    const finalUrl = getFinalUrl(img.url);

    return (
        <Box
            sx={{
                borderRadius: "14px",
                overflow: "hidden",
                background: dark ? "rgba(255,255,255,0.04)" : "#f9fafb",
                border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
                transition: "all 0.3s ease",
                position: "relative",
                mb: 2,
                "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: "0 12px 30px rgba(0,0,0,0.2)",
                },
            }}
        >
            {/* ── Image Display ── */}
            <Box
                sx={{
                    position: "relative",
                    cursor: "pointer",
                    aspectRatio: isPortrait ? "3/4" : "1/1",
                    overflow: "hidden",
                    background: isPortrait ? (dark ? "rgba(0,0,0,0.2)" : "#eee") : (dark ? "#111" : "#fff"),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                {img.url ? (
                    <>
                        {/* Shimmer skeleton while loading */}
                        {!imageLoaded && !imageError && (
                            <Box sx={{
                                position: "absolute", inset: 0,
                                background: dark
                                    ? "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 75%)"
                                    : "linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%)",
                                backgroundSize: "200% 100%",
                                animation: "shimmer 1.5s infinite",
                                "@keyframes shimmer": {
                                    "0%": { backgroundPosition: "200% 0" },
                                    "100%": { backgroundPosition: "-200% 0" },
                                }
                            }} />
                        )}
                        <img
                            src={finalUrl}
                            alt={`${img.category} ${idx + 1}`}
                            style={{
                                width: "100%",
                                height: "100%",
                                objectFit: isPortrait ? "cover" : "contain",
                                objectPosition: "center",
                                display: "block",
                                transition: "transform 0.5s ease, opacity 0.4s ease",
                                transform: isHovered ? "scale(1.05)" : "scale(1)",
                                opacity: imageLoaded ? 1 : 0,
                            }}
                            loading="lazy"
                            onClick={() => onPreview && onPreview(finalUrl, isPortrait ? "portrait" : "square")}
                            onLoad={() => setImageLoaded(true)}
                            onError={() => setImageError(true)}
                        />
                        {/* Error state — only shown if image actually failed */}
                        {imageError && (
                            <Box sx={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1, p: 2 }}>
                                <Typography variant="caption" sx={{ color: "warning.main", textAlign: "center" }}>⚠️ Image failed to load</Typography>
                                <Typography variant="caption" sx={{ color: "text.disabled", textAlign: "center", fontSize: "11px" }}>S3 upload may have failed.<br />Regenerate to get a new link.</Typography>
                            </Box>
                        )}
                        {/* Hover Overlay */}
                        <Box
                            sx={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                width: "100%",
                                height: "100%",
                                background: "rgba(0,0,0,0.3)",
                                opacity: isHovered ? 1 : 0,
                                transition: "opacity 0.3s ease",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                pointerEvents: "none"
                            }}
                        >
                            <Button
                                variant="contained"
                                size="small"
                                startIcon={<VisibilityIcon />}
                                sx={{
                                    backgroundColor: "rgba(255,255,255,0.9)",
                                    color: "#000",
                                    fontWeight: 700,
                                    borderRadius: "30px",
                                    pointerEvents: "auto",
                                    "&:hover": { backgroundColor: "#fff" }
                                }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onPreview && onPreview(finalUrl, isPortrait ? "portrait" : "square");
                                }}
                            >
                                View
                            </Button>
                        </Box>
                    </>
                ) : (
                    <Box sx={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1, p: 2 }}>
                        <Typography variant="caption" sx={{ color: "error.main" }}>No URL generated</Typography>
                        <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "11px", textAlign: "center" }}>FAL generation may have failed. Try regenerating.</Typography>
                    </Box>
                )}

                {/* Portrait / Square toggle + Delete — top right */}
                <Box
                    sx={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        zIndex: 2,
                        display: "flex",
                        gap: 0.5,
                        background: "rgba(0,0,0,0.55)",
                        borderRadius: "8px",
                        p: "2px 4px",
                    }}
                >
                    <Tooltip title="Portrait (3:4)">
                        <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); setDisplayFormat("portrait"); }}
                            sx={{
                                p: 0.5,
                                color: isPortrait ? "#6366f1" : "rgba(255,255,255,0.6)",
                                background: isPortrait ? "rgba(99,102,241,0.25)" : "transparent",
                                borderRadius: "6px",
                                "&:hover": { background: "rgba(99,102,241,0.15)" },
                            }}
                        >
                            <CropPortraitIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Square (1:1)">
                        <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); setDisplayFormat("square"); }}
                            sx={{
                                p: 0.5,
                                color: !isPortrait ? "#6366f1" : "rgba(255,255,255,0.6)",
                                background: !isPortrait ? "rgba(99,102,241,0.25)" : "transparent",
                                borderRadius: "6px",
                                "&:hover": { background: "rgba(99,102,241,0.15)" },
                            }}
                        >
                            <CropLandscapeIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>

                    <Tooltip title="Delete this asset">
                        <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); onDelete && onDelete(img.url); }}
                            sx={{
                                p: 0.5,
                                color: "#ef4444",
                                background: "rgba(239,68,68,0.1)",
                                ml: 0.5,
                                borderRadius: "6px",
                                "&:hover": { background: "rgba(239,68,68,0.2)" },
                            }}
                        >
                            <DeleteOutlineIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                </Box>

                {/* Category chip — top left */}
                <Box sx={{ position: "absolute", top: 6, left: 6 }}>
                    <CategoryChip category={img.category} />
                </Box>
            </Box>

            {/* ── Captions Area ── */}
            {captions && (
                <Box sx={{ px: 1.5, pb: 1.5 }}>
                    <Box sx={{ display: "flex", gap: 1, mb: 1, borderBottom: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #eee", pb: 0.5 }}>
                        {CAPTION_PLATFORMS.map(p => (
                            <IconButton
                                key={p.key}
                                size="small"
                                onClick={() => setSelectedPlat(p.key)}
                                sx={{
                                    p: 0.5,
                                    color: selectedPlat === p.key ? p.color : "text.disabled",
                                    background: selectedPlat === p.key ? `${p.color}15` : "transparent",
                                    borderRadius: "4px"
                                }}
                            >
                                {p.icon}
                            </IconButton>
                        ))}
                    </Box>
                    <Box sx={{ position: "relative" }}>
                        <Box
                            sx={{
                                maxHeight: "80px",
                                overflowY: "auto",
                                pr: 1,
                                "&::-webkit-scrollbar": { width: "3px" },
                                "&::-webkit-scrollbar-thumb": { background: "rgba(99,102,241,0.2)", borderRadius: "10px" }
                            }}
                        >
                            {(() => {
                                // The backend now generates unique captions for every image in the batch.
                                // We use globalIdx to link each image to its matching caption.
                                const captionText = (captions[selectedPlat] || [])[globalIdx];
                                const isCreditsError = captionText && (captionText.includes("Credits Low") || captionText.includes("402") || captionText.includes("Recharge"));
                                if (isCreditsError) {
                                    return (
                                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, py: 0.5 }}>
                                            <Typography variant="caption" sx={{ fontSize: "11px", color: "warning.main", fontWeight: 700 }}>
                                                ⚡ Credits Low
                                            </Typography>
                                            <Typography variant="caption" sx={{ fontSize: "10px", color: "text.disabled" }}>
                                                — Recharge OpenRouter to generate captions
                                            </Typography>
                                        </Box>
                                    );
                                }
                                return (
                                    <Typography
                                        variant="caption"
                                        sx={{
                                            fontSize: "11px",
                                            lineHeight: 1.4,
                                            color: dark ? "rgba(255,255,255,0.65)" : "#374151",
                                        }}
                                    >
                                        {captionText || "No caption available"}
                                    </Typography>
                                );
                            })()}
                        </Box>
                        <Box sx={{ position: "absolute", bottom: -2, right: -2 }}>
                            <CopyButton text={(captions[selectedPlat] || [])[globalIdx] || ""} size="small" />
                        </Box>
                    </Box>
                </Box>
            )}

            {/* ── Card footer: download ── */}
            <Box sx={{ px: 1.5, py: 1, display: "flex", alignItems: "center", justifyContent: "flex-end", borderTop: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #eee" }}>
                {img.url && (
                    <Box sx={{ display: "flex", gap: 0.5 }}>
                        <Tooltip title={`Download ${isPortrait ? "Portrait" : "Square"}`}>
                            <IconButton
                                size="small"
                                onClick={async () => {
                                    const filename = `${bookTitle.replace(/\s+/g, "_")}_${idx}`;
                                    if (isPortrait) {
                                        await forceDownload(finalUrl, `${filename}_portrait.png`);
                                    } else {
                                        try {
                                            const croppedData = await cropToSquare(finalUrl);
                                            const link = document.createElement("a");
                                            link.href = croppedData;
                                            link.download = `${filename}_square.png`;
                                            link.click();
                                        } catch (err) {
                                            console.error("Cropping failed:", err);
                                        }
                                    }
                                }}
                                sx={{ color: "#6366f1", p: 0.5, "&:hover": { background: "rgba(99,102,241,0.1)" } }}
                            >
                                <DownloadIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                        </Tooltip>
                    </Box>
                )}
            </Box>
        </Box >
    );
});

// ─────────────────────────────────────────────────────────
// Helper: VideoCard
// ─────────────────────────────────────────────────────────
const VideoCard = memo(({ vid, idx, bookTitle, dark, onPreview, onDelete }) => {
    const [isHovered, setIsHovered] = useState(false);

    // Build the correct URL — use relative path for local assets so Vite proxy handles CORS
    const getFinalUrl = (url) => {
        if (!url) return "";
        if (url.startsWith("http")) return url; // External FAL URL — use as-is
        return url; // Local /static/... — Vite proxy will forward to :8000
    };

    const finalUrl = getFinalUrl(vid.url);

    return (
        <Box
            sx={{
                borderRadius: "14px",
                overflow: "hidden",
                background: dark ? "rgba(255,255,255,0.04)" : "#f9fafb",
                border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
                transition: "transform 0.2s, box-shadow 0.2s",
                position: "relative",
                "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
                },
            }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Box
                onClick={() => onPreview && onPreview(finalUrl)}
                sx={{
                    position: "relative",
                    width: "100%",
                    aspectRatio: "9/16",
                    background: "#000",
                    cursor: "pointer"
                }}
            >
                {vid.url ? (
                    <video
                        src={finalUrl}
                        preload="metadata"
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                ) : (
                    <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 1.5, p: 3 }}>
                        <Typography variant="body2" sx={{ fontWeight: 700, color: "error.main", textAlign: "center" }}>
                            Creative moment unavailable
                        </Typography>
                        <Typography variant="caption" sx={{ textAlign: "center", color: dark ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.5)", fontSize: "10px", lineHeight: 1.4 }}>
                            {vid.error && vid.error.includes("extraction")
                                ? "We couldn't find a cinematic moment in this manuscript section. Try uploading a different excerpt."
                                : (vid.error || "The AI encountered a temporary issue. Please try again.")}
                        </Typography>
                    </Box>
                )}

                {/* Play Icon Overlay */}
                <Box
                    sx={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        background: "rgba(0,0,0,0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        opacity: isHovered ? 1 : 0.7,
                        transition: "opacity 0.3s"
                    }}
                >
                    <PlayCircleOutlineIcon sx={{ fontSize: 48, color: "white", filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.5))" }} />
                </Box>

                {/* Top Action Buttons */}
                <Box
                    sx={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        display: "flex",
                        gap: 0.5,
                        background: "rgba(0,0,0,0.55)",
                        borderRadius: "8px",
                        p: "2px 4px",
                        opacity: isHovered ? 1 : 0.8,
                        transition: "opacity 0.2s"
                    }}
                >
                    <Tooltip title="Download this video">
                        <IconButton
                            size="small"
                            onClick={async (e) => {
                                e.stopPropagation();
                                await forceDownload(finalUrl, `${bookTitle.replace(/\s+/g, '_')}_video_${idx}.mp4`);
                            }}
                            sx={{
                                p: 0.5,
                                color: "#6366f1",
                                background: "rgba(99,102,241,0.1)",
                                borderRadius: "6px",
                                "&:hover": { background: "rgba(99,102,241,0.2)" },
                            }}
                        >
                            <DownloadIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete this video">
                        <IconButton
                            size="small"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDelete && onDelete(vid.url);
                            }}
                            sx={{
                                p: 0.5,
                                color: "#ef4444",
                                background: "rgba(239,68,68,0.1)",
                                borderRadius: "6px",
                                "&:hover": { background: "rgba(239,68,68,0.2)" },
                            }}
                        >
                            <DeleteOutlineIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                </Box>

                {/* Visual Label */}
                <Box sx={{ position: "absolute", top: 8, left: 8 }}>
                    <Chip
                        label="VIDEO"
                        size="small"
                        sx={{
                            background: "linear-gradient(45deg, #f093fb 0%, #f5576c 100%)",
                            color: "#white",
                            fontWeight: 900,
                            fontSize: "9px",
                            height: 18
                        }}
                    />
                </Box>
            </Box>

            <Box sx={{ px: 1.5, py: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 700, display: "block", mb: 0.5, color: "text.secondary" }}>
                    {typeof vid.concept === 'object'
                        ? (vid.concept.hook || vid.concept.scene_desc || "Promotional Video")
                        : (vid.concept ? vid.concept.substring(0, 60) + "..." : "Promotional Video")}
                </Typography>
                {vid.url && (
                    <Button
                        variant="outlined"
                        fullWidth
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={async () => await forceDownload(finalUrl, `${bookTitle.replace(/\s+/g, '_')}_video.mp4`)}
                        sx={{ mt: 1, borderRadius: "8px", textTransform: "none", fontSize: "11px" }}
                    >
                        Download Video
                    </Button>
                )}
            </Box>
        </Box>
    );
});

// ─────────────────────────────────────────────────────────
// Helper: CopyButton
// ─────────────────────────────────────────────────────────
function CopyButton({ text }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <Tooltip title={copied ? "Copied!" : "Copy caption"}>
            <IconButton size="small" onClick={handleCopy}>
                {copied ? (
                    <CheckCircleIcon sx={{ fontSize: 16, color: "#22c55e" }} />
                ) : (
                    <ContentCopyIcon sx={{ fontSize: 16 }} />
                )}
            </IconButton>
        </Tooltip>
    );
}

// ─────────────────────────────────────────────────────────
// Helper to normalize S3 URLs for DNS resilience
const normalizeS3Url = (url) => {
    if (!url || !url.includes("amazonaws.com")) return url;
    // Transform bucket.s3.region.amazonaws.com/key -> s3.region.amazonaws.com/bucket/key
    const match = url.match(/^https:\/\/([^.]+)\.s3\.([^.]+)\.amazonaws\.com\/(.+)$/);
    if (match) {
        const [, bucket, region, key] = match;
        return `https://s3.${region}.amazonaws.com/${bucket}/${key}`;
    }
    return url;
};

// ─────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────
function SocialMediaGenerator() {
    const theme = useTheme();
    const { toggleColorMode } = useContext(ColorModeContext);
    const dark = theme.palette.mode === "dark";
    const navigate = useNavigate();
    const fileInputRef = useRef(null);
    const coverInputRef = useRef(null);

    // ── Form state ──
    const [file, setFile] = useState(null);
    const [coverFile, setCoverFile] = useState(null);
    const [coverPreview, setCoverPreview] = useState(null);
    const [bookTitle, setBookTitle] = useState("");
    const [authorName, setAuthorName] = useState("");
    const [dragOver, setDragOver] = useState(false);
    const [dragOverCover, setDragOverCover] = useState(false);
    const [numCover, setNumCover] = useState(12);
    const [numAvailable, setNumAvailable] = useState(2);
    const [numSoon, setNumSoon] = useState(2);
    const [numOthers, setNumOthers] = useState(4);
    const [numVideos, setNumVideos] = useState(2);

    // ── Generation state ──
    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);
    const [progress, setProgress] = useState(0);
    const [pipelineStep, setPipelineStep] = useState(0);
    const [error, setError] = useState(null);
    // Persist batches to localStorage so they survive page refreshes
    const [batches, setBatches] = useState(() => {
        try {
            const saved = localStorage.getItem("smg_batches");
            return saved ? JSON.parse(saved) : [];
        } catch {
            return [];
        }
    });
    // ── Deletion state ──
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [batchToDelete, setBatchToDelete] = useState(null);
    const [deleting, setDeleting] = useState(false);
    // ── Preview state ──
    const [previewOpen, setPreviewOpen] = useState(false);
    const [previewUrl, setPreviewUrl] = useState("");
    const [previewType, setPreviewType] = useState("image"); // "image" | "video"
    const [previewFormat, setPreviewFormat] = useState("portrait"); // "portrait" | "square"

    // ── Session state (which batches are expanded) ──
    const [expandedBatches, setExpandedBatches] = useState({}); // { batchId: boolean }
    const [searchQuery, setSearchQuery] = useState("");

    const toggleBatch = (batchId) => {
        setExpandedBatches(prev => ({
            ...prev,
            [batchId]: !prev[batchId]
        }));
    };

    // ── Persist batches to localStorage whenever they change ──
    useEffect(() => {
        try {
            localStorage.setItem("smg_batches", JSON.stringify(batches));
        } catch { }
        setFetching(false);
    }, [batches]);

    // ── Load history on mount (Universal S3 History) ──
    const fetchHistory = async () => {
        setFetching(true);
        try {
            // Priority 1: Fetch from Backend (Universal S3 manifests)
            const res = await api.get("/social-media/history");
            if (res.data.success && Array.isArray(res.data.batches)) {
                // Deduplicate and merge (Backend is source of truth)
                setBatches(res.data.batches);
                return;
            }
        } catch (err) {
            console.error("Failed to load history from API:", err);
            // Fallback: localStorage
            const saved = localStorage.getItem("smg_batches");
            if (saved) setBatches(JSON.parse(saved));
        } finally {
            setFetching(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    // ── UI tabs ──
    const [batchFilters, setBatchFilters] = useState({}); // { batchId: categoryKey }
    const [captionPlatformTab, setCaptionPlatformTab] = useState("instagram");

    // ── Review checklist ──
    const [reviewChecks, setReviewChecks] = useState(
        Object.fromEntries(REVIEW_ITEMS.map((_, i) => [i, false]))
    );

    const allChecked = Object.values(reviewChecks).every(Boolean);

    // ─────────────────────────────────────────────────────
    // File handling
    // ─────────────────────────────────────────────────────
    const handleFileSelect = (f) => {
        if (!f) return;
        const ext = f.name.toLowerCase();
        if (!(ext.endsWith(".pdf") || ext.endsWith(".docx"))) {
            setError("Please upload a PDF or DOCX file for the manuscript.");
            return;
        }
        setError(null);
        setFile(f);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleFileSelect(e.dataTransfer.files[0]);
    };

    // Cover image handlers
    const handleCoverSelect = (f) => {
        if (!f) return;
        const ok = ["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(f.type)
            || /\.(jpe?g|png|webp)$/i.test(f.name);
        if (!ok) { setError("Cover image must be JPG, PNG or WebP."); return }
        setError(null);
        setCoverFile(f);
        setCoverPreview(URL.createObjectURL(f));
    };

    const handleCoverDrop = (e) => {
        e.preventDefault();
        setDragOverCover(false);
        handleCoverSelect(e.dataTransfer.files[0]);
    };

    // ─────────────────────────────────────────────────────
    // Generate handler — calls backend
    // ─────────────────────────────────────────────────────
    const handleGenerate = async () => {
        const hasImages = (numCover + numAvailable + numSoon + numOthers) > 0;
        const hasVideos = numVideos > 0;

        if (!file) { setError("Please upload a manuscript (PDF or DOCX)."); return; }
        if (!bookTitle.trim()) { setError("Please enter the book title."); return; }
        if (!authorName.trim()) { setError("Please enter the author name."); return; }
        if (!hasImages && !hasVideos) { setError("Please select at least one asset to generate."); return; }
        if (hasImages && !coverFile) { setError("A cover image is required for image generation."); return; }

        setError(null);
        setLoading(true);
        setProgress(5);
        setPipelineStep(0);

        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("book_title", bookTitle.trim());
            formData.append("author_name", authorName.trim());
            formData.append("generate_images", hasImages.toString());
            formData.append("generate_videos", hasVideos.toString());
            formData.append("num_cover", numCover);
            formData.append("num_available", numAvailable);
            formData.append("num_soon", numSoon);
            formData.append("num_others", numOthers);
            formData.append("num_videos", numVideos);
            if (coverFile) formData.append("cover_image", coverFile);

            // ── Step 1: Submit job (returns immediately with job_id) ──
            const submitRes = await api.post("/social-media/generate", formData, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 30_000, // only 30s for submission
            });

            if (!submitRes.data.success) {
                setError(submitRes.data.message || "Failed to start generation.");
                return;
            }

            const jobId = submitRes.data.job_id;
            setProgress(10);

            // ── Step 2: Poll for job completion ──
            const STEP_PROGRESS = {
                "Queued": 10,
                "Extracting manuscript text": 20,
                "Uploading book cover to FAL": 30,
                "Detecting book genre and ideas": 35,
                "Generating post ideas": 40,
                "Generating image prompt concepts": 50,
                "Generating 30 image prompts": 50,
                "Generating images": 65,
                "Generating video cinematic logic": 75,
                "Generating promotional video (FAL)": 85,
                "Processing video outro (FFmpeg)": 90,
                "Generating platform-specific captions": 95,
                "Generating captions": 95,
                "Done": 100,
            };

            const STEP_TO_INDEX = {
                "Extracting manuscript text": 0,
                "Uploading book cover to FAL": 1,
                "Detecting book genre and ideas": 2,
                "Generating post ideas": 2,
                "Generating image prompt concepts": 2,
                "Generating 30 image prompts": 2,
                "Generating images": 3,
                "Generating video cinematic logic": 4,
                "Generating promotional video (FAL)": 4,
                "Processing video outro (FFmpeg)": 5,
                "Generating platform-specific captions": 6,
                "Generating captions": 6,
                "Done": 7,
            };

            await new Promise((resolve, reject) => {
                const poll = setInterval(async () => {
                    try {
                        const statusRes = await api.get(`/social-media/job/${jobId}`);
                        const { status, step, result, error } = statusRes.data;

                        // Update UI progress %
                        if (step && STEP_PROGRESS[step] !== undefined) {
                            setProgress(STEP_PROGRESS[step]);
                        } else if (status === "running") {
                            setProgress(prev => Math.min(prev + 1, 98));
                        }

                        // Update UI pipeline step index
                        if (step && STEP_TO_INDEX[step] !== undefined) {
                            setPipelineStep(STEP_TO_INDEX[step]);
                        }

                        if (status === "completed") {
                            clearInterval(poll);
                            setProgress(100);
                            setPipelineStep(PIPELINE_STEPS.length - 1);
                            if (result) setBatches(prev => [result, ...prev]);
                            resolve();
                        } else if (status === "failed") {
                            clearInterval(poll);
                            reject(new Error(error || "Generation failed on server."));
                        }
                    } catch (pollErr) {
                        clearInterval(poll);
                        reject(pollErr);
                    }
                }, 5_000); // poll every 5 seconds
            });

        } catch (err) {
            const msg = err.response?.data?.message || err.message || "Generation failed.";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteBatch = async () => {
        if (!batchToDelete) return;

        try {
            setDeleting(true);
            await api.post(`/social-media/delete-asset/${batchToDelete}`);
            setBatches(prev => prev.filter(b => (b.id || b.job_id) !== batchToDelete));
            setDeleteDialogOpen(false);
            setBatchToDelete(null);
        } catch (err) {
            setError("Failed to delete batch: " + (err.response?.data?.message || err.message));
        } finally {
            setDeleting(false);
        }
    };

    const handleDeleteAsset = async (batchId, assetUrl) => {
        try {
            const formData = new FormData();
            formData.append("batch_id", batchId);
            formData.append("asset_url", assetUrl);

            await api.post("/social-media/delete-item", formData);

            // Update local state
            setBatches(prev => prev.map(b => {
                if ((b.id || b.job_id) === batchId) {
                    return {
                        ...b,
                        images: b.images.filter(img => img.url !== assetUrl),
                        videos: b.videos.filter(vid => vid.url !== assetUrl)
                    };
                }
                return b;
            }));
        } catch (err) {
            setError("Failed to delete asset: " + (err.response?.data?.message || err.message));
        }
    };

    const openDeleteDialog = (batchId) => {
        setBatchToDelete(batchId);
        setDeleteDialogOpen(true);
    };

    // ─────────────────────────────────────────────────────
    // Styles helpers
    // ─────────────────────────────────────────────────────
    const cardStyle = {
        borderRadius: "20px",
        border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #E5E7EB",
        background: dark ? "#111827" : "#ffffff",
        boxShadow: dark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 4px 20px rgba(0,0,0,0.06)",
        p: 3,
        mb: 3,
    };

    // ─────────────────────────────────────────────────────
    // Render
    // ─────────────────────────────────────────────────────
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
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 4 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <IconButton
                        size="small"
                        onClick={() => navigate("/")}
                        sx={{
                            background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
                            border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)",
                            width: 36,
                            height: 36,
                        }}
                    >
                        <ArrowBackIcon sx={{ fontSize: 18 }} />
                    </IconButton>
                    <Box>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                            <AutoAwesomeIcon sx={{ color: "#6366f1", fontSize: 28 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.5px" }}>
                                Social Media Generator
                            </Typography>
                        </Box>
                        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.25 }}>
                            Upload a manuscript · Generate  images ·  videos · Captions for all platforms
                        </Typography>
                    </Box>
                </Box>

                <IconButton
                    onClick={toggleColorMode}
                    size="small"
                    sx={{
                        background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
                        border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)",
                        width: 36,
                        height: 36,
                    }}
                >
                    {dark ? <LightModeIcon sx={{ fontSize: 18 }} /> : <DarkModeIcon sx={{ fontSize: 18 }} />}
                </IconButton>
            </Box>

            {/* ── Upload + Config Section ── */}
            <Paper elevation={0} sx={cardStyle}>
                <Typography variant="h6" sx={{ mb: 2.5, fontWeight: 700 }}>
                    📖 Book Details
                </Typography>

                <Grid container spacing={3}>

                    {/* ── Manuscript upload (PDF/DOCX) ── */}
                    <Grid item xs={12} sm={6} md={3}>
                        <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.55)" : "#374151", fontWeight: 700, mb: 1, display: "block", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                            Manuscript *
                        </Typography>
                        <Box
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                            sx={{
                                border: `2px dashed ${dragOver ? "#6366f1"
                                    : file ? "#22c55e"
                                        : dark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)"
                                    }`,
                                borderRadius: "16px",
                                p: 3,
                                textAlign: "center",
                                cursor: "pointer",
                                background: dragOver ? (dark ? "rgba(99,102,241,0.08)" : "rgba(99,102,241,0.04)")
                                    : file ? (dark ? "rgba(34,197,94,0.06)" : "rgba(34,197,94,0.03)") : "transparent",
                                transition: "all 0.2s ease",
                                minHeight: 150,
                                display: "flex", flexDirection: "column",
                                alignItems: "center", justifyContent: "center", gap: 1,
                                "&:hover": { borderColor: "#6366f1", background: dark ? "rgba(99,102,241,0.06)" : "rgba(99,102,241,0.03)" },
                            }}
                        >
                            <input ref={fileInputRef} type="file" accept=".pdf,.docx" style={{ display: "none" }}
                                onChange={(e) => handleFileSelect(e.target.files[0])} />
                            {file ? (
                                <>
                                    <CheckCircleIcon sx={{ fontSize: 36, color: "#22c55e" }} />
                                    <Typography variant="body2" sx={{ fontWeight: 600, color: "#22c55e", wordBreak: "break-all" }}>{file.name}</Typography>
                                    <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.4)" : "#6b7280" }}>{(file.size / 1024 / 1024).toFixed(2)} MB · Click to change</Typography>
                                </>
                            ) : (
                                <>
                                    <CloudUploadIcon sx={{ fontSize: 36, color: dark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.25)" }} />
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Drop PDF/DOCX or click</Typography>
                                    <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.4)" : "#6b7280" }}>Manuscript · PDF or DOCX</Typography>
                                </>
                            )}
                        </Box>
                    </Grid>

                    {/* ── Book Cover Image upload ── */}
                    <Grid item xs={12} sm={6} md={3}>
                        <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.55)" : "#374151", fontWeight: 700, mb: 1, display: "block", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                            Book Cover Image
                            <Chip label="Recommended" size="small" sx={{ ml: 1, fontSize: "9px", height: 16, background: "rgba(99,102,241,0.15)", color: "#6366f1", fontWeight: 700 }} />
                        </Typography>
                        <Box
                            onDragOver={(e) => { e.preventDefault(); setDragOverCover(true); }}
                            onDragLeave={() => setDragOverCover(false)}
                            onDrop={handleCoverDrop}
                            onClick={() => coverInputRef.current?.click()}
                            sx={{
                                border: `2px dashed ${dragOverCover ? "#6366f1"
                                    : coverFile ? "#8b5cf6"
                                        : dark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)"
                                    }`,
                                borderRadius: "16px",
                                p: 1,
                                textAlign: "center",
                                cursor: "pointer",
                                background: dragOverCover ? (dark ? "rgba(139,92,246,0.08)" : "rgba(139,92,246,0.04)")
                                    : coverFile ? (dark ? "rgba(139,92,246,0.06)" : "rgba(139,92,246,0.03)") : "transparent",
                                transition: "all 0.2s ease",
                                minHeight: 150,
                                display: "flex", flexDirection: "column",
                                alignItems: "center", justifyContent: "center", gap: 1,
                                overflow: "hidden",
                                "&:hover": { borderColor: "#8b5cf6", background: dark ? "rgba(139,92,246,0.06)" : "rgba(139,92,246,0.03)" },
                            }}
                        >
                            <input ref={coverInputRef} type="file" accept="image/jpeg,image/png,image/webp"
                                style={{ display: "none" }}
                                onChange={(e) => handleCoverSelect(e.target.files[0])} />
                            {coverFile && coverPreview ? (
                                <>
                                    <img src={coverPreview} alt="Cover preview"
                                        style={{ maxHeight: 110, maxWidth: "100%", borderRadius: 8, objectFit: "contain" }} />
                                    <Typography variant="caption" sx={{ color: "#8b5cf6", fontWeight: 600 }}>✓ Cover ready · Click to change</Typography>
                                </>
                            ) : (
                                <>
                                    <CloudUploadIcon sx={{ fontSize: 36, color: dark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.25)" }} />
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Drop cover or click</Typography>
                                    <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.4)" : "#6b7280" }}>JPG / PNG / WebP</Typography>
                                    <Typography variant="caption" sx={{ color: dark ? "rgba(255,255,255,0.25)" : "#6b7280", mt: 0.5, fontSize: "10px" }}>
                                        Used as reference for<br />image-to-image generation
                                    </Typography>
                                </>
                            )}
                        </Box>
                    </Grid>

                    {/* Book metadata */}
                    <Grid item xs={12} md={6}>
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
                            <TextField
                                label="Book Title"
                                placeholder="e.g. The Power of Habit"
                                value={bookTitle}
                                onChange={(e) => setBookTitle(e.target.value)}
                                fullWidth
                                size="small"
                                InputProps={{
                                    startAdornment: <LibraryBooksIcon sx={{ fontSize: 18, mr: 1, color: "text.secondary" }} />,
                                }}
                                sx={{
                                    "& .MuiOutlinedInput-root": {
                                        borderRadius: "12px",
                                        background: dark ? "rgba(255,255,255,0.03)" : "#f9fafb",
                                    },
                                    "& input:-webkit-autofill": {
                                        WebkitBoxShadow: `0 0 0 1000px ${dark ? "#111827" : "#f9fafb"} inset`,
                                        WebkitTextFillColor: dark ? "#ffffff" : "#111827",
                                        transition: "background-color 5000s ease-in-out 0s",
                                    },
                                }}
                            />
                            <TextField
                                label="Author Name"
                                placeholder="e.g. Charles Duhigg"
                                value={authorName}
                                onChange={(e) => setAuthorName(e.target.value)}
                                fullWidth
                                size="small"
                                sx={{
                                    "& .MuiOutlinedInput-root": {
                                        borderRadius: "12px",
                                        background: dark ? "rgba(255,255,255,0.03)" : "#f9fafb",
                                    },
                                    "& input:-webkit-autofill": {
                                        WebkitBoxShadow: `0 0 0 1000px ${dark ? "#111827" : "#f9fafb"} inset`,
                                        WebkitTextFillColor: dark ? "#ffffff" : "#111827",
                                        transition: "background-color 5000s ease-in-out 0s",
                                    },
                                }}
                            />

                            {/* Cinematic Configuration Mixer — Enhanced All-in-One */}
                            <Paper variant="outlined" sx={{
                                mt: 1,
                                mb: 1,
                                p: 2,
                                borderRadius: "16px",
                                background: dark ? "rgba(255,255,255,0.02)" : "#ffffff",
                                border: `1px solid ${dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)"}`,
                                boxShadow: dark ? "0 4px 20px rgba(0,0,0,0.2)" : "0 2px 10px rgba(0,0,0,0.02)"
                            }}>
                                <Typography variant="caption" sx={{
                                    color: dark ? "rgba(255,255,255,0.45)" : "#374151",
                                    fontWeight: 800,
                                    mb: 2,
                                    display: "block",
                                    textTransform: "uppercase",
                                    letterSpacing: "1.5px",
                                    fontSize: "10px"
                                }}>
                                    Asset Mixer
                                </Typography>

                                <Grid container spacing={2}>
                                    {[
                                        { label: "Book Cover", count: numCover, setter: setNumCover, color: "#6366f1", icon: <LibraryBooksIcon sx={{ fontSize: 20 }} /> },
                                        { label: "Available Now", count: numAvailable, setter: setNumAvailable, color: "#22c55e", icon: <AutoAwesomeIcon sx={{ fontSize: 20 }} /> },
                                        { label: "Coming Soon", count: numSoon, setter: setNumSoon, color: "#ec4899", icon: <CalendarTodayIcon sx={{ fontSize: 20 }} /> },
                                        { label: "Narrative Beats", count: numOthers, setter: setNumOthers, color: "#f59e0b", icon: <ChatIcon sx={{ fontSize: 20 }} /> },
                                        { label: "Videos", count: numVideos, setter: setNumVideos, color: "#8b5cf6", icon: <PlayCircleOutlineIcon sx={{ fontSize: 20 }} />, isVideo: true },
                                    ].map((type) => (
                                        <Grid item xs={type.isVideo ? 12 : 6} key={type.label}>
                                            <Box sx={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: 1.5,
                                                p: 1,
                                                px: 1.5,
                                                borderRadius: "12px",
                                                background: dark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)",
                                                border: `1px solid ${dark ? "rgba(255,255,255,0.05)" : "transparent"}`,
                                                transition: "all 0.2s ease",
                                                "&:hover": {
                                                    background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
                                                }
                                            }}>
                                                <Box sx={{ color: type.color, display: "flex" }}>{type.icon}</Box>
                                                <Typography variant="body2" sx={{ fontWeight: 700, flex: 1, fontSize: "13px" }}>{type.label}</Typography>
                                                <Box sx={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: 1.5,
                                                    background: dark ? "rgba(0,0,0,0.3)" : "rgba(255,255,255,0.8)",
                                                    borderRadius: "10px",
                                                    px: 1,
                                                    py: 0.5,
                                                    border: `1px solid ${dark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.12)"}`,
                                                    boxShadow: "0 2px 4px rgba(0,0,0,0.05)"
                                                }}>
                                                    <IconButton
                                                        size="small"
                                                        onClick={() => type.setter(Math.max(0, type.count - 1))}
                                                        sx={{
                                                            p: 0.75,
                                                            color: type.color,
                                                            background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
                                                            "&:hover": { background: dark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.06)" }
                                                        }}
                                                    >
                                                        <RemoveIcon sx={{ fontSize: 18 }} />
                                                    </IconButton>
                                                    <TextField
                                                        value={type.count}
                                                        size="small"
                                                        variant="standard"
                                                        type="number"
                                                        onChange={(e) => {
                                                            const val = parseInt(e.target.value) || 0;
                                                            if (type.isVideo) {
                                                                if (val <= 5) type.setter(val);
                                                                else type.setter(5);
                                                            } else {
                                                                const otherTotal = (numCover + numAvailable + numSoon + numOthers) - type.count;
                                                                if (otherTotal + val <= 20) type.setter(val);
                                                                else type.setter(20 - otherTotal);
                                                            }
                                                        }}
                                                        InputProps={{
                                                            disableUnderline: true,
                                                            sx: {
                                                                fontSize: "14px",
                                                                fontWeight: 900,
                                                                width: "30px",
                                                                textAlign: "center",
                                                                "& input": {
                                                                    p: 0,
                                                                    textAlign: "center",
                                                                    appearance: "none",
                                                                    MozAppearance: "textfield",
                                                                    "&::-webkit-outer-spin-button, &::-webkit-inner-spin-button": {
                                                                        WebkitAppearance: "none",
                                                                        margin: 0
                                                                    }
                                                                }
                                                            }
                                                        }}
                                                    />
                                                    <IconButton
                                                        size="small"
                                                        onClick={() => {
                                                            if (type.isVideo) {
                                                                if (numVideos < 5) type.setter(type.count + 1);
                                                            } else {
                                                                const total = numCover + numAvailable + numSoon + numOthers;
                                                                if (total < 20) type.setter(type.count + 1);
                                                            }
                                                        }}
                                                        sx={{
                                                            p: 0.75,
                                                            color: type.color,
                                                            background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
                                                            "&:hover": { background: dark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.06)" }
                                                        }}
                                                    >
                                                        <AddIcon sx={{ fontSize: 18 }} />
                                                    </IconButton>
                                                </Box>
                                            </Box>
                                        </Grid>
                                    ))}
                                </Grid>
                            </Paper>

                            {/* Generate button */}
                            <Button
                                variant="contained"
                                size="large"
                                startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <AutoAwesomeIcon />}
                                onClick={handleGenerate}
                                disabled={!file || !bookTitle.trim() || loading}
                                sx={{
                                    background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                                    fontSize: "14px",
                                    fontWeight: 700,
                                    height: 48,
                                    borderRadius: "14px",
                                    textTransform: "none",
                                    boxShadow: "0 4px 20px rgba(99,102,241,0.4)",
                                    "&:hover": {
                                        background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
                                        boxShadow: "0 6px 24px rgba(99,102,241,0.5)",
                                    },
                                    "&:disabled": {
                                        background: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.10)",
                                        color: dark ? "rgba(255,255,255,0.3)" : "#374151",
                                        boxShadow: "none",
                                    },
                                }}
                            >
                                {loading ? "Generating Assets…" : "Generate All Assets"}
                            </Button>
                        </Box>
                    </Grid>
                </Grid>
            </Paper>

            {/* ── Progress ── */}
            {loading && (
                <Paper elevation={0} sx={{ ...cardStyle, mb: 3 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                        <CircularProgress size={20} sx={{ color: "#6366f1" }} />
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                            {PIPELINE_STEPS[pipelineStep]}
                        </Typography>
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={progress}
                        sx={{
                            height: 8,
                            borderRadius: 4,
                            background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
                            "& .MuiLinearProgress-bar": {
                                background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                                borderRadius: 4,
                            },
                        }}
                    />
                    <Typography variant="caption" sx={{ color: "text.secondary", mt: 1, display: "block" }}>
                        Step {pipelineStep + 1} of {PIPELINE_STEPS.length} · {progress}% complete · ~2–4 minutes total
                    </Typography>
                </Paper>
            )}

            {/* ── Error ── */}
            {error && (
                <Alert
                    severity="error"
                    sx={{ mb: 3, borderRadius: "14px" }}
                    onClose={() => setError(null)}
                >
                    {error}
                </Alert>
            )}

            {/* ── Sessions Section Header ── */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", mb: 3 }}>

                {batches.length > 0 && (
                    <TextField
                        size="small"
                        placeholder="Search books…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        variant="outlined"
                        sx={{
                            width: { xs: "100%", sm: 250 },
                            "& .MuiOutlinedInput-root": {
                                borderRadius: "12px",
                                background: dark ? "rgba(255,255,255,0.03)" : "#fff",
                            },
                            "& input::placeholder": {
                                color: dark ? "rgba(255,255,255,0.35)" : "#374151",
                                opacity: 1,
                            },
                            "& input": {
                                color: dark ? "#e2e8f0" : "#111827",
                            },
                        }}
                        InputProps={{
                            startAdornment: (
                                <HistoryIcon sx={{ mr: 1, color: dark ? "rgba(255,255,255,0.35)" : "#374151", fontSize: 20 }} />
                            ),
                            endAdornment: searchQuery && (
                                <IconButton size="small" onClick={() => setSearchQuery("")}>
                                    <CloseIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                            )
                        }}
                    />
                )}
            </Box>

            {/* ══════════════════════════════════════════════════
                RESULTS SECTION — shown for each batch
            ══════════════════════════════════════════════════ */}
            {batches
                .filter(b => (b.book_title || "").toLowerCase().includes((searchQuery || "").toLowerCase()))
                .map((batch) => {
                    const bid = batch.id || batch.job_id;
                    const isExpanded = expandedBatches[bid] !== false;
                    const batchImages = Array.isArray(batch.images) ? batch.images : [];
                    const batchVideos = Array.isArray(batch.videos) ? batch.videos : [];
                    return (
                        <Box key={bid} sx={{ mb: 4, position: "relative" }}>
                            {/* ── High-Status Session Header ── */}
                            <Paper
                                elevation={0}
                                onClick={() => toggleBatch(batch.id)}
                                sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    p: 2,
                                    borderRadius: isExpanded ? "16px 16px 0 0" : "16px",
                                    background: dark ? "rgba(255,255,255,0.03)" : "#f8fafc",
                                    border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #e2e8f0",
                                    cursor: "pointer",
                                    transition: "all 0.2s ease",
                                    "&:hover": {
                                        background: dark ? "rgba(255,255,255,0.05)" : "#f1f5f9"
                                    }
                                }}
                            >
                                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                                    <Box sx={{
                                        background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                                        width: 36, height: 36, borderRadius: "10px",
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        boxShadow: "0 4px 12px rgba(99,102,241,0.2)"
                                    }}>
                                        <HistoryIcon sx={{ color: "#fff", fontSize: 20 }} />
                                    </Box>
                                    <Box>
                                        <Typography variant="subtitle1" sx={{ fontWeight: 800, color: dark ? "#e2e8f0" : "#111827" }}>
                                            {batch.book_title || "Untitled Session"} <Divider sx={{ display: "inline-block", mx: 1, height: 16, verticalAlign: "middle", borderColor: dark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)" }} orientation="vertical" /> <Typography component="span" variant="subtitle2" sx={{ fontWeight: 500, color: dark ? "#94a3b8" : "#374151" }}>{batch.author_name || "Unknown Author"}</Typography>
                                        </Typography>
                                        <Typography variant="caption" sx={{ color: dark ? "#64748b" : "#6b7280", display: "block", mt: -0.5 }}>
                                            {new Date(batch.timestamp).toLocaleString()} · {batchImages.length} images · {batchVideos.length} videos
                                        </Typography>
                                    </Box>
                                </Box>

                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                    <Tooltip title="Delete Entire Session">
                                        <IconButton
                                            size="small"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                openDeleteDialog(batch.id);
                                            }}
                                            sx={{
                                                color: "error.main",
                                                "&:hover": { background: "rgba(239,68,68,0.1)" }
                                            }}
                                        >
                                            <DeleteSweepIcon sx={{ fontSize: 20 }} />
                                        </IconButton>
                                    </Tooltip>
                                    <IconButton size="small">
                                        {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                    </IconButton>
                                </Box>
                            </Paper>

                            {/* ── Collapsible Session Content ── */}
                            <Collapse in={isExpanded}>
                                <Box sx={{
                                    p: 3,
                                    border: dark ? "1px solid rgba(255,255,255,0.06)" : "1px solid #e2e8f0",
                                    borderTop: "none",
                                    borderRadius: "0 0 16px 16px",
                                    background: dark ? "rgba(0,0,0,0.1)" : "#fff"
                                }}>
                                    {/* Stats banner */}
                                    <Paper elevation={0} sx={{ ...cardStyle, p: 2, mb: 2, background: dark ? "rgba(99,102,241,0.08)" : "rgba(99,102,241,0.04)", border: "1px solid rgba(99,102,241,0.2)" }}>
                                        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
                                            <CheckCircleIcon sx={{ color: "#22c55e", fontSize: 20 }} />
                                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                Assets ready for review
                                            </Typography>
                                            <Box sx={{ ml: "auto", display: "flex", gap: 1, flexWrap: "wrap" }}>
                                                {batch.stats?.used_img2img && (
                                                    <Chip label="✦ Img2Img" size="small" sx={{ height: 20, fontSize: "10px", background: "#8b5cf622", color: "#8b5cf6", fontWeight: 700, border: "1px solid #8b5cf644" }} />
                                                )}
                                                <Chip label={`${batch.stats?.images_ok || 0} Images`} size="small" sx={{ height: 20, fontSize: "10px", background: "#6366f122", color: "#6366f1", fontWeight: 700 }} />
                                                <Chip label={`${batch.stats?.videos_ok || 0} Videos`} size="small" sx={{ height: 20, fontSize: "10px", background: "#8b5cf622", color: "#8b5cf6", fontWeight: 700 }} />
                                            </Box>
                                        </Box>
                                    </Paper>

                                    {/* ── Category Filtering Tabs (Per Batch) ── */}
                                    <Box sx={{ mb: 3, display: "flex", justifyContent: "center" }}>
                                        <Tabs
                                            value={batchFilters[batch.id] || "all"}
                                            onChange={(_, newVal) => setBatchFilters(prev => ({ ...prev, [batch.id]: newVal }))}
                                            variant="scrollable"
                                            scrollButtons="auto"
                                            sx={{
                                                minHeight: 40,
                                                "& .MuiTabs-indicator": {
                                                    height: 3,
                                                    borderRadius: "3px 3px 0 0",
                                                    background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                                                },
                                                "& .MuiTab-root": {
                                                    textTransform: "none",
                                                    fontWeight: 600,
                                                    fontSize: "13px",
                                                    minWidth: 100,
                                                    color: "text.secondary",
                                                    "&.Mui-selected": {
                                                        color: "#6366f1",
                                                    }
                                                }
                                            }}
                                        >
                                            {IMAGE_CATEGORIES.map((cat) => (
                                                <Tab key={cat.key} label={cat.label} value={cat.key} />
                                            ))}
                                        </Tabs>
                                    </Box>

                                    {/* ── Generated Images ── */}
                                    <Box sx={{ mb: 3 }}>
                                        <Grid container spacing={2}>
                                            {batchImages
                                                .filter(img => {
                                                    const currentFilter = batchFilters[batch.id] || "all";
                                                    if (currentFilter === "all") return true;
                                                    return img.category === currentFilter;
                                                })
                                                .map((img, idx) => (
                                                    <Grid item xs={12} sm={6} md={4} lg={3} key={idx}>
                                                        <ImageCard
                                                            img={img}
                                                            idx={idx}
                                                            globalIdx={batchImages.indexOf(img)}
                                                            captions={batch.captions}
                                                            bookTitle={batch.book_title}
                                                            dark={dark}
                                                            onPreview={(url, format) => {
                                                                setPreviewUrl(url);
                                                                setPreviewType("image");
                                                                setPreviewFormat(format || "portrait");
                                                                setPreviewOpen(true);
                                                            }}
                                                            onDelete={(assetUrl) => handleDeleteAsset(batch.id, assetUrl)}
                                                        />
                                                    </Grid>
                                                ))}
                                        </Grid>
                                        {/* Empty State for Filter */}
                                        {batchImages.filter(img => {
                                            const currentFilter = batchFilters[batch.id] || "all";
                                            if (currentFilter === "all") return true;
                                            return img.category === currentFilter;
                                        }).length === 0 && (
                                                <Box sx={{ py: 4, textAlign: "center", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: "12px" }}>
                                                    <Typography variant="body2" sx={{ color: "text.disabled" }}>
                                                        No {IMAGE_CATEGORIES.find(c => c.key === (batchFilters[batch.id] || "all"))?.label} image assets in this batch
                                                    </Typography>
                                                </Box>
                                            )}
                                    </Box>

                                    {/* ── Generated Videos ── */}
                                    {batchVideos.length > 0 && (
                                        <Box sx={{ mb: 3 }}>
                                            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
                                                🎬 Videos
                                            </Typography>
                                            <Grid container spacing={2}>
                                                {batchVideos.map((vid, idx) => (
                                                    <Grid item xs={12} sm={6} md={3} key={idx}>
                                                        <VideoCard
                                                            vid={vid}
                                                            idx={idx}
                                                            bookTitle={batch.book_title}
                                                            dark={dark}
                                                            onPreview={(url) => {
                                                                setPreviewUrl(url);
                                                                setPreviewType("video");
                                                                setPreviewOpen(true);
                                                            }}
                                                            onDelete={(assetUrl) => handleDeleteAsset(batch.id, assetUrl)}
                                                        />
                                                    </Grid>
                                                ))}
                                            </Grid>
                                        </Box>
                                    )}

                                    {/* Captions removed as they are now per-image */}
                                </Box>
                            </Collapse>
                        </Box>
                    );
                })}

            {fetching && batches.length === 0 && (
                <Box sx={{ p: 8, textAlign: "center" }}>
                    <CircularProgress size={30} sx={{ mb: 2 }} />
                    <Typography variant="body2" color="text.secondary">Loading your workspace assets…</Typography>
                </Box>
            )}

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={deleteDialogOpen}
                onClose={() => !deleting && setDeleteDialogOpen(false)}
                PaperProps={{
                    sx: {
                        background: dark ? "#1e1e1e" : "#fff",
                        color: dark ? "#fff" : "inherit",
                        borderRadius: "16px",
                        backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05))"
                    }
                }}
            >
                <DialogTitle sx={{ fontWeight: 700 }}>Confirm Deletion</DialogTitle>
                <DialogContent>
                    <DialogContentText sx={{ color: dark ? "rgba(255,255,255,0.7)" : "inherit" }}>
                        Are you sure you want to permanently delete this generation? This action cannot be undone and all associated files will be removed from the server.
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ p: 3, pt: 1 }}>
                    <Button
                        onClick={() => setDeleteDialogOpen(false)}
                        disabled={deleting}
                        sx={{ color: "text.secondary" }}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleDeleteBatch}
                        color="error"
                        variant="contained"
                        disabled={deleting}
                        startIcon={deleting ? <CircularProgress size={16} color="inherit" /> : <DeleteOutlineIcon />}
                        sx={{
                            borderRadius: "8px",
                            boxShadow: "none",
                            "&:hover": { boxShadow: "0 4px 12px rgba(239,68,68,0.2)" }
                        }}
                    >
                        {deleting ? "Deleting..." : "Delete Forever"}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Image Preview Lightbox */}
            <Dialog
                open={previewOpen}
                onClose={() => setPreviewOpen(false)}
                maxWidth="lg"
                PaperProps={{
                    sx: {
                        background: "transparent",
                        boxShadow: "none",
                        overflow: "hidden"
                    }
                }}
            >
                <Box sx={{ position: "relative", display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
                    <Box sx={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 1, zIndex: 10 }}>
                        <Button
                            variant="contained"
                            size="small"
                            startIcon={<DownloadIcon />}
                            sx={{
                                backgroundColor: "rgba(99,102,241,0.9)",
                                color: "#fff",
                                fontWeight: 700,
                                borderRadius: "30px",
                                "&:hover": { backgroundColor: "#6366f1" }
                            }}
                            onClick={async () => {
                                const filename = `${bookTitle.replace(/\s+/g, "_")}_asset`;
                                if (previewType === "video") {
                                    await forceDownload(previewUrl, `${filename}.mp4`);
                                } else if (previewFormat === "portrait") {
                                    await forceDownload(previewUrl, `${filename}_portrait.png`);
                                } else {
                                    // Handle Square Download
                                    try {
                                        const croppedData = await cropToSquare(previewUrl);
                                        const link = document.createElement("a");
                                        link.href = croppedData;
                                        link.download = `${filename}_square.png`;
                                        link.click();
                                    } catch (err) {
                                        console.error("Cropping failed in modal:", err);
                                    }
                                }
                            }}
                        >
                            Download {previewType === "video" ? "Video" : (previewFormat === "square" ? "Square" : "Portrait")}
                        </Button>
                        <IconButton
                            onClick={() => setPreviewOpen(false)}
                            sx={{
                                color: "#fff",
                                backgroundColor: "rgba(0,0,0,0.5)",
                                "&:hover": { backgroundColor: "rgba(0,0,0,0.8)" }
                            }}
                        >
                            <CloseIcon />
                        </IconButton>
                    </Box>

                    {previewType === "image" ? (
                        <Box sx={{
                            position: "relative",
                            width: "auto",
                            height: "auto",
                            maxWidth: "100%",
                            maxHeight: "90vh",
                            borderRadius: "12px",
                            overflow: "hidden",
                            boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
                            aspectRatio: previewFormat === "square" ? "1/1" : "3/4",
                            display: "flex",
                            justifyContent: "center",
                            alignItems: "center",
                            background: previewFormat === "square" ? (dark ? "#111" : "#fff") : "transparent"
                        }}>
                            <img
                                src={previewUrl}
                                alt="Preview"
                                style={{
                                    width: "100%",
                                    height: "100%",
                                    objectFit: previewFormat === "square" ? "contain" : "cover",
                                    objectPosition: "center",
                                    display: "block"
                                }}
                            />
                        </Box>
                    ) : (
                        <Box sx={{ width: "100%", maxWidth: "450px", aspectRatio: "9/16", borderRadius: "12px", overflow: "hidden", boxShadow: "0 10px 40px rgba(0,0,0,0.5)" }}>
                            <video
                                src={previewUrl}
                                controls
                                autoPlay
                                style={{ width: "100%", height: "100%", display: "block" }}
                            />
                        </Box>
                    )}
                </Box>
            </Dialog>
        </Box>
    );
}

export default SocialMediaGenerator;
