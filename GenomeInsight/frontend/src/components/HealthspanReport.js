import React, { useEffect, useState } from "react";
import {
  Alert, Box, Card, CardContent, Chip, Container, Grid,
  Skeleton, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer,
  AreaChart, Area,
} from "recharts";
import { healthspanAPI } from "../services/api";
import { staggerChild, WABI_CHART_COLORS } from "../theme/wabiSabi";

function ScoreCard({ label, score, color }) {
  return (
    <Card elevation={0} sx={{ textAlign: "center", py: 2.5 }}>
      <Typography variant="overline" color="text.secondary" display="block">{label}</Typography>
      <Typography
        variant="h3"
        sx={{ fontWeight: 700, color: color || "#5C4B3F", my: 0.5 }}
      >
        {score != null ? Math.round(score) : "—"}
      </Typography>
      <Box
        sx={{
          width: "60%", height: 4, mx: "auto", mt: 1, borderRadius: 2,
          backgroundColor: "rgba(92,75,63,0.06)",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            width: `${Math.min(score || 0, 100)}%`,
            height: "100%",
            borderRadius: 2,
            background: `linear-gradient(90deg, ${color || WABI_CHART_COLORS[0]}, ${color || WABI_CHART_COLORS[1]})`,
            transition: "width 0.6s ease",
          }}
        />
      </Box>
    </Card>
  );
}

export default function HealthspanReport() {
  const [reports, setReports] = useState([]);
  const [latest, setLatest] = useState(null);
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([healthspanAPI.listReports(), healthspanAPI.getZones()])
      .then(([rRes, zRes]) => {
        if (cancelled) return;
        if (rRes.status === "fulfilled") {
          const list = rRes.value.data.reports || rRes.value.data || [];
          setReports(list);
          if (list.length > 0) setLatest(list[0]);
        }
        if (zRes.status === "fulfilled") {
          setZones(zRes.value.data.zones || zRes.value.data || []);
        }
      })
      .catch(() => setError("Failed to load healthspan data."))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={320} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={2}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Grid item xs={6} sm={4} md={2.4} key={i}>
              <Skeleton variant="rounded" height={120} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  const scoreCards = latest
    ? [
        { label: "Overall", score: latest.overall_score, color: WABI_CHART_COLORS[0] },
        { label: "Sleep", score: latest.sleep_score, color: WABI_CHART_COLORS[1] },
        { label: "Activity", score: latest.activity_score, color: WABI_CHART_COLORS[2] },
        { label: "Nutrition", score: latest.nutrition_score, color: WABI_CHART_COLORS[3] },
        { label: "Stress", score: latest.stress_score, color: WABI_CHART_COLORS[4] },
      ]
    : [];

  const trendData = [...reports].reverse().map((r) => ({
    period: r.period_start,
    overall: r.overall_score,
    sleep: r.sleep_score,
    activity: r.activity_score,
  }));

  const zoneBarData = zones.map((z) => ({
    name: z.marker_display_name || z.marker_name,
    current: z.current_value || 0,
    optLow: z.optimal_low,
    optHigh: z.optimal_high,
    status: z.zone_status,
  }));

  const recommendations = latest?.recommendations_json
    ? (() => { try { return JSON.parse(latest.recommendations_json); } catch { return []; } })()
    : [];

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>Healthspan Report</Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 5, maxWidth: "55ch" }}
        >
          Weekly rhythms of well-being — patterns emerging from stillness
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {latest ? (
        <>
          {/* Period header */}
          <Box sx={{ mb: 4, display: "flex", alignItems: "center", gap: 2 }}>
            <Typography variant="h6">
              {latest.period_start} — {latest.period_end}
            </Typography>
            <Chip label={latest.report_type} size="small" variant="outlined" />
            {latest.innerage_snapshot != null && (
              <Chip
                label={`InnerAge: ${latest.innerage_snapshot.toFixed(1)}`}
                size="small"
                sx={{ borderColor: "rgba(139,154,127,0.4)", color: "#576450" }}
                variant="outlined"
              />
            )}
          </Box>

          {/* Score cards */}
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {scoreCards.map((sc) => (
              <Grid item xs={6} sm={4} md={2.4} key={sc.label}>
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
                  <ScoreCard {...sc} />
                </motion.div>
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={3}>
            {/* Score trend */}
            {trendData.length >= 2 && (
              <Grid item xs={12} md={7}>
                <Card elevation={0}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2 }}>Score Trends</Typography>
                    <ResponsiveContainer width="100%" height={260}>
                      <AreaChart data={trendData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(92,75,63,0.08)" />
                        <XAxis dataKey="period" tick={{ fontSize: 10, fontFamily: "Inter" }} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 10, fontFamily: "Inter" }} />
                        <ReTooltip />
                        <Area type="monotone" dataKey="overall" name="Overall" stroke={WABI_CHART_COLORS[0]} fill={WABI_CHART_COLORS[0]} fillOpacity={0.15} strokeWidth={2} />
                        <Area type="monotone" dataKey="sleep" name="Sleep" stroke={WABI_CHART_COLORS[1]} fill={WABI_CHART_COLORS[1]} fillOpacity={0.1} strokeWidth={1.5} />
                        <Area type="monotone" dataKey="activity" name="Activity" stroke={WABI_CHART_COLORS[2]} fill={WABI_CHART_COLORS[2]} fillOpacity={0.1} strokeWidth={1.5} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>
            )}

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <Grid item xs={12} md={5}>
                <Card elevation={0} sx={{ height: "100%" }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2 }}>Recommendations</Typography>
                    <div className="space-y-2">
                      {recommendations.slice(0, 6).map((rec, i) => (
                        <Box
                          key={i}
                          sx={{
                            p: 2, borderRadius: "0.375rem",
                            bgcolor: "rgba(255,255,255,0.4)",
                            border: "1px solid rgba(92,75,63,0.04)",
                          }}
                        >
                          <Box sx={{ display: "flex", gap: 1, mb: 0.5, alignItems: "center" }}>
                            <Typography variant="body2" fontWeight={600}>{rec.title}</Typography>
                            {rec.category && (
                              <Chip label={rec.category} size="small" variant="outlined" sx={{ fontSize: 10 }} />
                            )}
                          </Box>
                          <Typography variant="caption" color="text.secondary">{rec.body}</Typography>
                        </Box>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>

          {/* Optimized Zones bar chart */}
          {zoneBarData.length > 0 && (
            <Card elevation={0} sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>Optimized Biomarker Zones</Typography>
                <ResponsiveContainer width="100%" height={Math.max(zoneBarData.length * 40, 200)}>
                  <BarChart data={zoneBarData} layout="vertical" margin={{ left: 100 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(92,75,63,0.06)" />
                    <XAxis type="number" tick={{ fontSize: 10, fontFamily: "Inter" }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontFamily: '"Crimson Text", serif' }} width={100} />
                    <ReTooltip />
                    <Bar dataKey="current" name="Current Value" fill={WABI_CHART_COLORS[0]} radius={[0, 4, 4, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card elevation={0} sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="body1" color="text.secondary">
            No healthspan reports generated yet. Reports are created weekly from your wearable,
            blood, and microbiome data.
          </Typography>
        </Card>
      )}
    </Container>
  );
}
