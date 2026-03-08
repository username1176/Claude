import React from "react";
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import { Box, Button, CssBaseline, ThemeProvider, Container } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";

import wabiSabiTheme from "./theme/wabiSabi";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import DisclaimerModal from "./components/DisclaimerModal";
import Login from "./components/Login";
import Register from "./components/Register";
import Dashboard from "./components/Dashboard";
import GenomeUpload from "./components/GenomeUpload";
import BloodUpload from "./components/BloodUpload";
import EpigeneticsUpload from "./components/EpigeneticsUpload";
import WearableConnect from "./components/WearableConnect";
import DailyInsights from "./components/DailyInsights";
import Report from "./components/Report";
import MicrobiomeUpload from "./components/MicrobiomeUpload";
import UnifiedReport from "./components/UnifiedReport";
import WGSUpload from "./components/WGSUpload";
import GenomeBrowser from "./components/GenomeBrowser";
import InnerAgeDisplay from "./components/InnerAgeDisplay";
import HealthspanReport from "./components/HealthspanReport";
import AIChat from "./components/AIChat";
import SubscriptionPage from "./components/SubscriptionPage";

/* ─── Wabi Sabi Navigation ─────────────────────────────────────────────────── */

const NAV_ITEMS = [
  { path: "/", label: "Home" },
  { path: "/upload-genome", label: "Genome" },
  { path: "/upload-blood", label: "Blood" },
  { path: "/upload-epigenetics", label: "Epigenetics" },
  { path: "/upload-microbiome", label: "Microbiome" },
  { path: "/upload-wgs", label: "WGS" },
  { path: "/wearables", label: "Wearables" },
  { path: "/innerage", label: "InnerAge" },
  { path: "/insights", label: "Insights" },
  { path: "/chat", label: "AI Chat" },
  { path: "/unified-report", label: "Report" },
  { path: "/subscription", label: "Plan" },
];

function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) return null;

  return (
    <motion.nav
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
      className="sticky top-0 z-50"
      style={{
        backgroundColor: "rgba(250, 250, 247, 0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(92, 75, 63, 0.06)",
      }}
    >
      <Container maxWidth="lg">
        <div className="flex items-center py-4 gap-6">
          {/* Logo — organic leaf/helix SVG */}
          <Link to="/" className="no-underline flex items-center gap-2 mr-6 group">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="transition-transform duration-500 group-hover:rotate-12">
              <circle cx="14" cy="14" r="12" stroke="#5C4B3F" strokeWidth="1.5" fill="none" opacity="0.6" />
              <path d="M14 4 C18 8, 20 12, 14 24 C8 12, 10 8, 14 4Z" fill="#8B9A7F" opacity="0.4" />
              <circle cx="14" cy="12" r="2.5" fill="#5C4B3F" opacity="0.5" />
            </svg>
            <span className="font-serif text-xl font-semibold tracking-wide" style={{ color: "#5C4B3F" }}>
              GenomeInsight
            </span>
          </Link>

          {/* Desktop navigation links */}
          <div className="hidden md:flex items-center gap-1 flex-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link key={item.path} to={item.path} className="no-underline">
                  <span
                    className="font-serif text-sm px-3 py-1.5 rounded-md transition-all duration-300"
                    style={{
                      color: isActive ? "#5C4B3F" : "#8B7A68",
                      backgroundColor: isActive ? "rgba(92,75,63,0.06)" : "transparent",
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </div>

          {/* User email + sign out */}
          <div className="flex items-center gap-3 ml-auto">
            <span className="hidden sm:inline font-sans text-xs tracking-wider" style={{ color: "#A8A8A8" }}>
              {user?.email}
            </span>
            <Button
              onClick={logout}
              size="small"
              sx={{
                color: "#7A7267",
                fontSize: "0.85rem",
                "&:hover": { backgroundColor: "rgba(92, 75, 63, 0.04)" },
              }}
            >
              Sign Out
            </Button>
          </div>
        </div>

        {/* Mobile nav */}
        <div className="md:hidden flex flex-wrap gap-1 pb-3">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link key={item.path} to={item.path} className="no-underline">
                <span
                  className="font-serif text-xs px-2.5 py-1 rounded-full transition-all duration-300"
                  style={{
                    color: isActive ? "#5C4B3F" : "#8B7A68",
                    backgroundColor: isActive ? "rgba(92,75,63,0.08)" : "rgba(92,75,63,0.03)",
                    fontWeight: isActive ? 600 : 400,
                  }}
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </Container>
    </motion.nav>
  );
}

/* ─── Page transition wrapper ──────────────────────────────────────────────── */

function PageTransition({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  );
}

/* ─── Routes ───────────────────────────────────────────────────────────────── */

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <PageTransition><Login /></PageTransition>} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <PageTransition><Register /></PageTransition>} />
        <Route path="/" element={<ProtectedRoute><PageTransition><Dashboard /></PageTransition></ProtectedRoute>} />
        <Route path="/upload-genome" element={<ProtectedRoute><PageTransition><GenomeUpload /></PageTransition></ProtectedRoute>} />
        <Route path="/upload-blood" element={<ProtectedRoute><PageTransition><BloodUpload /></PageTransition></ProtectedRoute>} />
        <Route path="/upload-epigenetics" element={<ProtectedRoute><PageTransition><EpigeneticsUpload /></PageTransition></ProtectedRoute>} />
        <Route path="/upload-microbiome" element={<ProtectedRoute><PageTransition><MicrobiomeUpload /></PageTransition></ProtectedRoute>} />
        <Route path="/upload-wgs" element={<ProtectedRoute><PageTransition><WGSUpload /></PageTransition></ProtectedRoute>} />
        <Route path="/wearables" element={<ProtectedRoute><PageTransition><WearableConnect /></PageTransition></ProtectedRoute>} />
        <Route path="/insights" element={<ProtectedRoute><PageTransition><DailyInsights /></PageTransition></ProtectedRoute>} />
        <Route path="/report/:analysisId" element={<ProtectedRoute><PageTransition><Report /></PageTransition></ProtectedRoute>} />
        <Route path="/unified-report" element={<ProtectedRoute><PageTransition><UnifiedReport /></PageTransition></ProtectedRoute>} />
        <Route path="/genome-browser" element={<ProtectedRoute><PageTransition><GenomeBrowser /></PageTransition></ProtectedRoute>} />
        <Route path="/innerage" element={<ProtectedRoute><PageTransition><InnerAgeDisplay /></PageTransition></ProtectedRoute>} />
        <Route path="/healthspan" element={<ProtectedRoute><PageTransition><HealthspanReport /></PageTransition></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><PageTransition><AIChat /></PageTransition></ProtectedRoute>} />
        <Route path="/subscription" element={<ProtectedRoute><PageTransition><SubscriptionPage /></PageTransition></ProtectedRoute>} />
        <Route path="/subscription/success" element={<ProtectedRoute><PageTransition><SubscriptionPage /></PageTransition></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AnimatePresence>
  );
}

/* ─── App Root ─────────────────────────────────────────────────────────────── */

export default function App() {
  return (
    <ThemeProvider theme={wabiSabiTheme}>
      <CssBaseline />
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <Box sx={{ minHeight: "100vh", bgcolor: "background.default", position: "relative" }}>
              <NavBar />
              <AppRoutes />
              <DisclaimerModal />

              {/* Subtle footer */}
              <footer style={{ marginTop: "4rem", paddingBottom: "2rem", textAlign: "center" }}>
                <div className="wabi-wave" style={{ maxWidth: "200px", margin: "0 auto 1rem" }} />
                <p className="font-sans text-xs tracking-widest uppercase" style={{ color: "#A8A8A8" }}>
                  GenomeInsight
                </p>
                <p className="font-serif text-xs italic" style={{ color: "#A8917A", marginTop: "0.25rem" }}>
                  Imperfectly perfect health exploration
                </p>
              </footer>
            </Box>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
