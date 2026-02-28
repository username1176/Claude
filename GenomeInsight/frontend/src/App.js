import React from "react";
import { BrowserRouter, Routes, Route, Link, Navigate } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  CssBaseline,
  Toolbar,
  Typography,
  ThemeProvider,
  createTheme,
  Container,
} from "@mui/material";
import ScienceIcon from "@mui/icons-material/Science";
import DashboardIcon from "@mui/icons-material/Dashboard";
import BiotechIcon from "@mui/icons-material/Biotech";
import BloodtypeIcon from "@mui/icons-material/Bloodtype";
import WatchIcon from "@mui/icons-material/Watch";
import InsightsIcon from "@mui/icons-material/Insights";
import FingerprintIcon from "@mui/icons-material/Fingerprint";
import LogoutIcon from "@mui/icons-material/Logout";

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

const theme = createTheme({
  palette: {
    primary: { main: "#1565c0" },
    secondary: { main: "#00897b" },
    background: { default: "#f5f7fa" },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: { borderRadius: 8 },
});

function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();

  if (!isAuthenticated) return null;

  return (
    <AppBar position="static" elevation={1} sx={{ bgcolor: "white", color: "text.primary" }}>
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ gap: 1 }}>
          <ScienceIcon color="primary" sx={{ mr: 0.5 }} />
          <Typography
            variant="h6"
            component={Link}
            to="/"
            sx={{
              textDecoration: "none",
              color: "primary.main",
              fontWeight: 700,
              mr: 4,
            }}
          >
            GenomeInsight
          </Typography>

          <Button
            component={Link}
            to="/"
            startIcon={<DashboardIcon />}
            sx={{ textTransform: "none" }}
          >
            Dashboard
          </Button>
          <Button
            component={Link}
            to="/upload-genome"
            startIcon={<BiotechIcon />}
            sx={{ textTransform: "none" }}
          >
            Upload Genome
          </Button>
          <Button
            component={Link}
            to="/upload-blood"
            startIcon={<BloodtypeIcon />}
            sx={{ textTransform: "none" }}
          >
            Blood Test
          </Button>
          <Button
            component={Link}
            to="/upload-epigenetics"
            startIcon={<FingerprintIcon />}
            sx={{ textTransform: "none" }}
          >
            Epigenetics
          </Button>
          <Button
            component={Link}
            to="/wearables"
            startIcon={<WatchIcon />}
            sx={{ textTransform: "none" }}
          >
            Wearables
          </Button>
          <Button
            component={Link}
            to="/insights"
            startIcon={<InsightsIcon />}
            sx={{ textTransform: "none" }}
          >
            Insights
          </Button>

          <Box sx={{ flex: 1 }} />

          <Typography variant="body2" color="text.secondary" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
          <Button
            onClick={logout}
            startIcon={<LogoutIcon />}
            color="inherit"
            sx={{ textTransform: "none" }}
          >
            Sign Out
          </Button>
        </Toolbar>
      </Container>
    </AppBar>
  );
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" /> : <Login />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/" /> : <Register />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload-genome"
        element={
          <ProtectedRoute>
            <GenomeUpload />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload-blood"
        element={
          <ProtectedRoute>
            <BloodUpload />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload-epigenetics"
        element={
          <ProtectedRoute>
            <EpigeneticsUpload />
          </ProtectedRoute>
        }
      />
      <Route
        path="/wearables"
        element={
          <ProtectedRoute>
            <WearableConnect />
          </ProtectedRoute>
        }
      />
      <Route
        path="/insights"
        element={
          <ProtectedRoute>
            <DailyInsights />
          </ProtectedRoute>
        }
      />
      <Route
        path="/report/:analysisId"
        element={
          <ProtectedRoute>
            <Report />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
              <NavBar />
              <AppRoutes />
              <DisclaimerModal />
            </Box>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
