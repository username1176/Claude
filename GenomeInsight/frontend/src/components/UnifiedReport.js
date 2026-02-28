import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Container,
  Grid, Paper, Tab, Tabs, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as ReTooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { analysisAPI } from "../services/api";
import { WABI_CHART_COLORS } from "../theme/wabiSabi";

const DOMAIN_LABELS = { genome: "Genome", blood: "Blood", wearable: "Wearables", microbiome: "Microbiome", epigenetics: "Epigenetics" };
const DOMAIN_COLORS = { genome: "#5C4B3F", blood: "#B89B8F", wearable: "#8B9A7F", microbiome: "#A0B4C2", epigenetics: "#C4A882" };

export default function UnifiedReport() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true); setError("");
      try { const { data } = await analysisAPI.getDaily(); if (!cancelled) setAnalysis(data); }
      catch (err) { if (!cancelled) setError(err.response?.data?.error || "Failed to load unified analysis."); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await analysisAPI.triggerGenerate();
      setTimeout(async () => {
        try { const { data } = await analysisAPI.getDaily(); setAnalysis(data); } catch {}
        setRefreshing(false);
      }, 2000);
    } catch { setRefreshing(false); }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress size={48} sx={{ color: "#8B9A7F" }} />
        <Typography sx={{ mt: 2, color: "text.secondary", fontStyle: "italic" }}>Weaving your health tapestry...</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={() => navigate("/")} sx={{ mt: 2 }}>Back to Dashboard</Button>
      </Container>
    );
  }

  const domains = analysis?.domains || {};
  const correlations = analysis?.correlations || [];
  const dailyInsights = analysis?.daily_insights || [];

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
          <Button onClick={() => navigate("/")} sx={{ color: "text.secondary" }}>Dashboard</Button>
          <Box sx={{ flex: 1 }} />
          <Typography variant="caption" color="text.secondary">{analysis?.analysis_date}</Typography>
          <Button variant="outlined" size="small" disabled={refreshing} onClick={handleRefresh}>
            {refreshing ? "Refreshing..." : "Refresh"}
          </Button>
        </Box>

        <Typography variant="h4" sx={{ mb: 4 }}>Unified Health Analysis</Typography>

        {/* Domain status */}
        <Grid container spacing={2} sx={{ mb: 4 }}>
          {Object.entries(DOMAIN_LABELS).map(([key, label]) => {
            const domain = domains[key];
            const available = domain?.status === "available";
            return (
              <Grid item xs={6} sm={4} md key={key}>
                <Card elevation={0} sx={{ opacity: available ? 1 : 0.45, borderLeft: `2px solid ${DOMAIN_COLORS[key]}` }}>
                  <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
                    <Typography variant="overline" sx={{ color: DOMAIN_COLORS[key] }}>{label}</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      {available ? "Data available" : "No data"}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>

        <Paper elevation={0} sx={{ mb: 3 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto">
            <Tab label="Overview" /><Tab label="Correlations" /><Tab label="Microbiome" />
            <Tab label="Daily Insights" /><Tab label="AI Narrative" />
          </Tabs>
        </Paper>

        <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          {tab === 0 && <OverviewPanel domains={domains} correlations={correlations} />}
          {tab === 1 && <CorrelationsPanel correlations={correlations} />}
          {tab === 2 && <MicrobiomePanelView domain={domains.microbiome} />}
          {tab === 3 && <DailyInsightsPanel insights={dailyInsights} />}
          {tab === 4 && <NarrativePanel narrative={analysis?.ai_narrative} />}
        </motion.div>

        <Box className="wabi-disclaimer" sx={{ mt: 5 }}>
          {analysis?.disclaimer || "This report is for informational purposes only and is not medical advice."}
        </Box>
      </motion.div>
    </Container>
  );
}

function OverviewPanel({ domains, correlations }) {
  const available = Object.entries(domains).filter(([, d]) => d.status === "available");
  const top = correlations.filter((c) => c.priority >= 70).slice(0, 5);
  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>Domain Highlights</Typography>
      {available.length === 0 && <Alert severity="info" sx={{ mb: 3 }}>No data domains available yet.</Alert>}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {available.map(([key, domain]) => (
          <Grid item xs={12} sm={6} key={key}>
            <Card elevation={0}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight={500} sx={{ color: DOMAIN_COLORS[key], mb: 1 }}>{DOMAIN_LABELS[key]}</Typography>
                {domain.highlights?.length > 0 ? domain.highlights.map((h, i) => (
                  <Typography key={i} variant="body2" color="text.secondary" sx={{ mb: 0.3 }}>
                    {typeof h === "string" ? h : h.text || h.label || JSON.stringify(h)}
                  </Typography>
                )) : <Typography variant="body2" color="text.secondary">No highlights.</Typography>}
                {domain.metrics && Object.keys(domain.metrics).length > 0 && (
                  <Box sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                    {Object.entries(domain.metrics).slice(0, 4).map(([mk, mv]) => (
                      <Chip key={mk} label={`${mk.replace(/_/g, " ")}: ${typeof mv === "number" ? mv.toLocaleString() : mv}`} size="small" variant="outlined" />
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      {top.length > 0 && (
        <><Typography variant="h6" sx={{ mb: 2 }}>Top Correlations</Typography>{top.map((c, i) => <CorrelationCard key={i} c={c} />)}</>
      )}
    </Box>
  );
}

function CorrelationsPanel({ correlations }) {
  if (!correlations?.length) return <Alert severity="info">No cross-domain correlations found.</Alert>;
  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{correlations.length} correlation{correlations.length !== 1 ? "s" : ""} found.</Typography>
      {correlations.map((c, i) => <CorrelationCard key={i} c={c} />)}
    </Box>
  );
}

function CorrelationCard({ c }) {
  return (
    <Card elevation={0} sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={500}>{c.title}</Typography>
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Chip label={`P${c.priority}`} size="small" variant="outlined" />
            <Chip label={c.confidence} size="small" variant="outlined" />
          </Box>
        </Box>
        <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.8 }}>{c.body}</Typography>
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: 1 }}>
          {(c.data_sources || []).map((src) => <Chip key={src} label={src} size="small" variant="outlined" sx={{ borderColor: DOMAIN_COLORS[src] || "rgba(92,75,63,0.15)", color: DOMAIN_COLORS[src] || "#7A7267" }} />)}
        </Box>
        {c.recommendations?.length > 0 && (
          <Box sx={{ mt: 1.5, p: 2, bgcolor: "rgba(245,245,240,0.5)", borderRadius: "0.375rem" }}>
            <Typography variant="caption" fontWeight={600} color="text.secondary">Recommendations</Typography>
            {c.recommendations.map((r, i) => <Typography key={i} variant="body2" sx={{ ml: 1 }}>- {r}</Typography>)}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function MicrobiomePanelView({ domain }) {
  if (!domain || domain.status !== "available") return <Alert severity="info">No microbiome data available.</Alert>;
  const { metrics } = domain;
  const phylaData = metrics?.composition?.phylum || metrics?.phylum || [];
  const pieData = Array.isArray(phylaData) ? phylaData.map((p) => ({ name: p.name, value: Math.round((p.abundance || 0) * 1000) / 10 })) : [];
  const genusData = metrics?.composition?.genus || metrics?.genus || [];
  const barData = Array.isArray(genusData) ? genusData.sort((a, b) => (b.abundance || 0) - (a.abundance || 0)).slice(0, 10).map((g) => ({ name: g.name, abundance: Math.round((g.abundance || 0) * 1000) / 10 })) : [];
  const diversity = metrics?.diversity || {};

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card elevation={0} sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontSize: "1rem" }}>Diversity</Typography>
            <Grid container spacing={2}>
              {[
                { label: "Shannon", value: diversity.shannon, desc: "Higher = more diverse" },
                { label: "Simpson", value: diversity.simpson, desc: "Closer to 1 = even" },
                { label: "Chao1", value: diversity.chao1, desc: "Richness" },
                { label: "OTUs", value: diversity.observed_otus, desc: "Unique taxa" },
              ].map((m) => m.value != null && (
                <Grid item xs={6} sm={3} key={m.label}>
                  <Box sx={{ textAlign: "center" }}>
                    <Typography variant="h5" sx={{ fontWeight: 700, color: "secondary.main" }}>{typeof m.value === "number" ? m.value.toFixed(2) : m.value}</Typography>
                    <Typography variant="caption" fontWeight={600}>{m.label}</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{m.desc}</Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Card>
        </Grid>
        {pieData.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card elevation={0} sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1, fontSize: "1rem" }}>Phylum</Typography>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={95} innerRadius={40} dataKey="value" nameKey="name" label={({ name, value }) => `${name} ${value}%`} strokeWidth={1} stroke="rgba(250,250,247,0.8)">
                    {pieData.map((_, idx) => <Cell key={idx} fill={WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]} />)}
                  </Pie>
                  <ReTooltip formatter={(val) => `${val}%`} />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Grid>
        )}
        {barData.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card elevation={0} sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1, fontSize: "1rem" }}>Top Genera</Typography>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData} layout="vertical" margin={{ left: 100 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fontStyle: "italic" }} width={95} />
                  <ReTooltip formatter={(val) => `${val}%`} />
                  <Bar dataKey="abundance" radius={[0, 4, 4, 0]}>
                    {barData.map((_, idx) => <Cell key={idx} fill={WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

function DailyInsightsPanel({ insights }) {
  if (!insights?.length) return <Alert severity="info">No daily insights available.</Alert>;
  return (
    <Grid container spacing={2}>
      {insights.map((ins, idx) => (
        <Grid item xs={12} sm={6} key={idx}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={500} sx={{ mb: 0.5 }}>{ins.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>{ins.body}</Typography>
              {ins.data_sources?.length > 0 && (
                <Box sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                  {ins.data_sources.map((src) => <Chip key={src} label={src} size="small" variant="outlined" />)}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

function NarrativePanel({ narrative }) {
  if (!narrative) return <Alert severity="info">No AI narrative available.</Alert>;
  return (
    <Paper elevation={0} sx={{ p: 4 }}>
      <Typography variant="h6" sx={{ mb: 2, fontSize: "1rem" }}>AI Health Narrative</Typography>
      <div className="wabi-divider" />
      <Box sx={{ whiteSpace: "pre-wrap", fontSize: 15, lineHeight: 1.9 }}>{narrative}</Box>
    </Paper>
  );
}
