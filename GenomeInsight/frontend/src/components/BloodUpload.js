import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  LinearProgress,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
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
    setError("");
    setResult(null);
    if (rejected.length > 0) {
      setError("Invalid file. Please upload a .csv or .pdf file.");
      return;
    }
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20 MB
  });

  const handleUpload = async () => {
    if (!file || !testDate) return;
    setUploading(true);
    setError("");
    setProgress(0);

    try {
      const { data } = await bloodAPI.upload(file, testDate, labName, (e) => {
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
        Upload Blood Test
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload a PDF or CSV of your blood test results. Markers will be
        auto-parsed and correlated with your genome data.
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
            <Chip label={`${result.markers_parsed} markers parsed`} />
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
              "&:hover": { borderColor: "secondary.main", bgcolor: "action.hover" },
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon sx={{ fontSize: 48, color: "secondary.main", mb: 1 }} />
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
                  Drag & drop your blood test file
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  PDF or CSV (max 20 MB)
                </Typography>
              </>
            )}
          </Box>

          {/* Form fields */}
          <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
            <TextField
              label="Test Date"
              type="date"
              value={testDate}
              onChange={(e) => setTestDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              required
              fullWidth
            />
            <TextField
              label="Lab Name (optional)"
              value={labName}
              onChange={(e) => setLabName(e.target.value)}
              fullWidth
            />
          </Box>

          {/* Progress bar */}
          {uploading && (
            <Box sx={{ mb: 2 }}>
              <LinearProgress
                variant="determinate"
                value={progress}
                color="secondary"
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
            disabled={!file || !testDate || uploading}
            onClick={handleUpload}
            sx={{ py: 1.5 }}
          >
            {uploading ? "Uploading..." : "Upload & Parse"}
          </Button>
        </Paper>
      )}
    </Container>
  );
}
