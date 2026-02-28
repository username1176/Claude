import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert, Box, Button, Chip, Container, Paper, TextField, Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { bloodAPI } from "../services/api";

export default function BloodUpload() {
  const [file, setFile] = useState(null);
  const [testDate, setTestDate] = useState(new Date().toISOString().split("T")[0]);
  const [labName, setLabName] = useState("");
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const onDrop = useCallback((accepted, rejected) => {
    setError(""); setResult(null);
    if (rejected.length > 0) { setError("Invalid file. Please upload a .csv or .pdf file."); return; }
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file || !testDate) return;
    setUploading(true); setError(""); setProgress(0);
    try {
      const { data } = await bloodAPI.upload(file, testDate, labName, (e) => setProgress(Math.round((e.loaded / e.total) * 100)));
      setResult(data);
    } catch (err) { setError(err.response?.data?.error || "Upload failed. Please try again."); }
    finally { setUploading(false); }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <Typography variant="h4" sx={{ mb: 1 }}>Upload Blood Test</Typography>
        <Typography variant="body1" sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "55ch" }}>
          Your blood tells a story — let us read between the lines
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        {result ? (
          <Paper elevation={0} sx={{ p: 5, textAlign: "center" }}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.5 }}>
              <Typography variant="h2" sx={{ mb: 2, fontSize: "3rem", opacity: 0.3 }}>&#10003;</Typography>
              <Typography variant="h5" sx={{ mb: 1 }}>Received</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{result.message}</Typography>
              <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 4 }}>
                <Chip label={`${result.markers_parsed} markers`} size="small" variant="outlined" />
              </Box>
              <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
                <Button variant="contained" onClick={() => navigate("/")}>Dashboard</Button>
                <Button variant="outlined" onClick={() => { setFile(null); setResult(null); setProgress(0); }}>Upload Another</Button>
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
                  <Typography variant="h6" sx={{ mb: 1, fontWeight: 400 }}>Drop your blood test here</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>PDF or CSV — up to 20 MB</Typography>
                </>
              )}
            </Box>

            <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
              <TextField label="Test Date" type="date" value={testDate} onChange={(e) => setTestDate(e.target.value)} InputLabelProps={{ shrink: true }} required fullWidth />
              <TextField label="Lab Name (optional)" value={labName} onChange={(e) => setLabName(e.target.value)} fullWidth />
            </Box>

            {uploading && (
              <Box sx={{ mb: 3 }}>
                <div className="wabi-progress"><div className="wabi-progress-bar" style={{ width: `${progress}%` }} /></div>
                <Typography variant="caption" align="center" sx={{ display: "block", mt: 1, color: "text.secondary" }}>Uploading... {progress}%</Typography>
              </Box>
            )}

            <Button variant="contained" size="large" fullWidth disabled={!file || !testDate || uploading} onClick={handleUpload} sx={{ py: 1.5 }}>
              {uploading ? "Uploading..." : "Upload & Parse"}
            </Button>
          </Paper>
        )}
      </motion.div>
    </Container>
  );
}
