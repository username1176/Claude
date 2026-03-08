import React, { useState, useEffect } from "react";
import {
  Alert, Box, Card, CardContent, Chip, Container, FormControl,
  InputLabel, MenuItem, Select, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { staggerChild, WABI_CHART_COLORS } from "../theme/wabiSabi";
import { wgsAPI } from "../services/api";

/**
 * Simplified genome browser / variant viewer.
 *
 * When @jbrowse/react-linear-genome-view is installed it will be used;
 * otherwise a lightweight table-based variant explorer is rendered.
 */

let JBrowseLinearGenomeView = null;
let createViewState = null;
try {
  const jb = require("@jbrowse/react-linear-genome-view");
  JBrowseLinearGenomeView = jb.JBrowseLinearGenomeView;
  createViewState = jb.createViewState;
} catch {
  // JBrowse not installed — fallback to table viewer
}

const CHROMOSOMES = [
  "All", ...Array.from({ length: 22 }, (_, i) => `chr${i + 1}`), "chrX", "chrY",
];

function FallbackVariantViewer({ variants }) {
  const [chrFilter, setChrFilter] = useState("All");
  const filtered = chrFilter === "All"
    ? variants
    : variants.filter((v) => v.chromosome === chrFilter);

  return (
    <Box>
      <Box sx={{ display: "flex", gap: 2, mb: 3, alignItems: "center" }}>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Chromosome</InputLabel>
          <Select value={chrFilter} label="Chromosome" onChange={(e) => setChrFilter(e.target.value)}>
            {CHROMOSOMES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
          </Select>
        </FormControl>
        <Typography variant="caption" color="text.secondary">
          {filtered.length} variant{filtered.length !== 1 ? "s" : ""} shown
        </Typography>
      </Box>

      {filtered.length === 0 ? (
        <Alert severity="info">No variants found for this filter.</Alert>
      ) : (
        <Box sx={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["rsID", "Chr", "Position", "Ref", "Alt", "Gene", "Significance"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left", padding: "10px 12px",
                      borderBottom: "1px solid rgba(92,75,63,0.1)",
                      fontFamily: "Inter, sans-serif", fontSize: 11,
                      fontWeight: 500, letterSpacing: "0.08em",
                      textTransform: "uppercase", color: "#7A7267",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((v, i) => (
                <tr key={v.rsid || i} style={{ backgroundColor: i % 2 === 0 ? "rgba(250,250,247,0.5)" : "transparent" }}>
                  <td style={{ padding: "8px 12px", fontSize: 14, fontFamily: '"Crimson Text", serif' }}>
                    {v.rsid || "—"}
                  </td>
                  <td style={{ padding: "8px 12px", fontSize: 13, color: "#7A7267" }}>{v.chromosome}</td>
                  <td style={{ padding: "8px 12px", fontSize: 13, color: "#7A7267" }}>{v.position?.toLocaleString()}</td>
                  <td style={{ padding: "8px 12px", fontSize: 13 }}>{v.ref_allele}</td>
                  <td style={{ padding: "8px 12px", fontSize: 13 }}>{v.alt_allele}</td>
                  <td style={{ padding: "8px 12px", fontSize: 13, color: "#576450" }}>{v.gene || "—"}</td>
                  <td style={{ padding: "8px 12px" }}>
                    <Chip
                      label={v.clinical_significance || "unknown"}
                      size="small"
                      variant="outlined"
                      sx={{
                        borderColor: v.clinical_significance === "pathogenic"
                          ? "rgba(184,114,109,0.4)"
                          : "rgba(92,75,63,0.15)",
                        color: v.clinical_significance === "pathogenic" ? "#B8726D" : "#7A7267",
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length > 100 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
              Showing 100 of {filtered.length} variants.
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
}

export default function GenomeBrowser() {
  const [uploads, setUploads] = useState([]);
  const [selectedUpload, setSelectedUpload] = useState("");
  const [ancestryData, setAncestryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    wgsAPI.listUploads()
      .then(({ data }) => {
        if (!cancelled) {
          const list = data.uploads || data || [];
          setUploads(list);
          if (list.length > 0) setSelectedUpload(list[0].id);
        }
      })
      .catch(() => setError("Failed to load WGS uploads."))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedUpload) return;
    let cancelled = false;
    wgsAPI.getAncestryReport(selectedUpload)
      .then(({ data }) => { if (!cancelled) setAncestryData(data); })
      .catch(() => { if (!cancelled) setAncestryData(null); });
    return () => { cancelled = true; };
  }, [selectedUpload]);

  const variants = ancestryData?.variants || ancestryData?.simulated_variants || [];

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>Genome Browser</Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 5, maxWidth: "50ch" }}
        >
          Explore your genomic variants — each imperfection telling a story
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {uploads.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <FormControl size="small" sx={{ minWidth: 300 }}>
            <InputLabel>WGS Upload</InputLabel>
            <Select value={selectedUpload} label="WGS Upload" onChange={(e) => setSelectedUpload(e.target.value)}>
              {uploads.map((u) => (
                <MenuItem key={u.id} value={u.id}>
                  {u.original_filename || u.id} — {u.status}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}

      {/* Ancestry summary */}
      {ancestryData?.ancestry && (
        <Card elevation={0} sx={{ mb: 4, p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Ancestry Composition</Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
            {Object.entries(ancestryData.ancestry).map(([pop, pct], idx) => (
              <Box key={pop} sx={{ textAlign: "center", minWidth: 100 }}>
                <Box
                  sx={{
                    width: 56, height: 56, borderRadius: "50%", mx: "auto", mb: 0.5,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    backgroundColor: `${WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]}22`,
                    border: `2px solid ${WABI_CHART_COLORS[idx % WABI_CHART_COLORS.length]}`,
                  }}
                >
                  <Typography variant="body2" fontWeight={600}>
                    {typeof pct === "number" ? `${(pct * 100).toFixed(0)}%` : pct}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">{pop}</Typography>
              </Box>
            ))}
          </Box>
        </Card>
      )}

      {/* JBrowse or Fallback viewer */}
      <Card elevation={0}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Variant Explorer</Typography>
          {JBrowseLinearGenomeView && createViewState ? (
            <Box sx={{ height: 400 }}>
              <JBrowseLinearGenomeView
                viewState={createViewState({
                  assembly: {
                    name: "hg38",
                    sequence: {
                      type: "ReferenceSequenceTrack",
                      trackId: "hg38-refseq",
                      adapter: {
                        type: "BgzipFastaAdapter",
                        fastaLocation: { uri: "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz" },
                        faiLocation: { uri: "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz.fai" },
                        gziLocation: { uri: "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz.gzi" },
                      },
                    },
                  },
                  location: "chr1:1..248956422",
                })}
              />
            </Box>
          ) : (
            <FallbackVariantViewer variants={variants} />
          )}
        </CardContent>
      </Card>

      {!loading && uploads.length === 0 && (
        <Alert severity="info" sx={{ mt: 3 }}>
          No WGS uploads yet. Upload a FASTQ or BAM file to begin exploring your genome.
        </Alert>
      )}
    </Container>
  );
}
