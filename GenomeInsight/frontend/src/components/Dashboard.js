import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  Alert,
  Skeleton,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import DescriptionIcon from "@mui/icons-material/Description";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import VisibilityIcon from "@mui/icons-material/Visibility";
import WatchIcon from "@mui/icons-material/Watch";
import BiotechIcon from "@mui/icons-material/Biotech";
import InsightsIcon from "@mui/icons-material/Insights";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { genomeAPI, bloodAPI, epigeneticsAPI, wearablesAPI, insightsAPI } from "../services/api";

const RISK_COLORS = { low: "#4caf50", average: "#ff9800", elevated: "#f44336", high: "#b71c1c" };
const CHART_COLORS = [
  "#1976d2", "#43a047", "#e53935", "#fb8c00", "#8e24aa",
  "#00acc1", "#6d4c41", "#546e7a",
];

export default function Dashboard() {
  const [tab, setTab] = useState(0);
  const [genomeUploads, setGenomeUploads] = useState([]);
  const [bloodUploads, setBloodUploads] = useState([]);
  const [bloodTrends, setBloodTrends] = useState(null);
  const [changeAnalysis, setChangeAnalysis] = useState(null);
  const [epiUploads, setEpiUploads] = useState([]);
  const [wearableConnections, setWearableConnections] = useState([]);
  const [dailyInsights, setDailyInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [gRes, bRes, eRes, wRes, iRes] = await Promise.allSettled([
        genomeAPI.listUploads(),
        bloodAPI.listUploads(),
        epigeneticsAPI.listUploads(),
        wearablesAPI.listConnections(),
        insightsAPI.getDaily(),
      ]);
      if (gRes.status === "fulfilled") setGenomeUploads(gRes.value.data);
      if (bRes.status === "fulfilled") setBloodUploads(bRes.value.data);
      if (eRes.status === "fulfilled") setEpiUploads(eRes.value.data || []);
      if (wRes.status === "fulfilled") setWearableConnections(wRes.value.data || []);
      if (iRes.status === "fulfilled") setDailyInsights(iRes.value.data.insights || []);

      // Fetch blood trends if there are uploads
      const bData = bRes.status === "fulfilled" ? bRes.value.data : [];
      if (bData.length > 0) {
        const [tRes, cRes] = await Promise.allSettled([
          bloodAPI.getTrends(),
          bloodAPI.analyzeChanges(),
        ]);
        if (tRes.status === "fulfilled") setBloodTrends(tRes.value.data.trends);
        if (cRes.status === "fulfilled") setChangeAnalysis(cRes.value.data);
      }
    } catch (err) {
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDeleteGenome = async (id) => {
    try {
      await genomeAPI.deleteUpload(id);
      setGenomeUploads((prev) => prev.filter((u) => u.id !== id));
    } catch {
      setError("Failed to delete genome upload.");
    }
  };

  const handleDeleteBlood = async (id) => {
    try {
      await bloodAPI.deleteUpload(id);
      setBloodUploads((prev) => prev.filter((u) => u.id !== id));
    } catch {
      setError("Failed to delete blood upload.");
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Skeleton variant="text" width={300} height={50} />
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} md={4} key={i}>
              <Skeleton variant="rounded" height={160} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Dashboard
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Summary cards */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Genomes
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {genomeUploads.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Blood Tests
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {bloodUploads.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Epigenetics
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {epiUploads.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Wearables
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {wearableConnections.filter((c) => c.status === "active").length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Markers
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {bloodTrends ? Object.keys(bloodTrends).length : 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Insights
              </Typography>
              <Typography variant="h4" fontWeight={700}>
                {dailyInsights.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Daily insights summary */}
      {dailyInsights.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
            <InsightsIcon color="primary" />
            <Typography variant="h6">Today's Insights</Typography>
            <Box sx={{ flex: 1 }} />
            <Chip
              label={`${dailyInsights.filter((i) => i.insight_type === "alert").length} alerts`}
              color="error"
              size="small"
              variant="outlined"
              sx={{ display: dailyInsights.some((i) => i.insight_type === "alert") ? "flex" : "none" }}
            />
            <Chip
              label="View All"
              size="small"
              color="primary"
              variant="outlined"
              onClick={() => navigate("/insights")}
              sx={{ cursor: "pointer" }}
            />
          </Box>
          <Grid container spacing={1}>
            {dailyInsights.slice(0, 4).map((insight, idx) => (
              <Grid item xs={12} sm={6} key={insight.id || idx}>
                <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start", p: 1, borderRadius: 1, bgcolor: "grey.50" }}>
                  {insight.insight_type === "alert" ? (
                    <WarningAmberIcon fontSize="small" color="error" />
                  ) : (
                    <CheckCircleIcon fontSize="small" color="success" />
                  )}
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      {insight.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {insight.body?.slice(0, 100)}{insight.body?.length > 100 ? "..." : ""}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Wearable connections summary */}
      {wearableConnections.filter((c) => c.status === "active").length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
            <WatchIcon color="primary" />
            <Typography variant="h6">Connected Wearables</Typography>
            <Box sx={{ flex: 1 }} />
            <Chip
              label="Manage"
              size="small"
              color="primary"
              variant="outlined"
              onClick={() => navigate("/wearables")}
              sx={{ cursor: "pointer" }}
            />
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {wearableConnections
              .filter((c) => c.status === "active")
              .map((conn) => (
                <Chip
                  key={conn.id}
                  icon={<CheckCircleIcon />}
                  label={conn.provider_display_name || conn.provider}
                  color="success"
                  variant="outlined"
                  size="small"
                />
              ))}
          </Box>
        </Paper>
      )}

      {/* Tabs */}
      <Paper elevation={1} sx={{ mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Genome History" />
          <Tab label="Blood History" />
          <Tab label="Blood Trends" />
          <Tab label="Change Analysis" />
          <Tab label="Epigenetics" />
        </Tabs>
      </Paper>

      {/* Tab panels */}
      {tab === 0 && (
        <GenomeHistoryPanel
          uploads={genomeUploads}
          onDelete={handleDeleteGenome}
          onViewReport={(analysisId) => navigate(`/report/${analysisId}`)}
        />
      )}
      {tab === 1 && (
        <BloodHistoryPanel
          uploads={bloodUploads}
          onDelete={handleDeleteBlood}
        />
      )}
      {tab === 2 && <BloodTrendsPanel trends={bloodTrends} />}
      {tab === 3 && <ChangeAnalysisPanel analysis={changeAnalysis} />}
      {tab === 4 && <EpigeneticsPanel uploads={epiUploads} navigate={navigate} />}
    </Container>
  );
}

/* ── Genome History ─────────────────────────────────────────────────────── */

function GenomeHistoryPanel({ uploads, onDelete, onViewReport }) {
  if (uploads.length === 0) {
    return (
      <Alert severity="info">
        No genome uploads yet. Go to <strong>Upload Genome</strong> to get started.
      </Alert>
    );
  }

  return (
    <Grid container spacing={2}>
      {uploads.map((u) => (
        <Grid item xs={12} key={u.id}>
          <Card variant="outlined">
            <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <DescriptionIcon color="primary" />
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  {u.filename}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Source: {u.source_service} | Uploaded:{" "}
                  {new Date(u.uploaded_at).toLocaleDateString()} |{" "}
                  {(u.file_size_bytes / 1024).toFixed(0)} KB
                </Typography>
              </Box>
              <Chip
                label={u.status}
                color={u.status === "uploaded" ? "info" : "default"}
                size="small"
              />
              <Tooltip title="View Report">
                <IconButton
                  color="primary"
                  onClick={() => {
                    // Navigate to report — we need the analysis_id from upload detail
                    onViewReport(u.id);
                  }}
                >
                  <VisibilityIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Delete">
                <IconButton color="error" onClick={() => onDelete(u.id)}>
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

/* ── Blood History ──────────────────────────────────────────────────────── */

function BloodHistoryPanel({ uploads, onDelete }) {
  if (uploads.length === 0) {
    return (
      <Alert severity="info">
        No blood tests uploaded yet. Go to <strong>Upload Blood Test</strong> to add one.
      </Alert>
    );
  }

  return (
    <Grid container spacing={2}>
      {uploads.map((u) => (
        <Grid item xs={12} key={u.id}>
          <Card variant="outlined">
            <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <DescriptionIcon color="secondary" />
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  {u.filename}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Test date: {u.test_date}
                  {u.lab_name && ` | Lab: ${u.lab_name}`} |{" "}
                  {u.result_count} markers
                </Typography>
              </Box>
              <Chip
                label={u.status}
                color={u.status === "parsed" ? "success" : "info"}
                size="small"
              />
              <Tooltip title="Delete">
                <IconButton color="error" onClick={() => onDelete(u.id)}>
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

/* ── Blood Trends (charts) ──────────────────────────────────────────────── */

function BloodTrendsPanel({ trends }) {
  if (!trends || Object.keys(trends).length === 0) {
    return (
      <Alert severity="info">
        Upload at least two blood tests to see trends over time.
      </Alert>
    );
  }

  const markerEntries = Object.entries(trends);

  return (
    <Grid container spacing={3}>
      {markerEntries.map(([key, info], idx) => {
        if (!info.data_points || info.data_points.length < 2) return null;

        const chartData = info.data_points.map((pt) => ({
          date: pt.date,
          value: pt.value,
        }));

        const refLow = info.reference_range?.low;
        const refHigh = info.reference_range?.high;

        const TrendIcon =
          info.trend_direction === "improving"
            ? TrendingDownIcon
            : info.trend_direction === "worsening"
            ? TrendingUpIcon
            : TrendingFlatIcon;

        const trendColor =
          info.trend_direction === "improving"
            ? "success"
            : info.trend_direction === "worsening"
            ? "error"
            : "default";

        return (
          <Grid item xs={12} md={6} key={key}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1, gap: 1 }}>
                  <Typography variant="h6">
                    {info.display_name || key}
                  </Typography>
                  <Chip
                    icon={<TrendIcon />}
                    label={info.trend_direction}
                    color={trendColor}
                    size="small"
                    variant="outlined"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Unit: {info.unit}
                  {refLow != null && refHigh != null && (
                    <> | Ref: {refLow} - {refHigh}</>
                  )}
                </Typography>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
                    <ReTooltip />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    {refLow != null && (
                      <ReferenceLine
                        y={refLow}
                        stroke="#aaa"
                        strokeDasharray="4 4"
                        label={{ value: "Low", fontSize: 10 }}
                      />
                    )}
                    {refHigh != null && (
                      <ReferenceLine
                        y={refHigh}
                        stroke="#aaa"
                        strokeDasharray="4 4"
                        label={{ value: "High", fontSize: 10 }}
                      />
                    )}
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

/* ── Change Analysis ────────────────────────────────────────────────────── */

function ChangeAnalysisPanel({ analysis }) {
  if (!analysis) {
    return (
      <Alert severity="info">
        Upload at least two blood tests to see change analysis with genome insights.
      </Alert>
    );
  }

  const { deltas, genome_insights, summary } = analysis;

  return (
    <Box>
      {/* Summary */}
      {summary && summary.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Key Changes
          </Typography>
          {summary.map((s, i) => (
            <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>
              {s}
            </Typography>
          ))}
        </Paper>
      )}

      {/* Deltas table */}
      {deltas && deltas.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Marker Changes
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Marker", "Previous", "Current", "Change", "Direction", "Improved"].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "8px 12px",
                          borderBottom: "2px solid #e0e0e0",
                          fontSize: 13,
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {deltas.map((d, i) => (
                  <tr
                    key={i}
                    style={{
                      backgroundColor: i % 2 === 0 ? "#fafafa" : "#fff",
                    }}
                  >
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      {d.marker_display_name}
                    </td>
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      {d.previous_value} {d.unit}
                    </td>
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      {d.current_value} {d.unit}
                    </td>
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      {d.percent_change > 0 ? "+" : ""}
                      {d.percent_change}%
                    </td>
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      <Chip
                        label={d.direction}
                        size="small"
                        color={
                          d.direction === "decreased"
                            ? "info"
                            : d.direction === "increased"
                            ? "warning"
                            : "default"
                        }
                      />
                    </td>
                    <td style={{ padding: "6px 12px", fontSize: 13 }}>
                      {d.improved === true
                        ? "Yes"
                        : d.improved === false
                        ? "No"
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Box>
        </Paper>
      )}

      {/* Genome insights */}
      {genome_insights && genome_insights.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Genome-Correlated Insights
          </Typography>
          {genome_insights.map((gi, i) => (
            <Box key={i} sx={{ mb: 2 }}>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.5 }}>
                <Chip label={gi.rsid} size="small" color="primary" variant="outlined" />
                <Chip label={gi.risk_category} size="small" />
              </Box>
              <Typography variant="body2">{gi.insight}</Typography>
              {i < genome_insights.length - 1 && <Divider sx={{ mt: 1.5 }} />}
            </Box>
          ))}
        </Paper>
      )}
    </Box>
  );
}

/* ── Epigenetics Panel ─────────────────────────────────────────────────── */

function EpigeneticsPanel({ uploads, navigate }) {
  if (!uploads || uploads.length === 0) {
    return (
      <Alert severity="info">
        No epigenetic data uploaded yet. Go to{" "}
        <strong>Upload Epigenetics</strong> to add histone or methylation data.
      </Alert>
    );
  }

  return (
    <Grid container spacing={2}>
      {uploads.map((u) => (
        <Grid item xs={12} key={u.id}>
          <Card variant="outlined">
            <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <BiotechIcon color="secondary" />
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  {u.filename}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Type: {u.data_type}
                  {u.assay_type && ` | Assay: ${u.assay_type}`}
                  {u.tissue_type && ` | Tissue: ${u.tissue_type}`}
                  {" | "}Uploaded: {new Date(u.uploaded_at).toLocaleDateString()}
                </Typography>
              </Box>
              <Chip
                label={u.status}
                color={u.status === "analyzed" ? "success" : "info"}
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
