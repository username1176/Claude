import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Chip, Container, Grid,
  IconButton, Paper, Tab, Tabs, Tooltip, Typography, Alert, Skeleton,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { motion } from "framer-motion";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, ReferenceLine,
  PieChart, Pie, Cell,
} from "recharts";
import { genomeAPI, bloodAPI, epigeneticsAPI, wearablesAPI, insightsAPI, microbiomeAPI } from "../services/api";
import { WABI_CHART_COLORS, staggerChild } from "../theme/wabiSabi";

export default function Dashboard() {
  const [tab, setTab] = useState(0);
  const [genomeUploads, setGenomeUploads] = useState([]);
  const [bloodUploads, setBloodUploads] = useState([]);
  const [bloodTrends, setBloodTrends] = useState(null);
  const [changeAnalysis, setChangeAnalysis] = useState(null);
  const [epiUploads, setEpiUploads] = useState([]);
  const [microbiomeUploads, setMicrobiomeUploads] = useState([]);
  const [wearableConnections, setWearableConnections] = useState([]);
  const [dailyInsights, setDailyInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [gRes, bRes, eRes, mRes, wRes, iRes] = await Promise.allSettled([
        genomeAPI.listUploads(), bloodAPI.listUploads(),
        epigeneticsAPI.listUploads(), microbiomeAPI.listUploads(),
        wearablesAPI.listConnections(), insightsAPI.getDaily(),
      ]);
      if (gRes.status === "fulfilled") setGenomeUploads(gRes.value.data);
      if (bRes.status === "fulfilled") setBloodUploads(bRes.value.data);
      if (eRes.status === "fulfilled") setEpiUploads(eRes.value.data || []);
      if (mRes.status === "fulfilled") setMicrobiomeUploads(mRes.value.data || []);
      if (wRes.status === "fulfilled") setWearableConnections(wRes.value.data || []);
      if (iRes.status === "fulfilled") setDailyInsights(iRes.value.data.insights || []);
      const bData = bRes.status === "fulfilled" ? bRes.value.data : [];
      if (bData.length > 0) {
        const [tRes, cRes] = await Promise.allSettled([bloodAPI.getTrends(), bloodAPI.analyzeChanges()]);
        if (tRes.status === "fulfilled") setBloodTrends(tRes.value.data.trends);
        if (cRes.status === "fulfilled") setChangeAnalysis(cRes.value.data);
      }
    } catch { setError("Failed to load dashboard data."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDeleteGenome = async (id) => {
    try { await genomeAPI.deleteUpload(id); setGenomeUploads((p) => p.filter((u) => u.id !== id)); }
    catch { setError("Failed to delete genome upload."); }
  };
  const handleDeleteBlood = async (id) => {
    try { await bloodAPI.deleteUpload(id); setBloodUploads((p) => p.filter((u) => u.id !== id)); }
    catch { setError("Failed to delete blood upload."); }
  };
  const handleDeleteMicrobiome = async (id) => {
    try { await microbiomeAPI.deleteUpload(id); setMicrobiomeUploads((p) => p.filter((u) => u.id !== id)); }
    catch { setError("Failed to delete microbiome upload."); }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={3}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Grid item xs={6} sm={4} md={2} key={i}>
              <Skeleton variant="rounded" height={100} sx={{ borderRadius: "0.5rem" }} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  const summaryCards = [
    { label: "Genomes", count: genomeUploads.length },
    { label: "Blood Tests", count: bloodUploads.length },
    { label: "Epigenetics", count: epiUploads.length },
    { label: "Microbiome", count: microbiomeUploads.length },
    { label: "Wearables", count: wearableConnections.filter((c) => c.status === "active").length },
    { label: "Insights", count: dailyInsights.length },
  ];

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>Your Health</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 5, maxWidth: "50ch" }}>
          A quiet reflection of your biological landscape
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Summary cards */}
      <Grid container spacing={2} sx={{ mb: 5 }}>
        {summaryCards.map((card, idx) => (
          <Grid item xs={6} sm={4} md={2} key={card.label}>
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: idx * 0.08 }}>
              <Card elevation={0} sx={{ textAlign: "center", py: 2.5, px: 2, borderLeft: idx === 0 ? "2px solid rgba(139,154,127,0.4)" : "none" }}>
                <Typography variant="overline" sx={{ color: "text.secondary", display: "block", mb: 0.5 }}>{card.label}</Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: "primary.main" }}>{card.count}</Typography>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {/* Unified Report link */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.5 }}>
        <Paper elevation={0} sx={{ p: 3, mb: 4, display: "flex", alignItems: "center", gap: 2, cursor: "pointer", "&:hover": { boxShadow: 2 }, transition: "box-shadow 0.4s ease" }} onClick={() => navigate("/unified-report")}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>Unified Health Report</Typography>
            <Typography variant="body2" color="text.secondary">Cross-domain correlations across all your health data</Typography>
          </Box>
          <Chip label="View" variant="outlined" size="small" sx={{ borderColor: "rgba(139,154,127,0.4)", color: "#8B9A7F" }} />
        </Paper>
      </motion.div>

      {/* Daily insights preview */}
      {dailyInsights.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.6 }}>
          <Box sx={{ mb: 4 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <Typography variant="h6">Today's Whispers</Typography>
              <Box sx={{ flex: 1 }} />
              <Chip label="View All" size="small" variant="outlined" onClick={() => navigate("/insights")} sx={{ cursor: "pointer", borderColor: "rgba(92,75,63,0.15)" }} />
            </Box>
            <Grid container spacing={2}>
              {dailyInsights.slice(0, 4).map((insight, idx) => (
                <Grid item xs={12} sm={6} key={insight.id || idx}>
                  <Box sx={{ p: 2, borderRadius: "0.375rem", bgcolor: "rgba(255,255,255,0.4)", border: "1px solid rgba(92,75,63,0.04)" }}>
                    <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>{insight.title}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {insight.body?.slice(0, 100)}{insight.body?.length > 100 ? "..." : ""}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>
        </motion.div>
      )}

      {/* Connected wearables */}
      {wearableConnections.filter((c) => c.status === "active").length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
            <Typography variant="h6">Connected Devices</Typography>
            <Box sx={{ flex: 1 }} />
            <Chip label="Manage" size="small" variant="outlined" onClick={() => navigate("/wearables")} sx={{ cursor: "pointer", borderColor: "rgba(92,75,63,0.15)" }} />
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {wearableConnections.filter((c) => c.status === "active").map((conn) => (
              <Chip key={conn.id} label={conn.provider_display_name || conn.provider} size="small" variant="outlined" sx={{ borderColor: "rgba(139,154,127,0.3)", color: "#576450" }} />
            ))}
          </Box>
        </Box>
      )}

      <div className="wabi-divider" />

      {/* Tabs */}
      <Paper elevation={0} sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Genome" /><Tab label="Blood" /><Tab label="Trends" />
          <Tab label="Changes" /><Tab label="Epigenetics" /><Tab label="Microbiome" />
        </Tabs>
      </Paper>

      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        {tab === 0 && <HistoryPanel uploads={genomeUploads} onDelete={handleDeleteGenome} emptyMsg="No genome uploads yet. Begin with Upload Genome." onViewReport={(id) => navigate(`/report/${id}`)} />}
        {tab === 1 && <HistoryPanel uploads={bloodUploads} onDelete={handleDeleteBlood} emptyMsg="No blood tests uploaded yet." />}
        {tab === 2 && <BloodTrendsPanel trends={bloodTrends} />}
        {tab === 3 && <ChangeAnalysisPanel analysis={changeAnalysis} />}
        {tab === 4 && <HistoryPanel uploads={epiUploads} emptyMsg="No epigenetic data uploaded yet." />}
        {tab === 5 && <MicrobiomePanel uploads={microbiomeUploads} onDelete={handleDeleteMicrobiome} />}
      </motion.div>
    </Container>
  );
}

function HistoryPanel({ uploads, onDelete, onViewReport, emptyMsg }) {
  if (!uploads || uploads.length === 0) return <Alert severity="info">{emptyMsg}</Alert>;
  return (
    <div className="space-y-3">
      {uploads.map((u) => (
        <Card key={u.id} elevation={0}>
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, py: 2 }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={500} noWrap>{u.filename}</Typography>
              <Typography variant="caption" color="text.secondary">
                {u.test_date || new Date(u.uploaded_at).toLocaleDateString()}
                {u.source_service && ` · ${u.source_service}`}{u.data_type && ` · ${u.data_type}`}
                {u.result_count != null && ` · ${u.result_count} markers`}
                {u.file_size_bytes && ` · ${(u.file_size_bytes / 1024).toFixed(0)} KB`}
              </Typography>
            </Box>
            <Chip label={u.status} size="small" variant="outlined" />
            {onViewReport && (
              <Tooltip title="View Report"><IconButton size="small" onClick={() => onViewReport(u.id)} sx={{ color: "text.secondary" }}><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
            )}
            {onDelete && (
              <Tooltip title="Remove"><IconButton size="small" onClick={() => onDelete(u.id)} sx={{ color: "text.disabled" }}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function BloodTrendsPanel({ trends }) {
  if (!trends || Object.keys(trends).length === 0) return <Alert severity="info">Upload at least two blood tests to see trends.</Alert>;
  return (
    <Grid container spacing={3}>
      {Object.entries(trends).map(([key, info], idx) => {
        if (!info.data_points || info.data_points.length < 2) return null;
        const chartData = info.data_points.map((pt) => ({ date: pt.date, value: pt.value }));
        const refLow = info.reference_range?.low;
        const refHigh = info.reference_range?.high;
        return (
          <Grid item xs={12} md={6} key={key}>
            <Card elevation={0}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1.5, gap: 1 }}>
                  <Typography variant="h6" sx={{ fontSize: "1rem" }}>{info.display_name || key}</Typography>
                  <Chip label={info.trend_direction} size="small" variant="outlined" />
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                  {info.unit}{refLow != null && refHigh != null && ` · Ref: ${refLow}–${refHigh}`}
                </Typography>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: "Inter" }} />
                    <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fontFamily: "Inter" }} />
                    <ReTooltip />
                    <Line type="monotone" dataKey="value" stroke={WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3, fill: "#FAFAF7", stroke: WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length] }} />
                    {refLow != null && <ReferenceLine y={refLow} stroke="#C4A882" strokeDasharray="4 4" />}
                    {refHigh != null && <ReferenceLine y={refHigh} stroke="#C4A882" strokeDasharray="4 4" />}
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}

function ChangeAnalysisPanel({ analysis }) {
  if (!analysis) return <Alert severity="info">Upload at least two blood tests to see change analysis.</Alert>;
  const { deltas, genome_insights, summary } = analysis;
  return (
    <Box>
      {summary?.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Key Changes</Typography>
          {summary.map((s, i) => <Typography key={i} variant="body2" sx={{ mb: 0.5, color: "text.secondary" }}>{s}</Typography>)}
        </Box>
      )}
      {deltas?.length > 0 && (
        <Box sx={{ mb: 4, overflowX: "auto" }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Marker Changes</Typography>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Marker", "Previous", "Current", "Change", "Direction"].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid rgba(92,75,63,0.1)", fontFamily: "Inter, sans-serif", fontSize: 11, fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "#7A7267" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deltas.map((d, i) => (
                <tr key={i} style={{ backgroundColor: i % 2 === 0 ? "rgba(250,250,247,0.5)" : "transparent" }}>
                  <td style={{ padding: "8px 12px", fontSize: 14, fontFamily: '"Crimson Text", serif' }}>{d.marker_display_name}</td>
                  <td style={{ padding: "8px 12px", fontSize: 14, color: "#7A7267" }}>{d.previous_value} {d.unit}</td>
                  <td style={{ padding: "8px 12px", fontSize: 14 }}>{d.current_value} {d.unit}</td>
                  <td style={{ padding: "8px 12px", fontSize: 14, color: "#7A7267" }}>{d.percent_change > 0 ? "+" : ""}{d.percent_change}%</td>
                  <td style={{ padding: "8px 12px" }}><Chip label={d.direction} size="small" variant="outlined" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      )}
      {genome_insights?.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>Genome-Correlated Insights</Typography>
          {genome_insights.map((gi, i) => (
            <Box key={i} sx={{ mb: 2, p: 2, bgcolor: "rgba(255,255,255,0.4)", borderRadius: "0.375rem" }}>
              <Box sx={{ display: "flex", gap: 1, mb: 0.5 }}>
                <Chip label={gi.rsid} size="small" variant="outlined" />
                <Chip label={gi.risk_category} size="small" variant="outlined" />
              </Box>
              <Typography variant="body2">{gi.insight}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

function MicrobiomePanel({ uploads, onDelete }) {
  const [composition, setComposition] = useState(null);
  React.useEffect(() => {
    const analyzed = uploads.find((u) => u.status === "analyzed" && u.analysis_id);
    if (!analyzed) return;
    let cancelled = false;
    microbiomeAPI.getComposition(analyzed.analysis_id)
      .then(({ data }) => { if (!cancelled) setComposition(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [uploads]);

  if (!uploads?.length) return <Alert severity="info">No microbiome data uploaded yet.</Alert>;

  const phylaRaw = composition?.composition?.phylum || composition?.phylum || [];
  const pieData = Array.isArray(phylaRaw) ? phylaRaw.map((p) => ({ name: p.name, value: Math.round((p.abundance || 0) * 1000) / 10 })) : [];

  return (
    <Box>
      {pieData.length > 0 && (
        <Card elevation={0} sx={{ mb: 3, p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>Phylum Composition</Typography>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" outerRadius={90} innerRadius={40} dataKey="value" nameKey="name" label={({ name, value }) => `${name} ${value}%`} labelLine strokeWidth={1} stroke="rgba(250,250,247,0.8)">
                {pieData.map((_, idx) => <Cell key={idx} fill={WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]} />)}
              </Pie>
              <ReTooltip formatter={(val) => `${val}%`} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      )}
      <Typography variant="h6" sx={{ mb: 2 }}>Upload History</Typography>
      <div className="space-y-2">
        {uploads.map((u) => (
          <Card key={u.id} elevation={0}>
            <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, py: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight={500}>{u.filename}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {u.sample_type && `${u.sample_type} · `}{new Date(u.uploaded_at).toLocaleDateString()}
                </Typography>
              </Box>
              <Chip label={u.status} size="small" variant="outlined" />
              {onDelete && <Tooltip title="Remove"><IconButton size="small" onClick={() => onDelete(u.id)} sx={{ color: "text.disabled" }}><DeleteIcon fontSize="small" /></IconButton></Tooltip>}
            </CardContent>
          </Card>
        ))}
      </div>
    </Box>
  );
}
