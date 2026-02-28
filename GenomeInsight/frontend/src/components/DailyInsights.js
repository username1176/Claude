import React, { useEffect, useState, useCallback } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Container,
  Grid, Paper, Skeleton, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, Legend, ResponsiveContainer,
} from "recharts";
import { wearablesAPI, insightsAPI } from "../services/api";

const WABI_METRIC_COLORS = {
  steps: "#8B9A7F",
  active_minutes: "#A7B99D",
  total_sleep_hours: "#A0B4C2",
  deep_sleep_hours: "#657F92",
  rem_sleep_hours: "#8B9A7F",
  avg_hr_bpm: "#B89B8F",
  resting_hr_bpm: "#B8726D",
  avg_hrv_ms: "#C4A882",
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
    setLoading(true); setError("");
    try {
      const [insR, latR, hisR] = await Promise.allSettled([
        insightsAPI.getDaily(), wearablesAPI.getLatestData(), wearablesAPI.getData({ days: 14 }),
      ]);
      if (insR.status === "fulfilled") setInsights(insR.value.data.insights || []);
      if (latR.status === "fulfilled") setLatestData(latR.value.data.data || []);
      if (hisR.status === "fulfilled") setTrendData(buildTrendData(hisR.value.data.data || []));
    } catch { setError("Failed to load insights."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleGenerate = async () => {
    setGenerating(true); setError(""); setSuccess("");
    try { await insightsAPI.generate(); setSuccess("Insights generated!"); await fetchData(); }
    catch (err) { setError(err.response?.data?.error || "Failed to generate."); }
    finally { setGenerating(false); }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={3}>{[1, 2, 3].map((i) => <Grid item xs={12} md={4} key={i}><Skeleton variant="rounded" height={160} /></Grid>)}</Grid>
      </Container>
    );
  }

  const activity = latestData.find((d) => d.data_type === "activity");
  const sleep = latestData.find((d) => d.data_type === "sleep");
  const hr = latestData.find((d) => d.data_type === "heart_rate");
  const hrv = latestData.find((d) => d.data_type === "hrv");

  const metrics = [
    { label: "Steps", value: activity?.summary?.steps, fmt: (v) => v.toLocaleString() },
    { label: "Sleep", value: sleep?.summary?.total_sleep_minutes, fmt: (v) => `${Math.floor(v / 60)}h ${v % 60}m` },
    { label: "Resting HR", value: hr?.summary?.resting_hr_bpm || hr?.summary?.avg_hr_bpm, fmt: (v) => `${v} bpm` },
    { label: "HRV", value: hrv?.summary?.avg_hrv_ms, fmt: (v) => `${v} ms` },
  ];

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
          <Typography variant="h4">Daily Insights</Typography>
          <Button variant="outlined" size="small" onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : "Regenerate"}
          </Button>
        </Box>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          Where your biology meets your daily rhythm
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError("")}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess("")}>{success}</Alert>}

        {/* Metric cards */}
        <Grid container spacing={2} sx={{ mb: 4 }}>
          {metrics.map((m) => (
            <Grid item xs={6} sm={3} key={m.label}>
              <Card elevation={0} sx={{ textAlign: "center", py: 2.5 }}>
                <Typography variant="overline" color="text.secondary">{m.label}</Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: "primary.main" }}>
                  {m.value != null ? m.fmt(m.value) : "—"}
                </Typography>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Insights */}
        {insights.length > 0 ? (
          <Box sx={{ mb: 5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Today's Whispers</Typography>
            <Grid container spacing={2}>
              {insights.map((ins, idx) => (
                <Grid item xs={12} md={6} key={ins.id || idx}>
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: idx * 0.06 }}>
                    <Card elevation={0}>
                      <CardContent>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                          <Typography variant="subtitle1" fontWeight={500} sx={{ flex: 1 }}>{ins.title}</Typography>
                          <Chip label={ins.insight_type} size="small" variant="outlined" />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>{ins.body}</Typography>
                        {ins.data_sources?.length > 0 && (
                          <Box sx={{ display: "flex", gap: 0.5, mt: 1.5, flexWrap: "wrap" }}>
                            {ins.data_sources.map((src, i) => <Chip key={i} label={src} size="small" variant="outlined" />)}
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>
                </Grid>
              ))}
            </Grid>
          </Box>
        ) : (
          <Alert severity="info" sx={{ mb: 5 }}>No insights yet. Connect a wearable and click Regenerate.</Alert>
        )}

        {/* Trends */}
        {trendData.length > 1 && (
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>14-Day Rhythms</Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TrendChart title="Steps & Activity" data={trendData} lines={[
                  { key: "steps", color: WABI_METRIC_COLORS.steps, name: "Steps" },
                  { key: "active_minutes", color: WABI_METRIC_COLORS.active_minutes, name: "Active Min", yAxisId: "right" },
                ]} dualAxis />
              </Grid>
              <Grid item xs={12} md={6}>
                <TrendChart title="Sleep" data={trendData} lines={[
                  { key: "total_sleep_hours", color: WABI_METRIC_COLORS.total_sleep_hours, name: "Total (hrs)" },
                  { key: "deep_sleep_hours", color: WABI_METRIC_COLORS.deep_sleep_hours, name: "Deep (hrs)" },
                  { key: "rem_sleep_hours", color: WABI_METRIC_COLORS.rem_sleep_hours, name: "REM (hrs)" },
                ]} areaChart />
              </Grid>
              <Grid item xs={12} md={6}>
                <TrendChart title="Heart Rate" data={trendData} lines={[
                  { key: "avg_hr_bpm", color: WABI_METRIC_COLORS.avg_hr_bpm, name: "Avg HR" },
                  { key: "resting_hr_bpm", color: WABI_METRIC_COLORS.resting_hr_bpm, name: "Resting" },
                ]} />
              </Grid>
              <Grid item xs={12} md={6}>
                <TrendChart title="HRV" data={trendData} lines={[
                  { key: "avg_hrv_ms", color: WABI_METRIC_COLORS.avg_hrv_ms, name: "Avg HRV (ms)" },
                ]} areaChart />
              </Grid>
            </Grid>
          </Box>
        )}
      </motion.div>
    </Container>
  );
}

function TrendChart({ title, data, lines, areaChart, dualAxis }) {
  const Chart = areaChart ? AreaChart : LineChart;
  return (
    <Card elevation={0} sx={{ p: 2 }}>
      <Typography variant="subtitle1" fontWeight={500} sx={{ mb: 1 }}>{title}</Typography>
      <ResponsiveContainer width="100%" height={220}>
        <Chart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: "Inter" }} />
          <YAxis yAxisId="left" tick={{ fontSize: 10, fontFamily: "Inter" }} />
          {dualAxis && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />}
          <ReTooltip />
          <Legend wrapperStyle={{ fontFamily: "Inter", fontSize: 11 }} />
          {lines.map((l) => areaChart ? (
            <Area key={l.key} type="monotone" dataKey={l.key} stroke={l.color} fill={l.color} fillOpacity={0.12} strokeWidth={2} name={l.name} yAxisId={l.yAxisId || "left"} connectNulls />
          ) : (
            <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color} strokeWidth={2} dot={{ r: 2, fill: "#FAFAF7", stroke: l.color }} name={l.name} yAxisId={l.yAxisId || "left"} connectNulls />
          ))}
        </Chart>
      </ResponsiveContainer>
    </Card>
  );
}

function buildTrendData(raw) {
  const byDate = {};
  for (const entry of raw) {
    const d = entry.date;
    if (!byDate[d]) byDate[d] = {};
    const s = entry.summary || {};
    if (entry.data_type === "activity") { byDate[d].steps = s.steps; byDate[d].active_minutes = s.active_minutes; }
    else if (entry.data_type === "sleep") {
      byDate[d].total_sleep_hours = s.total_sleep_minutes ? +(s.total_sleep_minutes / 60).toFixed(1) : null;
      byDate[d].deep_sleep_hours = s.deep_sleep_minutes ? +(s.deep_sleep_minutes / 60).toFixed(1) : null;
      byDate[d].rem_sleep_hours = s.rem_sleep_minutes ? +(s.rem_sleep_minutes / 60).toFixed(1) : null;
    } else if (entry.data_type === "heart_rate") { byDate[d].avg_hr_bpm = s.avg_hr_bpm; byDate[d].resting_hr_bpm = s.resting_hr_bpm; }
    else if (entry.data_type === "hrv") { byDate[d].avg_hrv_ms = s.avg_hrv_ms; }
  }
  return Object.entries(byDate).map(([date, m]) => ({ date, ...m })).sort((a, b) => a.date.localeCompare(b.date));
}
