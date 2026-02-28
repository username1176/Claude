import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
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
    setError("");
    setResult(null);
    if (rejected.length > 0) {
      setError(
        "Invalid file. Please upload a BIOM (.biom, .json), OTU table (.csv, .tsv), or FASTQ (.fastq, .fq, .fastq.gz) file."
      );
      return;
    }
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
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
    setUploading(true);
    setError("");
    setProgress(0);

    try {
      const { data } = await microbiomeAPI.upload(file, sampleType, (e) => {
        const pct = Math.round((e.loaded / e.total) * 100);
        setProgress(pct);
      });
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.error || "Upload failed. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 6 }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Upload Microbiome Data
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload a BIOM file, OTU table (CSV/TSV), or FASTQ reads to analyze
        your gut microbiome composition, diversity metrics, and cross-domain
        health correlations.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {result ? (
        <Paper elevation={2} sx={{ p: 4, textAlign: "center" }}>
          <CheckCircleIcon color="success" sx={{ fontSize: 64, mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Upload Successful!
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            {result.message ||
              "Your microbiome sample has been uploaded and analysis is in progress."}
          </Typography>
          <Box
            sx={{
              display: "flex",
              gap: 1,
              justifyContent: "center",
              mb: 3,
            }}
          >
            <Chip label={`Status: ${result.status}`} color="success" />
            {result.upload_id && (
              <Chip
                label={`Upload: ${result.upload_id.slice(0, 8)}...`}
              />
            )}
            {result.analysis_id && (
              <Chip
                label={`Analysis: ${result.analysis_id.slice(0, 8)}...`}
              />
            )}
          </Box>
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
            <Button variant="contained" onClick={() => navigate("/")}>
              Go to Dashboard
            </Button>
            {result.analysis_id && (
              <Button
                variant="outlined"
                color="secondary"
                onClick={() =>
                  navigate(`/unified-report`)
                }
              >
                View Unified Report
              </Button>
            )}
            <Button
              variant="outlined"
              onClick={() => {
                setFile(null);
                setResult(null);
                setProgress(0);
                setSampleType("stool");
              }}
            >
              Upload Another
            </Button>
          </Box>
        </Paper>
      ) : (
        <Paper elevation={2} sx={{ p: 4 }}>
          {/* Dropzone */}
          <Box
            {...getRootProps()}
            sx={{
              border: "2px dashed",
              borderColor: isDragActive ? "secondary.main" : "grey.400",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
              cursor: "pointer",
              bgcolor: isDragActive ? "action.hover" : "grey.50",
              transition: "all 0.2s",
              mb: 3,
              "&:hover": {
                borderColor: "secondary.main",
                bgcolor: "action.hover",
              },
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon
              sx={{ fontSize: 48, color: "secondary.main", mb: 1 }}
            />
            {file ? (
              <Typography variant="h6">
                {file.name}{" "}
                <Typography
                  component="span"
                  variant="body2"
                  color="text.secondary"
                >
                  ({(file.size / 1024).toFixed(0)} KB)
                </Typography>
              </Typography>
            ) : isDragActive ? (
              <Typography variant="h6">Drop your file here...</Typography>
            ) : (
              <>
                <Typography variant="h6">
                  Drag & drop your microbiome data file
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  BIOM (.biom, .json) | OTU table (.csv, .tsv) | FASTQ
                  (.fastq, .fq) — max 200 MB
                </Typography>
              </>
            )}
          </Box>

          {/* Sample type */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Sample Type</InputLabel>
            <Select
              value={sampleType}
              label="Sample Type"
              onChange={(e) => setSampleType(e.target.value)}
            >
              {SAMPLE_TYPES.map((s) => (
                <MenuItem key={s.value} value={s.value}>
                  {s.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Progress bar */}
          {uploading && (
            <Box sx={{ mb: 2 }}>
              <LinearProgress
                variant="determinate"
                value={progress}
                sx={{ height: 8, borderRadius: 4 }}
              />
              <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                Uploading... {progress}%
              </Typography>
            </Box>
          )}

          <Button
            variant="contained"
            color="secondary"
            size="large"
            fullWidth
            disabled={!file || uploading}
            onClick={handleUpload}
            sx={{ py: 1.5 }}
          >
            {uploading ? "Uploading..." : "Upload & Analyze"}
          </Button>
        </Paper>
      )}
    </Container>
  );
}
