import { createTheme } from "@mui/material";

/* ─── Wabi Sabi MUI Theme ──────────────────────────────────────────────────── */

const wabiSabiTheme = createTheme({
  palette: {
    primary: {
      main: "#5C4B3F",
      light: "#7A7267",
      dark: "#3A3632",
      contrastText: "#FAFAF7",
    },
    secondary: {
      main: "#8B9A7F",
      light: "#A7B99D",
      dark: "#576450",
      contrastText: "#FAFAF7",
    },
    error: {
      main: "#B8726D",
      light: "#D4A09C",
    },
    warning: {
      main: "#C4A882",
      light: "#EDE5DC",
    },
    info: {
      main: "#A0B4C2",
      light: "#E0E9EF",
    },
    success: {
      main: "#8B9A7F",
      light: "#E4EBE0",
    },
    background: {
      default: "#F5F5F0",
      paper: "rgba(255, 255, 255, 0.7)",
    },
    text: {
      primary: "#3A3632",
      secondary: "#7A7267",
      disabled: "#A8A8A8",
    },
    divider: "rgba(92, 75, 63, 0.1)",
  },
  typography: {
    fontFamily: '"Crimson Text", "Noto Serif JP", Georgia, serif',
    h1: {
      fontWeight: 600,
      letterSpacing: "0.02em",
      color: "#5C4B3F",
    },
    h2: {
      fontWeight: 600,
      letterSpacing: "0.02em",
      color: "#5C4B3F",
    },
    h3: {
      fontWeight: 600,
      letterSpacing: "0.02em",
      color: "#5C4B3F",
    },
    h4: {
      fontWeight: 600,
      letterSpacing: "0.02em",
      color: "#5C4B3F",
    },
    h5: {
      fontWeight: 600,
      letterSpacing: "0.02em",
      color: "#5C4B3F",
    },
    h6: {
      fontWeight: 600,
      letterSpacing: "0.01em",
      color: "#5C4B3F",
    },
    subtitle1: {
      fontWeight: 500,
      fontSize: "1.05rem",
    },
    body1: {
      lineHeight: 1.8,
      fontSize: "1.05rem",
    },
    body2: {
      lineHeight: 1.7,
      fontSize: "0.95rem",
    },
    caption: {
      fontFamily: 'Inter, system-ui, sans-serif',
      letterSpacing: "0.05em",
      fontSize: "0.78rem",
    },
    button: {
      fontFamily: '"Crimson Text", Georgia, serif',
      textTransform: "none",
      fontWeight: 600,
      letterSpacing: "0.03em",
    },
    overline: {
      fontFamily: 'Inter, system-ui, sans-serif',
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      fontSize: "0.7rem",
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 6,
  },
  shadows: [
    "none",
    "0 1px 3px rgba(92,75,63,0.04), 0 2px 8px rgba(92,75,63,0.06)",
    "0 2px 6px rgba(92,75,63,0.05), 0 4px 16px rgba(92,75,63,0.08)",
    "0 4px 12px rgba(92,75,63,0.06), 0 8px 24px rgba(92,75,63,0.08)",
    ...Array(21).fill("0 4px 12px rgba(92,75,63,0.06), 0 8px 24px rgba(92,75,63,0.08)"),
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: "#F5F5F0",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: "0.375rem",
          padding: "8px 24px",
          transition: "all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)",
        },
        contained: {
          boxShadow: "none",
          "&:hover": {
            boxShadow: "0 2px 8px rgba(92,75,63,0.12)",
          },
        },
        outlined: {
          borderColor: "rgba(92, 75, 63, 0.2)",
          "&:hover": {
            borderColor: "rgba(92, 75, 63, 0.4)",
            backgroundColor: "rgba(92, 75, 63, 0.03)",
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(255, 255, 255, 0.7)",
          backdropFilter: "blur(8px)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(255, 255, 255, 0.6)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(92, 75, 63, 0.06)",
          transition: "all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)",
          "&:hover": {
            boxShadow: "0 4px 16px rgba(92,75,63,0.08)",
            transform: "translateY(-1px)",
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: "0.75rem",
          letterSpacing: "0.03em",
          borderRadius: "999px",
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: "#5C4B3F",
          height: 2,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontFamily: '"Crimson Text", Georgia, serif',
          textTransform: "none",
          fontSize: "1rem",
          letterSpacing: "0.03em",
          minHeight: 52,
          color: "#7A7267",
          "&.Mui-selected": {
            color: "#5C4B3F",
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiInputBase-root": {
            fontFamily: '"Crimson Text", Georgia, serif',
            fontSize: "1.05rem",
          },
          "& .MuiOutlinedInput-root": {
            "& fieldset": {
              borderColor: "rgba(92, 75, 63, 0.15)",
              transition: "border-color 0.3s ease",
            },
            "&:hover fieldset": {
              borderColor: "rgba(92, 75, 63, 0.3)",
            },
            "&.Mui-focused fieldset": {
              borderColor: "#8B9A7F",
              borderWidth: 1,
            },
          },
          "& .MuiInputLabel-root": {
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: "0.85rem",
            letterSpacing: "0.03em",
            color: "#7A7267",
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          fontFamily: '"Crimson Text", Georgia, serif',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: "0.5rem",
          backgroundColor: "#FAFAF7",
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: "0.375rem",
          fontFamily: '"Crimson Text", Georgia, serif',
        },
        standardInfo: {
          backgroundColor: "rgba(160, 180, 194, 0.12)",
          color: "#4D6575",
        },
        standardError: {
          backgroundColor: "rgba(184, 114, 109, 0.12)",
          color: "#8B4F4B",
        },
        standardSuccess: {
          backgroundColor: "rgba(139, 154, 127, 0.12)",
          color: "#3F4A39",
        },
        standardWarning: {
          backgroundColor: "rgba(196, 168, 130, 0.12)",
          color: "#5C4B3F",
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          backgroundColor: "rgba(92, 75, 63, 0.08)",
        },
        bar: {
          borderRadius: 4,
          background: "linear-gradient(90deg, #8B9A7F 0%, #A0B4C2 100%)",
        },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(92, 75, 63, 0.06)",
        },
      },
    },
  },
});

/* ─── Wabi Sabi chart color palette ────────────────────────────────────────── */

export const WABI_CHART_COLORS = [
  "#8B9A7F", // moss
  "#A0B4C2", // mist
  "#C4A882", // clay
  "#B89B8F", // rose-earth
  "#7A7267", // earth-600
  "#5C4B3F", // earth-700
  "#A7B99D", // moss-300
  "#657F92", // mist-500
  "#DFC7AB", // clay-200
  "#A8917A", // earth-400
];

/* ─── Wabi Sabi risk level colors (muted) ──────────────────────────────────── */

export const WABI_RISK_COLORS = {
  low: "#8B9A7F",
  average: "#C4A882",
  elevated: "#B89B8F",
  high: "#B8726D",
};

/* ─── Framer-motion animation variants ────────────────────────────────────── */

export const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] },
};

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.5, ease: "easeOut" },
};

export const mistReveal = {
  initial: { opacity: 0, filter: "blur(8px)" },
  animate: { opacity: 1, filter: "blur(0px)" },
  transition: { duration: 0.8, ease: "easeOut" },
};

export const stagger = (delay = 0.08) => ({
  animate: {
    transition: { staggerChildren: delay },
  },
});

export const staggerChild = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] } },
};

export default wabiSabiTheme;
