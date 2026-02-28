import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import { motion } from "framer-motion";
import { useAuth } from "../contexts/AuthContext";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await register(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.error || "Registration failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <Box
          sx={{
            mt: 12,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Box
            sx={{
              width: "100%",
              maxWidth: 440,
              p: { xs: 4, sm: 6 },
              bgcolor: "rgba(255,255,255,0.55)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(92, 75, 63, 0.06)",
              borderRadius: "0.5rem 0.75rem 0.45rem 0.625rem",
            }}
          >
            {/* Logo */}
            <Box sx={{ display: "flex", alignItems: "center", mb: 5, gap: 1.5 }}>
              <svg width="32" height="32" viewBox="0 0 28 28" fill="none">
                <circle cx="14" cy="14" r="12" stroke="#5C4B3F" strokeWidth="1.5" fill="none" opacity="0.6" />
                <path d="M14 4 C18 8, 20 12, 14 24 C8 12, 10 8, 14 4Z" fill="#8B9A7F" opacity="0.4" />
                <circle cx="14" cy="12" r="2.5" fill="#5C4B3F" opacity="0.5" />
              </svg>
              <Typography
                variant="h4"
                sx={{ fontWeight: 600, color: "primary.main", letterSpacing: "0.02em" }}
              >
                GenomeInsight
              </Typography>
            </Box>

            <Typography variant="h5" sx={{ mb: 0.5, fontWeight: 400, color: "text.primary" }}>
              Begin your journey
            </Typography>
            <Typography variant="body2" sx={{ mb: 4, color: "text.secondary", fontStyle: "italic" }}>
              Every path starts with a single step
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                label="Email"
                type="email"
                fullWidth
                required
                margin="normal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                autoFocus
              />
              <TextField
                label="Password"
                type="password"
                fullWidth
                required
                margin="normal"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                helperText="At least 8 characters"
              />
              <TextField
                label="Confirm Password"
                type="password"
                fullWidth
                required
                margin="normal"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  mt: 3,
                  mb: 2,
                  py: 1.5,
                  bgcolor: "primary.main",
                  "&:hover": { bgcolor: "primary.dark" },
                }}
              >
                {loading ? <CircularProgress size={24} sx={{ color: "#FAFAF7" }} /> : "Create Account"}
              </Button>
            </Box>

            <Typography variant="body2" align="center" sx={{ mt: 2, color: "text.secondary" }}>
              Already on the path?{" "}
              <Link to="/login" style={{ color: "#8B9A7F", fontWeight: 600 }}>
                Sign in
              </Link>
            </Typography>
          </Box>
        </Box>
      </motion.div>
    </Container>
  );
}
