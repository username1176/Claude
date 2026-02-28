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
import { epigeneticsAPI } from "../services/api";

const ASSAY_TYPES = {
  histone: [
    { value: "H3K27ac", label: "H3K27ac (Active enhancers/promoters)" },
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

const TISSUE_TYPES = [
  "blood", "pbmc", "saliva", "liver", "brain",
  "adipose", "lung", "monocyte", "t_cell", "b_cell",
];

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
    setError("");
    setResult(null);
    if (rejected.length > 0) {
      setError("Invalid file. Please upload a .bed or .csv file.");
      return;
    }
    if (accepted.length > 0) {
      setFile(accepted[0]);
      // Auto-detect data type from extension
      const name = accepted[0].name.toLowerCase();
      if (name.endsWith(".bed") && !dataType) {
        setDataType("histone");
      } else if (name.endsWith(".csv") && !dataType) {
        setDataType("methylation");
      }
    }
  }, [dataType]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/plain": [".bed"],
      "text/csv": [".csv"],
      "text/tab-separated-values": [".bed"],
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file || !dataType) return;
    setUploading(true);
    setError("");
    setProgress(0);

    try {
      const { data } = await epigeneticsAPI.upload(
        file, dataType, assayType, tissueType,
        (e) => {
          const pct = Math.round((e.loaded / e.total) * 100);
          setProgress(pct);
        }
      );
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
        Upload Epigenetic Data
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload a BED file (histone ChIP-seq peaks) or CSV (methylation array
        data) to analyze epigenetic marks and cross-reference with your genome.
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
          <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 3 }}>
            <Chip label={`Status: ${result.status}`} color="success" />
            {result.analysis_id && (
              <Chip label={`Analysis: ${result.analysis_id.slice(0, 8)}...`} />
            )}
          </Box>
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
            <Button variant="contained" onClick={() => navigate("/")}>
              Go to Dashboard
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                setFile(null);
                setResult(null);
                setProgress(0);
                setDataType("");
                setAssayType("");
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
                  ({(file.size / 1024).toFixed(0)} KB)
                </Typography>
              </Typography>
            ) : isDragActive ? (
              <Typography variant="h6">Drop your file here...</Typography>
            ) : (
              <>
                <Typography variant="h6">
                  Drag & drop your epigenetic data file
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  BED (histone marks) or CSV (methylation) — max 100 MB
                </Typography>
              </>
            )}
          </Box>

          {/* Data type */}
          <FormControl fullWidth sx={{ mb: 2 }} required>
            <InputLabel>Data Type</InputLabel>
            <Select
              value={dataType}
              label="Data Type"
              onChange={(e) => {
                setDataType(e.target.value);
                setAssayType("");
              }}
            >
              <MenuItem value="histone">Histone Modifications (BED)</MenuItem>
              <MenuItem value="methylation">DNA Methylation (CSV)</MenuItem>
            </Select>
          </FormControl>

          {/* Assay type */}
          {dataType && (
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Assay Type (optional)</InputLabel>
              <Select
                value={assayType}
                label="Assay Type (optional)"
                onChange={(e) => setAssayType(e.target.value)}
              >
                <MenuItem value="">Not specified</MenuItem>
                {(ASSAY_TYPES[dataType] || []).map((a) => (
                  <MenuItem key={a.value} value={a.value}>{a.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Tissue type */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Tissue Type (optional)</InputLabel>
            <Select
              value={tissueType}
              label="Tissue Type (optional)"
              onChange={(e) => setTissueType(e.target.value)}
            >
              <MenuItem value="">Not specified</MenuItem>
              {TISSUE_TYPES.map((t) => (
                <MenuItem key={t} value={t}>
                  {t.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
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
            size="large"
            fullWidth
            disabled={!file || !dataType || uploading}
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
