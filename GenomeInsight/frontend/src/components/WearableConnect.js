import React, { useEffect, useState, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  IconButton,
  Skeleton,
  Tooltip,
  Typography,
} from "@mui/material";
import WatchIcon from "@mui/icons-material/Watch";
import LinkIcon from "@mui/icons-material/Link";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import SyncIcon from "@mui/icons-material/Sync";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import { wearablesAPI } from "../services/api";

const PROVIDER_ICONS = {
  fitbit: "Fitbit",
  garmin: "Garmin",
  apple_health: "Apple Health",
  oura: "Oura Ring",
  whoop: "WHOOP",
  polar: "Polar",
  suunto: "Suunto",
  withings: "Withings",
  samsung: "Samsung Health",
  coros: "COROS",
};

const STATUS_CONFIG = {
  active: { color: "success", icon: <CheckCircleIcon fontSize="small" /> },
  expired: { color: "warning", icon: <ErrorIcon fontSize="small" /> },
  revoked: { color: "default", icon: <LinkOffIcon fontSize="small" /> },
  error: { color: "error", icon: <ErrorIcon fontSize="small" /> },
};

export default function WearableConnect() {
  const [providers, setProviders] = useState([]);
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [connecting, setConnecting] = useState("");
  const [syncing, setSyncing] = useState("");
  const [disconnectDialog, setDisconnectDialog] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [pRes, cRes] = await Promise.all([
        wearablesAPI.listProviders(),
        wearablesAPI.listConnections(),
      ]);
      setProviders(pRes.data.providers);
      setConnections(cRes.data);
    } catch {
      setError("Failed to load wearable data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Check for OAuth callback params on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const provider = params.get("provider");
    if (code && provider) {
      handleOAuthCallback(code, provider);
      // Clean up URL
      window.history.replaceState({}, "", window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConnect = async (provider) => {
    setConnecting(provider);
    setError("");
    setSuccess("");
    try {
      const { data } = await wearablesAPI.connect(provider);
      if (data.auth_url) {
        // In production, redirect to auth_url
        // For demo/dev, simulate callback
        await handleOAuthCallback("demo-auth-code", provider);
      }
    } catch (err) {
      if (err.response?.status === 409) {
        setError(`Already connected to ${PROVIDER_ICONS[provider] || provider}.`);
      } else {
        setError(err.response?.data?.error || "Connection failed.");
      }
    } finally {
      setConnecting("");
    }
  };

  const handleOAuthCallback = async (code, provider) => {
    try {
      await wearablesAPI.callback(code, provider);
      setSuccess(`Successfully connected to ${PROVIDER_ICONS[provider] || provider}!`);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.error || "OAuth callback failed.");
    }
  };

  const handleDisconnect = async (connectionId) => {
    setDisconnectDialog(null);
    setError("");
    try {
      await wearablesAPI.disconnect(connectionId);
      setSuccess("Device disconnected.");
      fetchData();
    } catch {
      setError("Failed to disconnect device.");
    }
  };

  const handleSync = async (connectionId) => {
    setSyncing(connectionId);
    setError("");
    try {
      await wearablesAPI.triggerSync(connectionId);
      setSuccess("Sync queued. Data will update shortly.");
    } catch (err) {
      setError(err.response?.data?.error || "Sync failed.");
    } finally {
      setSyncing("");
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Skeleton variant="text" width={300} height={50} />
        <Grid container spacing={2} sx={{ mt: 2 }}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Skeleton variant="rounded" height={180} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  const activeConnections = connections.filter((c) => c.status === "active");

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Wearable Devices
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Connect your wearable devices to correlate daily activity, sleep, heart
        rate, and HRV data with your genetic and health profiles.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {/* Active connections */}
      {activeConnections.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Connected Devices
          </Typography>
          <Grid container spacing={2}>
            {activeConnections.map((conn) => {
              const statusCfg = STATUS_CONFIG[conn.status] || STATUS_CONFIG.error;
              return (
                <Grid item xs={12} sm={6} md={4} key={conn.id}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                        <WatchIcon color="primary" />
                        <Typography variant="h6" sx={{ flex: 1 }}>
                          {PROVIDER_ICONS[conn.provider] || conn.provider}
                        </Typography>
                        <Chip
                          icon={statusCfg.icon}
                          label={conn.status}
                          color={statusCfg.color}
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        Connected: {new Date(conn.connected_at).toLocaleDateString()}
                      </Typography>
                      {conn.last_sync_at && (
                        <Typography variant="body2" color="text.secondary">
                          Last sync: {new Date(conn.last_sync_at).toLocaleString()}
                        </Typography>
                      )}
                      <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
                        <Tooltip title="Sync now">
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleSync(conn.id)}
                            disabled={syncing === conn.id}
                          >
                            <SyncIcon
                              sx={syncing === conn.id ? {
                                animation: "spin 1s linear infinite",
                                "@keyframes spin": {
                                  "0%": { transform: "rotate(0deg)" },
                                  "100%": { transform: "rotate(360deg)" },
                                },
                              } : {}}
                            />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Disconnect">
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => setDisconnectDialog(conn)}
                          >
                            <LinkOffIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      )}

      {/* Available providers */}
      <Typography variant="h6" gutterBottom>
        Available Providers
      </Typography>
      <Grid container spacing={2}>
        {providers.map((p) => (
          <Grid item xs={6} sm={4} md={3} key={p.provider}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                opacity: p.connected ? 0.6 : 1,
                transition: "all 0.2s",
                "&:hover": p.connected ? {} : {
                  borderColor: "primary.main",
                  boxShadow: 2,
                },
              }}
            >
              <CardContent>
                <WatchIcon
                  sx={{ fontSize: 40, color: p.connected ? "success.main" : "grey.500", mb: 1 }}
                />
                <Typography variant="subtitle1" fontWeight={600}>
                  {p.display_name}
                </Typography>
                {p.connected ? (
                  <Chip
                    icon={<CheckCircleIcon />}
                    label="Connected"
                    color="success"
                    size="small"
                    sx={{ mt: 1 }}
                  />
                ) : (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<LinkIcon />}
                    onClick={() => handleConnect(p.provider)}
                    disabled={connecting === p.provider}
                    sx={{ mt: 1, textTransform: "none" }}
                  >
                    {connecting === p.provider ? "Connecting..." : "Connect"}
                  </Button>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Disconnect confirmation dialog */}
      <Dialog
        open={!!disconnectDialog}
        onClose={() => setDisconnectDialog(null)}
      >
        <DialogTitle>Disconnect Device</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to disconnect{" "}
            <strong>
              {disconnectDialog && (PROVIDER_ICONS[disconnectDialog.provider] || disconnectDialog.provider)}
            </strong>
            ? This will revoke access tokens and stop data syncing. Your
            existing data will be preserved.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDisconnectDialog(null)}>Cancel</Button>
          <Button
            color="error"
            onClick={() => handleDisconnect(disconnectDialog.id)}
          >
            Disconnect
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
