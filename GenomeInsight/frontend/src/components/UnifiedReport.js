import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import RefreshIcon from "@mui/icons-material/Refresh";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import BiotechIcon from "@mui/icons-material/Biotech";
import BloodtypeIcon from "@mui/icons-material/Bloodtype";
import WatchIcon from "@mui/icons-material/Watch";
import BubbleChartIcon from "@mui/icons-material/BubbleChart";
import FingerprintIcon from "@mui/icons-material/Fingerprint";
import InsightsIcon from "@mui/icons-material/Insights";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { analysisAPI } from "../services/api";

const DOMAIN_ICONS = {
  genome: <BiotechIcon />,
  blood: <BloodtypeIcon />,
  wearable: <WatchIcon />,
  microbiome: <BubbleChartIcon />,
  epigenetics: <FingerprintIcon />,
};

const DOMAIN_LABELS = {
  genome: "Genome",
  blood: "Blood Markers",
  wearable: "Wearables",
  microbiome: "Microbiome",
  epigenetics: "Epigenetics",
};

const DOMAIN_COLORS = {
  genome: "#1976d2",
  blood: "#e53935",
  wearable: "#43a047",
  microbiome: "#8e24aa",
  epigenetics: "#fb8c00",
};

const PIE_COLORS = [
  "#1976d2", "#43a047", "#e53935", "#fb8c00", "#8e24aa",
  "#00acc1", "#6d4c41", "#546e7a", "#d81b60", "#7cb342",
];

const CONFIDENCE_COLOR = {
  high: "success",
  medium: "warning",
  low: "default",
};

export default function UnifiedReport() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchAnalysis() {
      setLoading(true);
      setError("");
      try {
        const { data } = await analysisAPI.getDaily();
        if (!cancelled) setAnalysis(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.error ||
              "Failed to load unified analysis. Please try again."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAnalysis();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await analysisAPI.triggerGenerate();
      // Re-fetch after a brief delay
      setTimeout(async () => {
        try {
          const { data } = await analysisAPI.getDaily();
          setAnalysis(data);
        } catch {
          // Ignore — data may not be ready yet
        }
        setRefreshing(false);
      }, 2000);
    } catch {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6, textAlign: "center" }}>
        <CircularProgress size={60} />
        <Typography sx={{ mt: 2 }}>Loading unified analysis...</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/")}
          sx={{ mt: 2 }}
        >
          Back to Dashboard
        </Button>
      </Container>
    );
  }

  const domains = analysis?.domains || {};
  const correlations = analysis?.correlations || [];
  const dailyInsights = analysis?.daily_insights || [];

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/")}
        >
          Dashboard
        </Button>
        <Box sx={{ flex: 1 }} />
        <Typography variant="body2" color="text.secondary">
          {analysis?.analysis_date}
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshIcon />}
          disabled={refreshing}
          onClick={handleRefresh}
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </Box>

      <Typography variant="h4" fontWeight={700} gutterBottom>
        Unified Health Analysis
      </Typography>

      {/* Domain status cards */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {Object.entries(DOMAIN_LABELS).map(([key, label]) => {
          const domain = domains[key];
          const available = domain?.status === "available";
          return (
            <Grid item xs={6} sm={4} md key={key}>
              <Card
                elevation={available ? 2 : 0}
                variant={available ? "elevation" : "outlined"}
                sx={{
                  opacity: available ? 1 : 0.5,
                  borderLeft: `4px solid ${DOMAIN_COLORS[key]}`,
                }}
              >
                <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box sx={{ color: DOMAIN_COLORS[key] }}>
                      {DOMAIN_ICONS[key]}
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={600}>
                        {label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {available ? "Data available" : "No data"}
                      </Typography>
                    </Box>
                    {available ? (
                      <CheckCircleIcon
                        fontSize="small"
                        sx={{ color: DOMAIN_COLORS[key] }}
                      />
                    ) : (
                      <Typography variant="caption" color="text.disabled">
                        --
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Tabs */}
      <Paper elevation={1} sx={{ mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Overview" />
          <Tab label="Correlations" />
          <Tab label="Microbiome" />
          <Tab label="Daily Insights" />
          <Tab label="AI Narrative" />
        </Tabs>
      </Paper>

      {tab === 0 && (
        <OverviewPanel
          domains={domains}
          correlations={correlations}
        />
      )}
      {tab === 1 && <CorrelationsPanel correlations={correlations} />}
      {tab === 2 && <MicrobiomePanel domain={domains.microbiome} />}
      {tab === 3 && <DailyInsightsPanel insights={dailyInsights} />}
      {tab === 4 && (
        <NarrativePanel
          narrative={analysis?.ai_narrative}
          disclaimer={analysis?.disclaimer}
        />
      )}

      {/* Disclaimer */}
      <Paper
        sx={{
          p: 2,
          mt: 4,
          bgcolor: "warning.light",
          borderLeft: "4px solid #ed6c02",
        }}
      >
        <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
          <WarningAmberIcon color="warning" />
          <Typography variant="body2">
            <strong>Disclaimer:</strong>{" "}
            {analysis?.disclaimer ||
              "This report is for informational purposes only and is NOT medical advice."}
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

/* ── Overview Panel ────────────────────────────────────────────────────── */

function OverviewPanel({ domains, correlations }) {
  const availableDomains = Object.entries(domains).filter(
    ([, d]) => d.status === "available"
  );
  const highPriorityCorrelations = correlations
    .filter((c) => c.priority >= 70)
    .slice(0, 5);

  return (
    <Box>
      {/* Domain highlights */}
      <Typography variant="h6" gutterBottom>
        Domain Highlights
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {availableDomains.map(([key, domain]) => (
          <Grid item xs={12} sm={6} key={key}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Box sx={{ color: DOMAIN_COLORS[key] }}>
                    {DOMAIN_ICONS[key]}
                  </Box>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {DOMAIN_LABELS[key]}
                  </Typography>
                </Box>
                {domain.highlights && domain.highlights.length > 0 ? (
                  domain.highlights.map((h, i) => (
                    <Box
                      key={i}
                      sx={{
                        display: "flex",
                        gap: 1,
                        alignItems: "flex-start",
                        mb: 0.5,
                      }}
                    >
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ minWidth: 8 }}
                      >
                        -
                      </Typography>
                      <Typography variant="body2">
                        {typeof h === "string" ? h : h.text || h.label || JSON.stringify(h)}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No highlights available.
                  </Typography>
                )}
                {domain.metrics && Object.keys(domain.metrics).length > 0 && (
                  <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                    {Object.entries(domain.metrics)
                      .slice(0, 4)
                      .map(([mk, mv]) => (
                        <Chip
                          key={mk}
                          label={`${mk.replace(/_/g, " ")}: ${
                            typeof mv === "number" ? mv.toLocaleString() : mv
                          }`}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {availableDomains.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          No data domains are available yet. Upload genome, blood, microbiome,
          or epigenetic data, or connect a wearable to see your unified health
          analysis.
        </Alert>
      )}

      {/* High-priority correlations */}
      {highPriorityCorrelations.length > 0 && (
        <>
          <Typography variant="h6" gutterBottom>
            Top Correlations
          </Typography>
          {highPriorityCorrelations.map((c, i) => (
            <CorrelationCard key={i} correlation={c} />
          ))}
        </>
      )}
    </Box>
  );
}

/* ── Correlations Panel ────────────────────────────────────────────────── */

function CorrelationsPanel({ correlations }) {
  if (!correlations || correlations.length === 0) {
    return (
      <Alert severity="info">
        No cross-domain correlations found. Upload data from multiple sources
        (genome, blood, wearable, microbiome) to discover multi-domain health
        insights.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {correlations.length} correlation{correlations.length !== 1 ? "s" : ""}{" "}
        found across your health data, sorted by priority.
      </Typography>
      {correlations.map((c, i) => (
        <CorrelationCard key={i} correlation={c} />
      ))}
    </Box>
  );
}

/* ── Correlation Card ──────────────────────────────────────────────────── */

function CorrelationCard({ correlation: c }) {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 1,
          }}
        >
          <Typography variant="subtitle1" fontWeight={600}>
            {c.title}
          </Typography>
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Chip
              label={`Priority: ${c.priority}`}
              size="small"
              variant="outlined"
              color={c.priority >= 80 ? "error" : c.priority >= 60 ? "warning" : "default"}
            />
            <Chip
              label={c.confidence}
              size="small"
              color={CONFIDENCE_COLOR[c.confidence] || "default"}
            />
          </Box>
        </Box>

        <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.7 }}>
          {c.body}
        </Typography>

        {/* Data sources */}
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: 1 }}>
          {(c.data_sources || []).map((src) => (
            <Chip
              key={src}
              label={src}
              size="small"
              variant="outlined"
              sx={{
                borderColor: DOMAIN_COLORS[src] || "#9e9e9e",
                color: DOMAIN_COLORS[src] || "#616161",
              }}
            />
          ))}
        </Box>

        {/* Recommendations */}
        {c.recommendations && c.recommendations.length > 0 && (
          <Box sx={{ mt: 1, p: 1.5, bgcolor: "grey.50", borderRadius: 1 }}>
            <Typography
              variant="caption"
              fontWeight={600}
              color="text.secondary"
            >
              Recommendations:
            </Typography>
            {c.recommendations.map((r, i) => (
              <Typography key={i} variant="body2" sx={{ ml: 1 }}>
                - {r}
              </Typography>
            ))}
          </Box>
        )}

        {/* Tags */}
        {c.tags && c.tags.length > 0 && (
          <Box sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
            {c.tags.map((t) => (
              <Chip key={t} label={t} size="small" sx={{ fontSize: 11 }} />
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Microbiome Panel ──────────────────────────────────────────────────── */

function MicrobiomePanel({ domain }) {
  if (!domain || domain.status !== "available") {
    return (
      <Alert severity="info">
        No microbiome data available. Upload a microbiome sample (BIOM, OTU
        table, or FASTQ) to see composition and diversity analysis.
      </Alert>
    );
  }

  const { metrics } = domain;

  // Phyla composition pie chart data
  const phylaData = metrics?.composition?.phylum || metrics?.phylum || [];
  const pieData = Array.isArray(phylaData)
    ? phylaData.map((p) => ({
        name: p.name,
        value: Math.round((p.abundance || 0) * 1000) / 10,
      }))
    : [];

  // Diversity metrics
  const diversity = metrics?.diversity || {};

  // Genus bar chart (top 10)
  const genusData = metrics?.composition?.genus || metrics?.genus || [];
  const barData = Array.isArray(genusData)
    ? genusData
        .sort((a, b) => (b.abundance || 0) - (a.abundance || 0))
        .slice(0, 10)
        .map((g) => ({
          name: g.name,
          abundance: Math.round((g.abundance || 0) * 1000) / 10,
        }))
    : [];

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Diversity metrics */}
        <Grid item xs={12}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Diversity Metrics
            </Typography>
            <Grid container spacing={2}>
              {[
                {
                  label: "Shannon Index",
                  value: diversity.shannon,
                  desc: "Higher = more diverse",
                },
                {
                  label: "Simpson Index",
                  value: diversity.simpson,
                  desc: "Closer to 1 = more even",
                },
                { label: "Chao1", value: diversity.chao1, desc: "Species richness" },
                {
                  label: "Observed OTUs",
                  value: diversity.observed_otus,
                  desc: "Unique taxa found",
                },
              ].map(
                (m) =>
                  m.value != null && (
                    <Grid item xs={6} sm={3} key={m.label}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: "center", py: 1.5 }}>
                          <Typography variant="h5" fontWeight={700} color="secondary">
                            {typeof m.value === "number"
                              ? m.value.toFixed(2)
                              : m.value}
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {m.label}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {m.desc}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  )
              )}
            </Grid>
            {metrics?.enterotype && (
              <Box sx={{ mt: 2 }}>
                <Chip
                  label={`Enterotype: ${metrics.enterotype}`}
                  color="secondary"
                  variant="outlined"
                />
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Phyla composition pie chart */}
        {pieData.length > 0 && (
          <Grid item xs={12} md={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Phylum Composition
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, value }) => `${name} ${value}%`}
                    labelLine
                  >
                    {pieData.map((_, idx) => (
                      <Cell
                        key={idx}
                        fill={PIE_COLORS[idx % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <ReTooltip
                    formatter={(val) => `${val}%`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        )}

        {/* Top genera bar chart */}
        {barData.length > 0 && (
          <Grid item xs={12} md={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Top Genera
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={barData}
                  layout="vertical"
                  margin={{ left: 100 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "Abundance (%)",
                      position: "bottom",
                      fontSize: 12,
                    }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fontStyle: "italic" }}
                    width={95}
                  />
                  <ReTooltip formatter={(val) => `${val}%`} />
                  <Bar dataKey="abundance" radius={[0, 4, 4, 0]}>
                    {barData.map((_, idx) => (
                      <Cell
                        key={idx}
                        fill={PIE_COLORS[idx % PIE_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        )}

        {/* Phyla/genus ratios */}
        {(metrics?.fb_ratio != null || metrics?.firmicutes_bacteroidetes_ratio != null) && (
          <Grid item xs={12}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Key Ratios
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={4}>
                  <Box sx={{ textAlign: "center" }}>
                    <Typography variant="h5" fontWeight={700}>
                      {(
                        metrics.fb_ratio ??
                        metrics.firmicutes_bacteroidetes_ratio ??
                        0
                      ).toFixed(2)}
                    </Typography>
                    <Typography variant="body2">
                      Firmicutes / Bacteroidetes
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Optimal: 1.0 - 3.0
                    </Typography>
                  </Box>
                </Grid>
                {metrics?.proteobacteria_pct != null && (
                  <Grid item xs={6} sm={4}>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h5" fontWeight={700}>
                        {(metrics.proteobacteria_pct * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2">Proteobacteria</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Elevated if &gt;15%
                      </Typography>
                    </Box>
                  </Grid>
                )}
              </Grid>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

/* ── Daily Insights Panel ──────────────────────────────────────────────── */

function DailyInsightsPanel({ insights }) {
  if (!insights || insights.length === 0) {
    return (
      <Alert severity="info">
        No daily insights available for today. Connect a wearable or upload
        data to generate personalized insights.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {insights.length} insight{insights.length !== 1 ? "s" : ""} generated
        for today.
      </Typography>
      <Grid container spacing={2}>
        {insights.map((insight, idx) => (
          <Grid item xs={12} sm={6} key={idx}>
            <Card variant="outlined">
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mb: 1,
                  }}
                >
                  {insight.category === "alert" || insight.insight_type === "alert" ? (
                    <WarningAmberIcon fontSize="small" color="error" />
                  ) : (
                    <InsightsIcon fontSize="small" color="primary" />
                  )}
                  <Typography variant="subtitle2" fontWeight={600}>
                    {insight.title}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {insight.body}
                </Typography>
                {insight.data_sources && insight.data_sources.length > 0 && (
                  <Box
                    sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}
                  >
                    {insight.data_sources.map((src) => (
                      <Chip
                        key={src}
                        label={src}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: 10 }}
                      />
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

/* ── AI Narrative Panel ────────────────────────────────────────────────── */

function NarrativePanel({ narrative, disclaimer }) {
  if (!narrative) {
    return (
      <Alert severity="info">
        No AI narrative available. Upload more data sources to generate a
        comprehensive health narrative.
      </Alert>
    );
  }

  return (
    <Box>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <InsightsIcon color="primary" />
          <Typography variant="h6">AI Health Narrative</Typography>
        </Box>
        <Divider sx={{ mb: 2 }} />
        <Box
          sx={{
            whiteSpace: "pre-wrap",
            fontFamily: "inherit",
            fontSize: 14,
            lineHeight: 1.8,
            "& h1, & h2, & h3": { mt: 3, mb: 1 },
            "& p": { mb: 1, lineHeight: 1.7 },
            "& ul, & ol": { pl: 3, mb: 2 },
            "& li": { mb: 0.5 },
          }}
        >
          {narrative}
        </Box>
      </Paper>
    </Box>
  );
}
