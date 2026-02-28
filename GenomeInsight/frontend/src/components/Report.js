import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Container,
  Grid, Paper, Tab, Tabs, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from "recharts";
import { genomeAPI } from "../services/api";
import { WABI_RISK_COLORS, WABI_CHART_COLORS } from "../theme/wabiSabi";

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
      setLoading(true); setError("");
      try {
        let aid = analysisId;
        try { const u = await genomeAPI.getUpload(analysisId); if (u.data?.analysis?.id) aid = u.data.analysis.id; } catch {}
        const [aRes, rRes, recRes] = await Promise.allSettled([
          genomeAPI.getAnalysis(aid), genomeAPI.getRisks(aid), genomeAPI.getRecommendations(aid),
        ]);
        if (cancelled) return;
        if (aRes.status === "fulfilled") setAnalysis(aRes.value.data);
        if (rRes.status === "fulfilled") setRisks(rRes.value.data.risk_categories);
        if (recRes.status === "fulfilled") setRecommendations(recRes.value.data.recommendations || []);
        try { const rep = await genomeAPI.getReport(aid); if (!cancelled) setReport(rep.data); } catch {}
      } catch { if (!cancelled) setError("Failed to load report data."); }
      finally { if (!cancelled) setLoading(false); }
    }
    fetchReport();
    return () => { cancelled = true; };
  }, [analysisId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress size={48} sx={{ color: "#8B9A7F" }} />
        <Typography sx={{ mt: 2, color: "text.secondary", fontStyle: "italic" }}>Gathering insights...</Typography>
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

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Button onClick={() => navigate("/")} sx={{ mb: 2, color: "text.secondary" }}>Back to Dashboard</Button>
        <Typography variant="h4" sx={{ mb: 3 }}>Genome Analysis</Typography>

        {/* Status */}
        {analysis && (
          <Paper elevation={0} sx={{ p: 3, mb: 4 }}>
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={6} sm={3}>
                <Typography variant="overline" color="text.secondary">Status</Typography>
                <Box><Chip label={analysis.status} size="small" variant="outlined" /></Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="overline" color="text.secondary">Variants</Typography>
                <Typography variant="h6">{analysis.variant_count?.toLocaleString() || "—"}</Typography>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="overline" color="text.secondary">Annotated</Typography>
                <Typography variant="h6">{analysis.annotated_variant_count?.toLocaleString() || "—"}</Typography>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Typography variant="overline" color="text.secondary">Completed</Typography>
                <Typography variant="h6">{analysis.completed_at ? new Date(analysis.completed_at).toLocaleDateString() : "—"}</Typography>
              </Grid>
            </Grid>
          </Paper>
        )}

        {analysis && analysis.status !== "complete" && analysis.status !== "error" && (
          <Alert severity="info" sx={{ mb: 3 }}>Analysis is still running ({analysis.status}).</Alert>
        )}

        <Paper elevation={0} sx={{ mb: 3 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
            <Tab label="Risk Overview" /><Tab label="Recommendations" /><Tab label="Full Report" />
          </Tabs>
        </Paper>

        <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          {tab === 0 && <RiskOverview risks={risks} />}
          {tab === 1 && <RecommendationsPanel recommendations={recommendations} />}
          {tab === 2 && <FullReport report={report} />}
        </motion.div>

        {/* Disclaimer */}
        <Box className="wabi-disclaimer" sx={{ mt: 5 }}>
          This report is for informational and educational purposes only. It is not medical advice.
          Genetic associations represent statistical probabilities, not certainties.
          Always consult a qualified healthcare provider before making health decisions.
        </Box>
      </motion.div>
    </Container>
  );
}

function RiskOverview({ risks }) {
  if (!risks || Object.keys(risks).length === 0) return <Alert severity="info">No risk data available.</Alert>;
  const entries = Object.entries(risks).map(([key, val]) => ({
    category: key, label: val.label, score: val.score, level: val.level, key_variants: val.key_variants || [],
  }));
  const radarData = entries.map((e) => ({ subject: e.label.split(" ")[0], score: e.score, fullMark: 10 }));
  const barData = entries.sort((a, b) => b.score - a.score).map((e) => ({ name: e.label, score: e.score, level: e.level }));

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card elevation={0} sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1, fontSize: "1rem" }}>Risk Profile</Typography>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(92,75,63,0.1)" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fontFamily: "Inter" }} />
                <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 10 }} />
                <Radar dataKey="score" stroke="#8B9A7F" fill="#8B9A7F" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card elevation={0} sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1, fontSize: "1rem" }}>Risk Scores</Typography>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 10]} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontFamily: "Inter" }} width={75} />
                <Tooltip />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {barData.map((entry, idx) => <Cell key={idx} fill={WABI_RISK_COLORS[entry.level] || "#A8A8A8"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mt: 2 }}>
        {entries.map((e) => (
          <Grid item xs={12} sm={6} md={4} key={e.category}>
            <Card elevation={0}>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={500}>{e.label}</Typography>
                  <Chip label={e.level} size="small" variant="outlined" />
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <div className="wabi-progress">
                      <div className="wabi-progress-bar" style={{ width: `${(e.score / 10) * 100}%`, background: WABI_RISK_COLORS[e.level] || "#A8A8A8" }} />
                    </div>
                  </Box>
                  <Typography variant="body2" fontWeight={700}>{e.score}/10</Typography>
                </Box>
                {e.key_variants.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    {e.key_variants.slice(0, 3).map((v, i) => (
                      <Typography key={i} variant="caption" display="block" color="text.secondary">
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

function RecommendationsPanel({ recommendations }) {
  if (!recommendations?.length) return <Alert severity="info">No recommendations yet.</Alert>;
  const grouped = {};
  recommendations.forEach((r) => { if (!grouped[r.category]) grouped[r.category] = []; grouped[r.category].push(r); });
  const labels = { diet: "Diet & Nutrition", exercise: "Exercise", supplement: "Supplements", lifestyle: "Lifestyle", pharmacogenomic: "Pharmacogenomics" };

  return (
    <Box>
      {Object.entries(grouped).map(([cat, recs]) => (
        <Box key={cat} sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>{labels[cat] || cat}</Typography>
          <div className="wabi-divider" />
          {recs.map((r) => (
            <Card key={r.id} elevation={0} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={500}>{r.title}</Typography>
                  <Box sx={{ display: "flex", gap: 0.5 }}>
                    <Chip label={`P${r.priority}`} size="small" variant="outlined" />
                    <Chip label={r.confidence} size="small" variant="outlined" />
                  </Box>
                </Box>
                <Typography variant="body2" sx={{ mb: 1, lineHeight: 1.8 }}>{r.body}</Typography>
                {r.evidence_rsids && (
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                    {r.evidence_rsids.split(",").map((rsid) => <Chip key={rsid} label={rsid.trim()} size="small" variant="outlined" />)}
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

function FullReport({ report }) {
  if (!report) return <Alert severity="info">Full report not yet available.</Alert>;
  return (
    <Paper elevation={0} sx={{ p: 4 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
        Generated: {report.generated_at ? new Date(report.generated_at).toLocaleString() : "N/A"}
      </Typography>
      <div className="wabi-divider" />
      <Box sx={{ whiteSpace: "pre-wrap", fontSize: 15, lineHeight: 1.9 }}>
        {report.report}
      </Box>
    </Paper>
  );
}
