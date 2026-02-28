import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert, Box, Button, Container, FormControl, InputLabel,
  MenuItem, Paper, Select, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { genomeAPI } from "../services/api";

export default function GenomeUpload() {
  const [file, setFile] = useState(null);
  const [source, setSource] = useState("other");
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const onDrop = useCallback((accepted, rejected) => {
    setError(""); setResult(null);
    if (rejected.length > 0) { setError("Invalid file. Please upload a .vcf or .txt file."); return; }
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/plain": [".vcf", ".txt"] },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError(""); setProgress(0);
    try {
      const { data } = await genomeAPI.upload(file, source, (e) => setProgress(Math.round((e.loaded / e.total) * 100)));
      setResult(data);
    } catch (err) { setError(err.response?.data?.error || "Upload failed. Please try again."); }
    finally { setUploading(false); }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>Upload Genome</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          Share your genetic blueprint — a VCF file from 23andMe, AncestryDNA, Nebula, or others
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        {result ? (
          <Paper elevation={0} sx={{ p: 5, textAlign: "center" }}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.5 }}>
              <Typography variant="h2" sx={{ mb: 2, fontSize: "3rem", opacity: 0.3 }}>&#10003;</Typography>
              <Typography variant="h5" sx={{ mb: 1 }}>Received</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{result.message}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 4, fontFamily: "monospace" }}>
                Analysis: {result.analysis_id}
              </Typography>
              <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                <Button variant="contained" onClick={() => navigate("/")}>Dashboard</Button>
                <Button variant="outlined" onClick={() => navigate(`/report/${result.analysis_id}`)}>View Report</Button>
              </Box>
            </motion.div>
          </Paper>
        ) : (
          <Paper elevation={0} sx={{ p: 5 }}>
            {/* Wabi Sabi Dropzone */}
            <Box
              {...getRootProps()}
              className={isDragActive ? "wabi-dropzone wabi-dropzone-active" : "wabi-dropzone"}
              sx={{ mb: 3 }}
            >
              <input {...getInputProps()} />
              {file ? (
                <Box>
                  <Typography variant="h6" sx={{ mb: 0.5 }}>{file.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{(file.size / 1024 / 1024).toFixed(1)} MB</Typography>
                </Box>
              ) : isDragActive ? (
                <Typography variant="h6" sx={{ color: "secondary.main" }}>Release your essence here...</Typography>
              ) : (
                <>
                  <Typography variant="h6" sx={{ mb: 1, fontWeight: 400 }}>
                    Drop your genome here
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                    VCF or TXT — up to 500 MB
                  </Typography>
                </>
              )}
            </Box>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Source</InputLabel>
              <Select value={source} label="Source" onChange={(e) => setSource(e.target.value)}>
                <MenuItem value="23andme">23andMe</MenuItem>
                <MenuItem value="ancestry">AncestryDNA</MenuItem>
                <MenuItem value="nebula">Nebula Genomics</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>

            {uploading && (
              <Box sx={{ mb: 3 }}>
                <div className="wabi-progress">
                  <div className="wabi-progress-bar" style={{ width: `${progress}%` }} />
                </div>
                <Typography variant="caption" align="center" sx={{ display: "block", mt: 1, color: "text.secondary" }}>
                  Uploading... {progress}%
                </Typography>
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
