import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert, Box, Button, Chip, Container, FormControl, InputLabel,
  MenuItem, Paper, Select, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { epigeneticsAPI } from "../services/api";

const ASSAY_TYPES = {
  histone: [
    { value: "H3K27ac", label: "H3K27ac (Active enhancers)" },
    { value: "H3K4me3", label: "H3K4me3 (Active promoters)" },
    { value: "H3K4me1", label: "H3K4me1 (Enhancers)" },
    { value: "H3K27me3", label: "H3K27me3 (Polycomb repression)" },
    { value: "H3K36me3", label: "H3K36me3 (Gene bodies)" },
    { value: "H3K9me3", label: "H3K9me3 (Heterochromatin)" },
  ],
  methylation: [
    { value: "WGBS", label: "WGBS (Whole Genome Bisulfite)" },
    { value: "450K", label: "Illumina 450K Array" },
    { value: "EPIC", label: "Illumina EPIC Array" },
  ],
};

const TISSUE_TYPES = ["blood", "pbmc", "saliva", "liver", "brain", "adipose", "lung", "monocyte", "t_cell", "b_cell"];

export default function EpigeneticsUpload() {
  const [file, setFile] = useState(null);
  const [dataType, setDataType] = useState("");
  const [assayType, setAssayType] = useState("");
  const [tissueType, setTissueType] = useState("");
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const onDrop = useCallback((accepted, rejected) => {
    setError(""); setResult(null);
    if (rejected.length > 0) { setError("Invalid file. Please upload a .bed or .csv file."); return; }
    if (accepted.length > 0) {
      setFile(accepted[0]);
      const name = accepted[0].name.toLowerCase();
      if (name.endsWith(".bed") && !dataType) setDataType("histone");
      else if (name.endsWith(".csv") && !dataType) setDataType("methylation");
    }
  }, [dataType]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/plain": [".bed"], "text/csv": [".csv"], "text/tab-separated-values": [".bed"] },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file || !dataType) return;
    setUploading(true); setError(""); setProgress(0);
    try {
      const { data } = await epigeneticsAPI.upload(file, dataType, assayType, tissueType, (e) => setProgress(Math.round((e.loaded / e.total) * 100)));
      setResult(data);
    } catch (err) { setError(err.response?.data?.error || "Upload failed. Please try again."); }
    finally { setUploading(false); }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>Upload Epigenetic Data</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          The marks above your genes — histone whispers and methylation memories
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        {result ? (
          <Paper elevation={0} sx={{ p: 5, textAlign: "center" }}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.5 }}>
              <Typography variant="h2" sx={{ mb: 2, fontSize: "3rem", opacity: 0.3 }}>&#10003;</Typography>
              <Typography variant="h5" sx={{ mb: 1 }}>Received</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{result.message}</Typography>
              <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 4 }}>
                <Chip label={`Status: ${result.status}`} size="small" variant="outlined" />
              </Box>
              <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                <Button variant="contained" onClick={() => navigate("/")}>Dashboard</Button>
                <Button variant="outlined" onClick={() => { setFile(null); setResult(null); setProgress(0); setDataType(""); setAssayType(""); }}>Upload Another</Button>
              </Box>
            </motion.div>
          </Paper>
        ) : (
          <Paper elevation={0} sx={{ p: 5 }}>
            <Box {...getRootProps()} className={isDragActive ? "wabi-dropzone wabi-dropzone-active" : "wabi-dropzone"} sx={{ mb: 3 }}>
              <input {...getInputProps()} />
              {file ? (
                <Box>
                  <Typography variant="h6" sx={{ mb: 0.5 }}>{file.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{(file.size / 1024).toFixed(0)} KB</Typography>
                </Box>
              ) : isDragActive ? (
                <Typography variant="h6" sx={{ color: "secondary.main" }}>Release your essence here...</Typography>
              ) : (
                <>
                  <Typography variant="h6" sx={{ mb: 1, fontWeight: 400 }}>Drop your epigenetic data here</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>BED (histone marks) or CSV (methylation) — up to 100 MB</Typography>
                </>
              )}
            </Box>

            <FormControl fullWidth sx={{ mb: 2 }} required>
              <InputLabel>Data Type</InputLabel>
              <Select value={dataType} label="Data Type" onChange={(e) => { setDataType(e.target.value); setAssayType(""); }}>
                <MenuItem value="histone">Histone Modifications (BED)</MenuItem>
                <MenuItem value="methylation">DNA Methylation (CSV)</MenuItem>
              </Select>
            </FormControl>

            {dataType && (
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Assay Type (optional)</InputLabel>
                <Select value={assayType} label="Assay Type (optional)" onChange={(e) => setAssayType(e.target.value)}>
                  <MenuItem value="">Not specified</MenuItem>
                  {(ASSAY_TYPES[dataType] || []).map((a) => <MenuItem key={a.value} value={a.value}>{a.label}</MenuItem>)}
                </Select>
              </FormControl>
            )}

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Tissue Type (optional)</InputLabel>
              <Select value={tissueType} label="Tissue Type (optional)" onChange={(e) => setTissueType(e.target.value)}>
                <MenuItem value="">Not specified</MenuItem>
                {TISSUE_TYPES.map((t) => <MenuItem key={t} value={t}>{t.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</MenuItem>)}
              </Select>
            </FormControl>

            {uploading && (
              <Box sx={{ mb: 3 }}>
                <div className="wabi-progress"><div className="wabi-progress-bar" style={{ width: `${progress}%` }} /></div>
                <Typography variant="caption" align="center" sx={{ display: "block", mt: 1, color: "text.secondary" }}>Uploading... {progress}%</Typography>
              </Box>
            )}

            <Button variant="contained" size="large" fullWidth disabled={!file || !dataType || uploading} onClick={handleUpload} sx={{ py: 1.5 }}>
              {uploading ? "Uploading..." : "Upload & Analyze"}
            </Button>
          </Paper>
        )}
      </motion.div>
    </Container>
  );
}
