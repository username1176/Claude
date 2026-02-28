import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert, Box, Button, Chip, Container, FormControl, InputLabel,
  MenuItem, Paper, Select, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { microbiomeAPI } from "../services/api";

const SAMPLE_TYPES = [
  { value: "stool", label: "Stool Sample" },
  { value: "oral", label: "Oral Swab" },
  { value: "skin", label: "Skin Swab" },
  { value: "nasal", label: "Nasal Swab" },
  { value: "vaginal", label: "Vaginal Swab" },
  { value: "environmental", label: "Environmental" },
  { value: "other", label: "Other" },
];

export default function MicrobiomeUpload() {
  const [file, setFile] = useState(null);
  const [sampleType, setSampleType] = useState("stool");
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const onDrop = useCallback((accepted, rejected) => {
    setError(""); setResult(null);
    if (rejected.length > 0) { setError("Invalid file. Upload a BIOM, OTU table, or FASTQ file."); return; }
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/json": [".biom", ".json"],
      "text/csv": [".csv"],
      "text/tab-separated-values": [".tsv"],
      "application/gzip": [".fastq.gz", ".fq.gz"],
      "application/octet-stream": [".fastq", ".fq"],
    },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError(""); setProgress(0);
    try {
      const { data } = await microbiomeAPI.upload(file, sampleType, (e) => setProgress(Math.round((e.loaded / e.total) * 100)));
      setResult(data);
    } catch (err) { setError(err.response?.data?.error || "Upload failed. Please try again."); }
    finally { setUploading(false); }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>Upload Microbiome Data</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          The garden within — trillions of companions shaping your health
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        {result ? (
          <Paper elevation={0} sx={{ p: 5, textAlign: "center" }}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.5 }}>
              <Typography variant="h2" sx={{ mb: 2, fontSize: "3rem", opacity: 0.3 }}>&#10003;</Typography>
              <Typography variant="h5" sx={{ mb: 1 }}>Received</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{result.message || "Your microbiome sample is being analyzed."}</Typography>
              <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 4 }}>
                <Chip label={`Status: ${result.status}`} size="small" variant="outlined" />
              </Box>
              <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                <Button variant="contained" onClick={() => navigate("/")}>Dashboard</Button>
                {result.analysis_id && <Button variant="outlined" onClick={() => navigate("/unified-report")}>Unified Report</Button>}
                <Button variant="outlined" onClick={() => { setFile(null); setResult(null); setProgress(0); setSampleType("stool"); }}>Upload Another</Button>
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
                  <Typography variant="h6" sx={{ mb: 1, fontWeight: 400 }}>Drop your microbiome data here</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>BIOM, OTU table, or FASTQ — up to 200 MB</Typography>
                </>
              )}
            </Box>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Sample Type</InputLabel>
              <Select value={sampleType} label="Sample Type" onChange={(e) => setSampleType(e.target.value)}>
                {SAMPLE_TYPES.map((s) => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}
              </Select>
            </FormControl>

            {uploading && (
              <Box sx={{ mb: 3 }}>
                <div className="wabi-progress"><div className="wabi-progress-bar" style={{ width: `${progress}%` }} /></div>
                <Typography variant="caption" align="center" sx={{ display: "block", mt: 1, color: "text.secondary" }}>Uploading... {progress}%</Typography>
              </Box>
            )}

            <Button variant="contained" size="large" fullWidth disabled={!file || uploading} onClick={handleUpload} sx={{ py: 1.5 }}>
              {uploading ? "Uploading..." : "Upload & Analyze"}
            </Button>
          </Paper>
        )}
      </motion.div>
    </Container>
  );
}
