import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import { genomeAPI } from "../services/api";

const LEVEL_COLORS = {
  low: "#4caf50",
  average: "#ff9800",
  elevated: "#f44336",
  high: "#b71c1c",
};

const CATEGORY_ICONS = {
  diet: "nutrition",
  exercise: "fitness",
  supplement: "pill",
  lifestyle: "wellness",
  pharmacogenomic: "pharmacy",
};

export default function Report() {
  const { analysisId } = useParams();
  const navigate = useNavigate();

  const [tab, setTab] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [risks, setRisks] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchReport() {
      setLoading(true);
      setError("");
      try {
        // First try to load as analysis ID directly
        let aid = analysisId;

        // It might be an upload_id — try fetching the upload to get the analysis
        try {
          const uploadRes = await genomeAPI.getUpload(analysisId);
          if (uploadRes.data?.analysis?.id) {
            aid = uploadRes.data.analysis.id;
          }
        } catch {
          // Not an upload ID; use as-is
        }

        const [aRes, rRes, recRes] = await Promise.allSettled([
          genomeAPI.getAnalysis(aid),
          genomeAPI.getRisks(aid),
          genomeAPI.getRecommendations(aid),
        ]);

        if (cancelled) return;

        if (aRes.status === "fulfilled") setAnalysis(aRes.value.data);
        if (rRes.status === "fulfilled") setRisks(rRes.value.data.risk_categories);
        if (recRes.status === "fulfilled")
          setRecommendations(recRes.value.data.recommendations || []);

        // Try to load AI report (may 409 if not complete)
        try {
          const repRes = await genomeAPI.getReport(aid);
          if (!cancelled) setReport(repRes.data);
        } catch {
          // Analysis not complete — that's fine
        }
      } catch (err) {
        if (!cancelled) setError("Failed to load report data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchReport();
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6, textAlign: "center" }}>
        <CircularProgress size={60} />
        <Typography sx={{ mt: 2 }}>Loading report...</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/")} sx={{ mt: 2 }}>
          Back to Dashboard
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/")}
        sx={{ mb: 2 }}
      >
        Back to Dashboard
      </Button>

      <Typography variant="h4" fontWeight={700} gutterBottom>
        Genome Analysis Report
      </Typography>

      {/* Status bar */}
      {analysis && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <Typography variant="body2" color="text.secondary">
                Status
              </Typography>
              <Chip
                label={analysis.status}
                color={
                  analysis.status === "complete"
                    ? "success"
                    : analysis.status === "error"
                    ? "error"
                    : "info"
                }
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="body2" color="text.secondary">
                Total Variants
              </Typography>
              <Typography variant="h6">
                {analysis.variant_count?.toLocaleString() || "-"}
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="body2" color="text.secondary">
                Annotated
              </Typography>
              <Typography variant="h6">
                {analysis.annotated_variant_count?.toLocaleString() || "-"}
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="body2" color="text.secondary">
                Completed
              </Typography>
              <Typography variant="h6">
                {analysis.completed_at
                  ? new Date(analysis.completed_at).toLocaleDateString()
                  : "-"}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Analysis pending */}
      {analysis && analysis.status !== "complete" && analysis.status !== "error" && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Analysis is still running ({analysis.status}). Results will appear
          once complete.
        </Alert>
      )}

      {analysis?.status === "error" && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Analysis failed: {analysis.error_message || "Unknown error"}
        </Alert>
      )}

      {/* Tabs */}
      <Paper elevation={1} sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
          <Tab label="Risk Overview" />
          <Tab label="Recommendations" />
          <Tab label="Full Report" />
        </Tabs>
      </Paper>

      {tab === 0 && <RiskOverview risks={risks} />}
      {tab === 1 && <RecommendationsPanel recommendations={recommendations} />}
      {tab === 2 && <FullReport report={report} />}

      {/* Disclaimer */}
      <Paper
        sx={{ p: 2, mt: 4, bgcolor: "warning.light", borderLeft: "4px solid #ed6c02" }}
      >
        <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
          <WarningAmberIcon color="warning" />
          <Typography variant="body2">
            <strong>Disclaimer:</strong> This report is for informational and
            educational purposes only. It is NOT medical advice and should NOT be
            used to diagnose, treat, or prevent any disease. Genetic associations
            represent statistical probabilities, not certainties. Always consult a
            qualified healthcare provider before making health decisions based on
            genetic information.
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

/* ── Risk Overview ──────────────────────────────────────────────────────── */

function RiskOverview({ risks }) {
  if (!risks || Object.keys(risks).length === 0) {
    return (
      <Alert severity="info">
        No risk data available. Analysis may still be running.
      </Alert>
    );
  }

  const entries = Object.entries(risks).map(([key, val]) => ({
    category: key,
    label: val.label,
    score: val.score,
    level: val.level,
    key_variants: val.key_variants || [],
  }));

  // Radar chart data
  const radarData = entries.map((e) => ({
    subject: e.label.split(" ")[0], // Short label for radar
    score: e.score,
    fullMark: 10,
  }));

  // Bar chart data
  const barData = entries
    .sort((a, b) => b.score - a.score)
    .map((e) => ({
      name: e.label,
      score: e.score,
      level: e.level,
    }));

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Radar chart */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Risk Profile
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 10 }} />
                <Radar
                  dataKey="score"
                  stroke="#1976d2"
                  fill="#1976d2"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Bar chart */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Risk Scores
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 10]} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  width={75}
                />
                <Tooltip />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {barData.map((entry, idx) => (
                    <Cell key={idx} fill={LEVEL_COLORS[entry.level] || "#9e9e9e"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Detail cards */}
      <Grid container spacing={2} sx={{ mt: 2 }}>
        {entries.map((e) => (
          <Grid item xs={12} sm={6} md={4} key={e.category}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {e.label}
                  </Typography>
                  <Chip
                    label={e.level}
                    size="small"
                    sx={{
                      bgcolor: LEVEL_COLORS[e.level],
                      color: "#fff",
                      fontWeight: 600,
                    }}
                  />
                </Box>

                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={(e.score / 10) * 100}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        bgcolor: "#e0e0e0",
                        "& .MuiLinearProgress-bar": {
                          bgcolor: LEVEL_COLORS[e.level],
                        },
                      }}
                    />
                  </Box>
                  <Typography variant="body2" fontWeight={700}>
                    {e.score}/10
                  </Typography>
                </Box>

                {e.key_variants.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Key variants:
                    </Typography>
                    {e.key_variants.slice(0, 3).map((v, i) => (
                      <Typography key={i} variant="caption" display="block">
                        {v.rsid} ({v.genotype}) — {v.note}
                      </Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

/* ── Recommendations ────────────────────────────────────────────────────── */

function RecommendationsPanel({ recommendations }) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <Alert severity="info">
        No recommendations available yet. Analysis may still be running.
      </Alert>
    );
  }

  // Group by category
  const grouped = {};
  recommendations.forEach((r) => {
    if (!grouped[r.category]) grouped[r.category] = [];
    grouped[r.category].push(r);
  });

  const categoryLabels = {
    diet: "Diet & Nutrition",
    exercise: "Exercise & Fitness",
    supplement: "Supplements",
    lifestyle: "Lifestyle",
    pharmacogenomic: "Pharmacogenomics",
  };

  const confidenceColor = (c) =>
    c === "high" ? "success" : c === "medium" ? "warning" : "error";

  return (
    <Box>
      {Object.entries(grouped).map(([cat, recs]) => (
        <Box key={cat} sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
            {categoryLabels[cat] || cat}
          </Typography>
          <Divider sx={{ mb: 2 }} />

          {recs.map((r) => (
            <Card key={r.id} variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    mb: 1,
                  }}
                >
                  <Typography variant="h6">{r.title}</Typography>
                  <Box sx={{ display: "flex", gap: 1 }}>
                    <Chip
                      label={`Priority: ${r.priority}`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={r.confidence}
                      size="small"
                      color={confidenceColor(r.confidence)}
                    />
                  </Box>
                </Box>

                <Typography variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  {r.body}
                </Typography>

                {r.evidence_rsids && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Evidence:{" "}
                    </Typography>
                    {r.evidence_rsids.split(",").map((rsid) => (
                      <Chip
                        key={rsid}
                        label={rsid.trim()}
                        size="small"
                        variant="outlined"
                        color="primary"
                        sx={{ mr: 0.5 }}
                      />
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      ))}
    </Box>
  );
}

/* ── Full Report ────────────────────────────────────────────────────────── */

function FullReport({ report }) {
  if (!report) {
    return (
      <Alert severity="info">
        The full AI-generated report is not yet available. Analysis may still
        be running.
      </Alert>
    );
  }

  return (
    <Box>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Generated: {report.generated_at
            ? new Date(report.generated_at).toLocaleString()
            : "N/A"}
        </Typography>
        <Divider sx={{ mb: 2 }} />
        {/* Render the report as pre-formatted markdown-ish text */}
        <Box
          sx={{
            "& h1, & h2, & h3": { mt: 3, mb: 1 },
            "& p": { mb: 1, lineHeight: 1.7 },
            "& ul, & ol": { pl: 3, mb: 2 },
            "& li": { mb: 0.5 },
            whiteSpace: "pre-wrap",
            fontFamily: "inherit",
            fontSize: 14,
            lineHeight: 1.8,
          }}
        >
          {report.report}
        </Box>
      </Paper>
    </Box>
  );
}
