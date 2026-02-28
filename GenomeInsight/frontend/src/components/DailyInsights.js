import React, { useEffect, useState, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import InsightsIcon from "@mui/icons-material/Insights";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import InfoIcon from "@mui/icons-material/Info";
import FavoriteIcon from "@mui/icons-material/Favorite";
import DirectionsWalkIcon from "@mui/icons-material/DirectionsWalk";
import HotelIcon from "@mui/icons-material/Hotel";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { wearablesAPI, insightsAPI } from "../services/api";

const INSIGHT_TYPE_CONFIG = {
  alert: { color: "error", icon: <WarningAmberIcon fontSize="small" /> },
  recommendation: { color: "info", icon: <InfoIcon fontSize="small" /> },
  correlation: { color: "secondary", icon: <InsightsIcon fontSize="small" /> },
  positive: { color: "success", icon: <CheckCircleIcon fontSize="small" /> },
};

const DATA_TYPE_ICONS = {
  activity: <DirectionsWalkIcon />,
  sleep: <HotelIcon />,
  heart_rate: <FavoriteIcon />,
  hrv: <FavoriteIcon />,
};

const METRIC_COLORS = {
  steps: "#1976d2",
  active_minutes: "#43a047",
  calories_burned: "#fb8c00",
  total_sleep_minutes: "#5e35b1",
  deep_sleep_minutes: "#1565c0",
  rem_sleep_minutes: "#00897b",
  avg_hr_bpm: "#e53935",
  resting_hr_bpm: "#c62828",
  avg_hrv_ms: "#6a1b9a",
};

export default function DailyInsights() {
  const [insights, setInsights] = useState([]);
  const [latestData, setLatestData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [insightsRes, latestRes, historyRes] = await Promise.allSettled([
        insightsAPI.getDaily(),
        wearablesAPI.getLatestData(),
        wearablesAPI.getData({ days: 14 }),
      ]);

      if (insightsRes.status === "fulfilled") {
        setInsights(insightsRes.value.data.insights || []);
      }
      if (latestRes.status === "fulfilled") {
        setLatestData(latestRes.value.data.data || []);
      }
      if (historyRes.status === "fulfilled") {
        const raw = historyRes.value.data.data || [];
        setTrendData(buildTrendData(raw));
      }
    } catch {
      setError("Failed to load insights data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    setSuccess("");
    try {
      await insightsAPI.generate();
      setSuccess("Insights generated! Refreshing...");
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to generate insights.");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Skeleton variant="text" width={300} height={50} />
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} md={4} key={i}>
              <Skeleton variant="rounded" height={180} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  // Build summary metrics from latest data
  const activityData = latestData.find((d) => d.data_type === "activity");
  const sleepData = latestData.find((d) => d.data_type === "sleep");
  const hrData = latestData.find((d) => d.data_type === "heart_rate");
  const hrvData = latestData.find((d) => d.data_type === "hrv");

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
        <Typography variant="h4" fontWeight={700}>
          Daily Insights
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshIcon />}
          onClick={handleGenerate}
          disabled={generating}
          sx={{ textTransform: "none" }}
        >
          {generating ? "Generating..." : "Regenerate"}
        </Button>
      </Box>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Cross-domain health insights combining your wearable data, genome, blood
        markers, and epigenetic profiles.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {/* Today's metrics summary */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={6} sm={3}>
          <MetricCard
            icon={<DirectionsWalkIcon />}
            label="Steps"
            value={activityData?.summary?.steps}
            format={(v) => v.toLocaleString()}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <MetricCard
            icon={<HotelIcon />}
            label="Sleep"
            value={sleepData?.summary?.total_sleep_minutes}
            format={(v) => `${Math.floor(v / 60)}h ${v % 60}m`}
            color="#5e35b1"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <MetricCard
            icon={<FavoriteIcon />}
            label="Resting HR"
            value={hrData?.summary?.resting_hr_bpm || hrData?.summary?.avg_hr_bpm}
            format={(v) => `${v} bpm`}
            color="#e53935"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <MetricCard
            icon={<FavoriteIcon />}
            label="HRV"
            value={hrvData?.summary?.avg_hrv_ms}
            format={(v) => `${v} ms`}
            color="#6a1b9a"
          />
        </Grid>
      </Grid>

      {/* Insights cards */}
      {insights.length > 0 ? (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Today's Insights
          </Typography>
          <Grid container spacing={2}>
            {insights.map((insight, idx) => {
              const typeCfg = INSIGHT_TYPE_CONFIG[insight.insight_type] || INSIGHT_TYPE_CONFIG.recommendation;
              return (
                <Grid item xs={12} md={6} key={insight.id || idx}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                        {typeCfg.icon}
                        <Typography variant="subtitle1" fontWeight={600} sx={{ flex: 1 }}>
                          {insight.title}
                        </Typography>
                        <Chip
                          label={insight.insight_type}
                          color={typeCfg.color}
                          size="small"
                        />
                        {insight.confidence && (
                          <Chip
                            label={insight.confidence}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {insight.body}
                      </Typography>
                      {insight.data_sources && insight.data_sources.length > 0 && (
                        <Box sx={{ display: "flex", gap: 0.5, mt: 1, flexWrap: "wrap" }}>
                          {insight.data_sources.map((src, i) => (
                            <Chip key={i} label={src} size="small" variant="outlined" />
                          ))}
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      ) : (
        <Alert severity="info" sx={{ mb: 4 }}>
          No insights yet. Connect a wearable device and click "Regenerate" to
          generate cross-domain health insights.
        </Alert>
      )}

      {/* Trend charts */}
      {trendData.length > 1 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            14-Day Trends
          </Typography>
          <Grid container spacing={3}>
            {/* Activity trend */}
            <Grid item xs={12} md={6}>
              <TrendChart
                title="Steps & Active Minutes"
                data={trendData}
                lines={[
                  { key: "steps", color: METRIC_COLORS.steps, name: "Steps" },
                  { key: "active_minutes", color: METRIC_COLORS.active_minutes, name: "Active Min", yAxisId: "right" },
                ]}
                dualAxis
              />
            </Grid>

            {/* Sleep trend */}
            <Grid item xs={12} md={6}>
              <TrendChart
                title="Sleep Duration"
                data={trendData}
                lines={[
                  { key: "total_sleep_hours", color: METRIC_COLORS.total_sleep_minutes, name: "Total (hrs)" },
                  { key: "deep_sleep_hours", color: METRIC_COLORS.deep_sleep_minutes, name: "Deep (hrs)" },
                  { key: "rem_sleep_hours", color: METRIC_COLORS.rem_sleep_minutes, name: "REM (hrs)" },
                ]}
                areaChart
              />
            </Grid>

            {/* Heart rate trend */}
            <Grid item xs={12} md={6}>
              <TrendChart
                title="Heart Rate"
                data={trendData}
                lines={[
                  { key: "avg_hr_bpm", color: METRIC_COLORS.avg_hr_bpm, name: "Avg HR" },
                  { key: "resting_hr_bpm", color: METRIC_COLORS.resting_hr_bpm, name: "Resting HR" },
                ]}
              />
            </Grid>

            {/* HRV trend */}
            <Grid item xs={12} md={6}>
              <TrendChart
                title="HRV (Heart Rate Variability)"
                data={trendData}
                lines={[
                  { key: "avg_hrv_ms", color: METRIC_COLORS.avg_hrv_ms, name: "Avg HRV (ms)" },
                ]}
                areaChart
              />
            </Grid>
          </Grid>
        </Box>
      )}
    </Container>
  );
}

/* ── Metric summary card ─────────────────────────────────────────────── */

function MetricCard({ icon, label, value, format, color }) {
  return (
    <Card elevation={2}>
      <CardContent sx={{ textAlign: "center", py: 2 }}>
        <Box sx={{ color, mb: 0.5 }}>{icon}</Box>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" fontWeight={700} sx={{ color }}>
          {value != null ? format(value) : "—"}
        </Typography>
      </CardContent>
    </Card>
  );
}

/* ── Trend chart ─────────────────────────────────────────────────────── */

function TrendChart({ title, data, lines, areaChart, dualAxis }) {
  const ChartComponent = areaChart ? AreaChart : LineChart;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        {title}
      </Typography>
      <ResponsiveContainer width="100%" height={240}>
        <ChartComponent data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
          {dualAxis && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />}
          <ReTooltip />
          <Legend />
          {lines.map((line) =>
            areaChart ? (
              <Area
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                fill={line.color}
                fillOpacity={0.15}
                strokeWidth={2}
                name={line.name}
                yAxisId={line.yAxisId || "left"}
                connectNulls
              />
            ) : (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                strokeWidth={2}
                dot={{ r: 3 }}
                name={line.name}
                yAxisId={line.yAxisId || "left"}
                connectNulls
              />
            )
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </Paper>
  );
}

/* ── Build trend data from raw wearable data ─────────────────────────── */

function buildTrendData(rawData) {
  // Group by date
  const byDate = {};
  for (const entry of rawData) {
    const d = entry.date;
    if (!byDate[d]) byDate[d] = {};
    const summary = entry.summary || {};

    if (entry.data_type === "activity") {
      byDate[d].steps = summary.steps;
      byDate[d].active_minutes = summary.active_minutes;
      byDate[d].calories_burned = summary.calories_burned;
    } else if (entry.data_type === "sleep") {
      byDate[d].total_sleep_hours = summary.total_sleep_minutes
        ? +(summary.total_sleep_minutes / 60).toFixed(1)
        : null;
      byDate[d].deep_sleep_hours = summary.deep_sleep_minutes
        ? +(summary.deep_sleep_minutes / 60).toFixed(1)
        : null;
      byDate[d].rem_sleep_hours = summary.rem_sleep_minutes
        ? +(summary.rem_sleep_minutes / 60).toFixed(1)
        : null;
    } else if (entry.data_type === "heart_rate") {
      byDate[d].avg_hr_bpm = summary.avg_hr_bpm;
      byDate[d].resting_hr_bpm = summary.resting_hr_bpm;
    } else if (entry.data_type === "hrv") {
      byDate[d].avg_hrv_ms = summary.avg_hrv_ms;
    }
  }

  return Object.entries(byDate)
    .map(([date, metrics]) => ({ date, ...metrics }))
    .sort((a, b) => a.date.localeCompare(b.date));
}
