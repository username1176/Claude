import React, { useEffect, useState, useCallback } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Container, Grid,
  Skeleton, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, ResponsiveContainer, ReferenceLine,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from "recharts";
import { healthspanAPI } from "../services/api";
import { staggerChild, WABI_CHART_COLORS } from "../theme/wabiSabi";

function AgeGauge({ biological, chronological }) {
  const delta = biological - chronological;
  const isYounger = delta < 0;
  const color = isYounger ? "#8B9A7F" : delta > 3 ? "#B8726D" : "#C4A882";
  const absD = Math.abs(delta).toFixed(1);

  return (
    <Box sx={{ textAlign: "center", py: 3 }}>
      <Box sx={{ position: "relative", display: "inline-block", mb: 2 }}>
        <svg width="180" height="100" viewBox="0 0 180 100">
          {/* background arc */}
          <path d="M 10 90 A 80 80 0 0 1 170 90" fill="none" stroke="rgba(92,75,63,0.08)" strokeWidth="12" strokeLinecap="round" />
          {/* value arc — proportional fill */}
          <path
            d="M 10 90 A 80 80 0 0 1 170 90"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${Math.min(Math.max((biological / (chronological * 1.5)) * 251, 20), 251)} 251`}
            opacity="0.7"
          />
        </svg>
        <Typography
          variant="h3"
          fontWeight={700}
          sx={{
            position: "absolute", top: "40%", left: "50%",
            transform: "translate(-50%, -50%)", color,
          }}
        >
          {biological.toFixed(1)}
        </Typography>
      </Box>
      <Typography variant="overline" color="text.secondary" display="block">
        Biological Age
      </Typography>
      <Typography variant="body2" sx={{ color, fontWeight: 600, mt: 0.5 }}>
        {isYounger ? `${absD} years younger` : delta === 0 ? "On track" : `${absD} years older`}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
        Chronological: {chronological.toFixed(0)}
      </Typography>
    </Box>
  );
}

function FactorBreakdown({ result }) {
  const factors = [];
  if (result.blood_score != null)
    factors.push({ name: "Blood\nBiomarkers", value: Math.max(result.blood_score, 0), fill: WABI_CHART_COLORS[0] });
  if (result.epigenetic_score != null)
    factors.push({ name: "Epigenetic\nClock", value: Math.max(result.epigenetic_score, 0), fill: WABI_CHART_COLORS[1] });
  if (result.wearable_score != null)
    factors.push({ name: "Wearable\nFitness", value: Math.max(result.wearable_score, 0), fill: WABI_CHART_COLORS[2] });

  if (factors.length < 3) return null;

  const radarData = factors.map((f) => ({
    subject: f.name,
    score: Math.min(f.value, 100),
  }));

  return (
    <Card elevation={0} sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 1, textAlign: "center" }}>Component Scores</Typography>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={radarData}>
          <PolarGrid strokeDasharray="3 3" stroke="rgba(92,75,63,0.1)" />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fontFamily: "Inter", fill: "#7A7267" }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar dataKey="score" stroke={WABI_CHART_COLORS[0]} fill={WABI_CHART_COLORS[0]} fillOpacity={0.2} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export default function InnerAgeDisplay() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await healthspanAPI.getInnerAgeHistory();
      const results = data.results || data || [];
      setHistory(results);
      if (results.length > 0) setLatest(results[0]);
    } catch {
      // No history yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCalculate = async () => {
    setCalculating(true);
    setError("");
    try {
      const { data } = await healthspanAPI.calculateInnerAge({
        use_latest_blood: true,
        use_latest_wearable: true,
      });
      setLatest(data);
      setHistory((prev) => [data, ...prev]);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to calculate InnerAge.");
    } finally {
      setCalculating(false);
    }
  };

  const chartData = [...history]
    .reverse()
    .map((r) => ({
      date: new Date(r.calculated_at).toLocaleDateString(),
      biological: r.biological_age,
      chronological: r.chronological_age,
    }));

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 3 }} />
        <Skeleton variant="rounded" height={300} />
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>InnerAge</Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}
        >
          Your biological age — a measure not of time passed, but of resilience within
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 3 }}>
        <Button
          variant="contained"
          onClick={handleCalculate}
          disabled={calculating}
        >
          {calculating ? "Calculating..." : "Calculate InnerAge"}
        </Button>
      </Box>

      {latest ? (
        <Grid container spacing={3}>
          {/* Main gauge */}
          <Grid item xs={12} md={5}>
            <Card elevation={0}>
              <CardContent>
                <AgeGauge biological={latest.biological_age} chronological={latest.chronological_age} />
                <Box sx={{ display: "flex", justifyContent: "center", gap: 1, mt: 1 }}>
                  <Chip label={`Model: ${latest.model_type}`} size="small" variant="outlined" />
                  {latest.confidence_low != null && (
                    <Chip
                      label={`CI: ${latest.confidence_low.toFixed(1)}–${latest.confidence_high.toFixed(1)}`}
                      size="small"
                      variant="outlined"
                      sx={{ borderColor: "rgba(160,180,194,0.4)" }}
                    />
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Factor breakdown */}
          <Grid item xs={12} md={7}>
            <FactorBreakdown result={latest} />
          </Grid>

          {/* Trend over time */}
          {chartData.length >= 2 && (
            <Grid item xs={12}>
              <Card elevation={0}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Age Trajectory</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(92,75,63,0.08)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fontFamily: "Inter" }} />
                      <ReTooltip />
                      <Line
                        type="monotone"
                        dataKey="biological"
                        name="Biological Age"
                        stroke={WABI_CHART_COLORS[0]}
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: "#FAFAF7", stroke: WABI_CHART_COLORS[0] }}
                      />
                      <Line
                        type="monotone"
                        dataKey="chronological"
                        name="Chronological Age"
                        stroke="#A8A8A8"
                        strokeWidth={1.5}
                        strokeDasharray="6 4"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      ) : (
        <Card elevation={0} sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="body1" color="text.secondary">
            No InnerAge results yet. Click "Calculate InnerAge" to compute your biological age
            from your blood biomarkers, epigenetic data, and wearable metrics.
          </Typography>
        </Card>
      )}
    </Container>
  );
}
