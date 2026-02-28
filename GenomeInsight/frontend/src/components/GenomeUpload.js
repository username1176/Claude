import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert,
  Box,
  Button,
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
    setError("");
    setResult(null);
    if (rejected.length > 0) {
      setError("Invalid file. Please upload a .vcf or .txt file.");
      return;
    }
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/plain": [".vcf", ".txt"] },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024, // 500 MB
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    setProgress(0);

    try {
      const { data } = await genomeAPI.upload(file, source, (e) => {
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
        Upload Genome
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload a VCF file from your genotyping service (23andMe, AncestryDNA,
        Nebula Genomics, etc.) to receive personalized health insights.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result ? (
        <Paper elevation={2} sx={{ p: 4, textAlign: "center" }}>
          <CheckCircleIcon color="success" sx={{ fontSize: 64, mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Upload Successful!
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            {result.message}
          </Typography>
          <Typography variant="body2" sx={{ mb: 3 }}>
            Analysis ID: <code>{result.analysis_id}</code>
          </Typography>
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
            <Button variant="contained" onClick={() => navigate("/")}>
              Go to Dashboard
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate(`/report/${result.analysis_id}`)}
            >
              View Report
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
              borderColor: isDragActive ? "primary.main" : "grey.400",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
              cursor: "pointer",
              bgcolor: isDragActive ? "action.hover" : "grey.50",
              transition: "all 0.2s",
              mb: 3,
              "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon sx={{ fontSize: 48, color: "primary.main", mb: 1 }} />
            {file ? (
              <Typography variant="h6">
                {file.name}{" "}
                <Typography component="span" variant="body2" color="text.secondary">
                  ({(file.size / 1024 / 1024).toFixed(1)} MB)
                </Typography>
              </Typography>
            ) : isDragActive ? (
              <Typography variant="h6">Drop your VCF file here...</Typography>
            ) : (
              <>
                <Typography variant="h6">
                  Drag & drop your VCF file here
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  or click to browse (max 500 MB)
                </Typography>
              </>
            )}
          </Box>

          {/* Source selection */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Genotyping Service</InputLabel>
            <Select
              value={source}
              label="Genotyping Service"
              onChange={(e) => setSource(e.target.value)}
            >
              <MenuItem value="23andme">23andMe</MenuItem>
              <MenuItem value="ancestry">AncestryDNA</MenuItem>
              <MenuItem value="nebula">Nebula Genomics</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </Select>
          </FormControl>

          {/* Progress bar */}
          {uploading && (
            <Box sx={{ mb: 2 }}>
              <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 4 }} />
              <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                Uploading... {progress}%
              </Typography>
            </Box>
          )}

          <Button
            variant="contained"
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
