import React from "react";
import { Box, Button, Container, Typography } from "@mui/material";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container maxWidth="sm">
          <Box
            sx={{
              mt: 16,
              textAlign: "center",
              p: 6,
              bgcolor: "rgba(255,255,255,0.55)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(92, 75, 63, 0.06)",
              borderRadius: "0.5rem 0.75rem 0.45rem 0.625rem",
            }}
          >
            <Typography
              variant="h2"
              sx={{ mb: 3, fontSize: "3rem", opacity: 0.2, fontWeight: 300 }}
            >
              &#8230;
            </Typography>
            <Typography variant="h5" sx={{ mb: 1 }}>
              Something went awry
            </Typography>
            <Typography
              variant="body1"
              sx={{ color: "text.secondary", fontStyle: "italic", mb: 4 }}
            >
              An unexpected error occurred. Like nature, things sometimes break.
            </Typography>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
              <Button variant="contained" onClick={this.handleReset}>
                Try Again
              </Button>
              <Button
                variant="outlined"
                onClick={() => (window.location.href = "/")}
              >
                Return Home
              </Button>
            </Box>
          </Box>
        </Container>
      );
    }

    return this.props.children;
  }
}
