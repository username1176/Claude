import React, { useEffect, useState, useCallback } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Container,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Grid, Skeleton, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { wearablesAPI } from "../services/api";

const PROVIDER_NAMES = {
  fitbit: "Fitbit", garmin: "Garmin", apple_health: "Apple Health", oura: "Oura Ring",
  whoop: "WHOOP", polar: "Polar", suunto: "Suunto", withings: "Withings",
  samsung: "Samsung Health", coros: "COROS",
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
    setLoading(true); setError("");
    try {
      const [pRes, cRes] = await Promise.all([wearablesAPI.listProviders(), wearablesAPI.listConnections()]);
      setProviders(pRes.data.providers);
      setConnections(cRes.data);
    } catch { setError("Failed to load wearable data."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const provider = params.get("provider");
    if (code && provider) {
      handleOAuthCallback(code, provider);
      window.history.replaceState({}, "", window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConnect = async (provider) => {
    setConnecting(provider); setError(""); setSuccess("");
    try {
      const { data } = await wearablesAPI.connect(provider);
      if (data.auth_url) await handleOAuthCallback("demo-auth-code", provider);
    } catch (err) {
      if (err.response?.status === 409) setError(`Already connected to ${PROVIDER_NAMES[provider] || provider}.`);
      else setError(err.response?.data?.error || "Connection failed.");
    } finally { setConnecting(""); }
  };

  const handleOAuthCallback = async (code, provider) => {
    try {
      await wearablesAPI.callback(code, provider);
      setSuccess(`Connected to ${PROVIDER_NAMES[provider] || provider}!`);
      fetchData();
    } catch (err) { setError(err.response?.data?.error || "OAuth callback failed."); }
  };

  const handleDisconnect = async (connectionId) => {
    setDisconnectDialog(null); setError("");
    try { await wearablesAPI.disconnect(connectionId); setSuccess("Disconnected."); fetchData(); }
    catch { setError("Failed to disconnect."); }
  };

  const handleSync = async (connectionId) => {
    setSyncing(connectionId); setError("");
    try { await wearablesAPI.triggerSync(connectionId); setSuccess("Sync queued."); }
    catch (err) { setError(err.response?.data?.error || "Sync failed."); }
    finally { setSyncing(""); }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={2}>{[1, 2, 3, 4].map((i) => <Grid item xs={12} sm={6} md={3} key={i}><Skeleton variant="rounded" height={160} /></Grid>)}</Grid>
      </Container>
    );
  }

  const active = connections.filter((c) => c.status === "active");

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>Wearable Devices</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          Your daily rhythm, captured — activity, sleep, heart, and breath
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

        {active.length > 0 && (
          <Box sx={{ mb: 5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Connected</Typography>
            <Grid container spacing={2}>
              {active.map((conn) => (
                <Grid item xs={12} sm={6} md={4} key={conn.id}>
                  <Card elevation={0}>
                    <CardContent>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight={500} sx={{ flex: 1 }}>{PROVIDER_NAMES[conn.provider] || conn.provider}</Typography>
                        <Chip label="active" size="small" variant="outlined" sx={{ borderColor: "rgba(139,154,127,0.4)", color: "#576450" }} />
                      </Box>
                      <Typography variant="caption" color="text.secondary">Connected: {new Date(conn.connected_at).toLocaleDateString()}</Typography>
                      {conn.last_sync_at && <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Last sync: {new Date(conn.last_sync_at).toLocaleString()}</Typography>}
                      <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
                        <Button size="small" variant="outlined" disabled={syncing === conn.id} onClick={() => handleSync(conn.id)}>{syncing === conn.id ? "Syncing..." : "Sync"}</Button>
                        <Button size="small" sx={{ color: "error.main" }} onClick={() => setDisconnectDialog(conn)}>Disconnect</Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        <Typography variant="h6" sx={{ mb: 2 }}>Available Providers</Typography>
        <Grid container spacing={2}>
          {providers.map((p) => (
            <Grid item xs={6} sm={4} md={3} key={p.provider}>
              <Card elevation={0} sx={{ textAlign: "center", opacity: p.connected ? 0.5 : 1, "&:hover": p.connected ? {} : { boxShadow: 2 }, transition: "all 0.4s ease" }}>
                <CardContent sx={{ py: 3 }}>
                  <Box sx={{ width: 48, height: 48, mx: "auto", mb: 1.5, borderRadius: "50%", border: "1.5px solid", borderColor: p.connected ? "rgba(139,154,127,0.4)" : "rgba(92,75,63,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Typography variant="body2" sx={{ fontSize: 10, fontFamily: "Inter", letterSpacing: "0.1em", textTransform: "uppercase", color: p.connected ? "#576450" : "#7A7267" }}>{p.provider.slice(0, 2).toUpperCase()}</Typography>
                  </Box>
                  <Typography variant="subtitle2" fontWeight={500}>{p.display_name}</Typography>
                  {p.connected ? (
                    <Chip label="Connected" size="small" variant="outlined" sx={{ mt: 1, borderColor: "rgba(139,154,127,0.3)", color: "#576450" }} />
                  ) : (
                    <Button variant="outlined" size="small" onClick={() => handleConnect(p.provider)} disabled={connecting === p.provider} sx={{ mt: 1 }}>{connecting === p.provider ? "Connecting..." : "Connect"}</Button>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Dialog open={!!disconnectDialog} onClose={() => setDisconnectDialog(null)}>
          <DialogTitle>Disconnect Device</DialogTitle>
          <DialogContent>
            <DialogContentText>Disconnect <strong>{disconnectDialog && (PROVIDER_NAMES[disconnectDialog.provider] || disconnectDialog.provider)}</strong>? Existing data is preserved.</DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDisconnectDialog(null)}>Cancel</Button>
            <Button color="error" onClick={() => handleDisconnect(disconnectDialog.id)}>Disconnect</Button>
          </DialogActions>
        </Dialog>
      </motion.div>
    </Container>
  );
}
