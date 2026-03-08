import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Alert, Box, Button, Card, CardContent, Chip, Container,
  LinearProgress, Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { motion } from "framer-motion";
import { wgsAPI } from "../services/api";
import { staggerChild } from "../theme/wabiSabi";

const ACCEPTED = {
  "application/gzip": [".fastq.gz", ".fq.gz"],
  "application/octet-stream": [".fastq", ".fq", ".bam"],
};

export default function WGSUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const onDrop = useCallback((accepted, rejected) => {
    setError("");
    setResult(null);
    if (rejected.length > 0) {
      setError("Unsupported file type. Please upload FASTQ, FASTQ.GZ, or BAM files.");
      return;
    }
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    maxSize: 2 * 1024 * 1024 * 1024, // 2 GB
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError("");
    try {
      const { data } = await wgsAPI.upload(file, (e) => {
        if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
      });
      setResult(data);
      setFile(null);
    } catch (err) {
      setError(err.response?.data?.error || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>
          Whole Genome Sequencing
        </Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 5, maxWidth: "50ch" }}
        >
          Upload your full genome — FASTQ, BAM, or compressed archives
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {result && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Upload complete — analysis queued. Upload ID: {result.upload_id || result.id}
        </Alert>
      )}

      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent sx={{ p: 0 }}>
          <div
            {...getRootProps()}
            className="wabi-dropzone"
            style={{
              padding: "3rem 2rem",
              textAlign: "center",
              cursor: uploading ? "not-allowed" : "pointer",
              opacity: uploading ? 0.6 : 1,
              borderRadius: "0.375rem 0.5rem 0.325rem 0.45rem",
            }}
          >
            <input {...getInputProps()} disabled={uploading} />
            <CloudUploadIcon sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
            {isDragActive ? (
              <Typography variant="body1" color="text.secondary">
                Release to upload your genome file...
              </Typography>
            ) : (
              <>
                <Typography variant="body1" sx={{ mb: 0.5 }}>
                  Drag & drop your WGS file here
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  FASTQ, FASTQ.GZ, or BAM — up to 2 GB
                </Typography>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {file && !uploading && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" fontWeight={500}>{file.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {(file.size / (1024 * 1024)).toFixed(1)} MB
              </Typography>
            </Box>
            <Chip
              label={file.name.endsWith(".bam") ? "BAM" : "FASTQ"}
              size="small"
              variant="outlined"
              sx={{ borderColor: "rgba(139,154,127,0.4)", color: "#576450" }}
            />
            <Button variant="contained" onClick={handleUpload}>
              Upload & Analyze
            </Button>
          </Box>
        </motion.div>
      )}

      {uploading && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
            <Typography variant="caption" color="text.secondary">Uploading...</Typography>
            <Typography variant="caption" color="text.secondary">{progress}%</Typography>
          </Box>
          <LinearProgress variant="determinate" value={progress} sx={{ borderRadius: 4 }} />
        </Box>
      )}

      {/* Info cards */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2, mt: 4 }}>
        <Card elevation={0} sx={{ p: 2.5 }}>
          <Typography variant="overline" color="text.secondary">Supported Formats</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            FASTQ (.fastq, .fq), compressed FASTQ (.fastq.gz, .fq.gz), and BAM alignment files.
            Paired-end reads are auto-detected from naming conventions.
          </Typography>
        </Card>
        <Card elevation={0} sx={{ p: 2.5 }}>
          <Typography variant="overline" color="text.secondary">What Happens Next</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Your genome is encrypted, quality-checked, and queued for variant calling
            and ancestry inference. Results appear in your dashboard within minutes.
          </Typography>
        </Card>
      </Box>
    </Container>
  );
}
