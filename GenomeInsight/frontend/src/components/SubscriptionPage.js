import React, { useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Container, Grid,
  Skeleton, Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { motion } from "framer-motion";
import { subscriptionAPI } from "../services/api";
import { staggerChild, WABI_CHART_COLORS } from "../theme/wabiSabi";

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    color: "#7A7267",
    features: [
      "3 genome uploads",
      "Basic blood panel view",
      "Single microbiome analysis",
      "Community support",
    ],
    excluded: [
      "AI Health Chat",
      "InnerAge calculation",
      "Predictive trends",
      "Healthspan reports",
    ],
  },
  {
    id: "basic",
    name: "Basic",
    price: "$9.99",
    period: "/month",
    color: WABI_CHART_COLORS[1],
    features: [
      "25 genome uploads",
      "Full blood panel history",
      "Biomarker optimized zones",
      "Microbiome insights",
      "Wearable integrations",
      "Email support",
    ],
    excluded: [
      "AI Health Chat",
      "Predictive trends",
      "Healthspan reports",
    ],
  },
  {
    id: "premium",
    name: "Premium",
    price: "$24.99",
    period: "/month",
    color: WABI_CHART_COLORS[0],
    popular: true,
    features: [
      "Unlimited uploads",
      "AI Health Chat",
      "InnerAge biological age",
      "Predictive biomarker trends",
      "Weekly healthspan reports",
      "Genome browser",
      "Blockchain data ownership",
      "WGS analysis",
      "Priority support",
    ],
    excluded: [],
  },
];

function TierCard({ tier, currentTier, onSelect, loading }) {
  const isCurrent = currentTier === tier.id;
  const isUpgrade = tier.id !== "free" && !isCurrent;

  return (
    <Card
      elevation={0}
      sx={{
        height: "100%",
        position: "relative",
        display: "flex",
        flexDirection: "column",
        border: tier.popular ? `2px solid ${tier.color}` : "1px solid rgba(92,75,63,0.06)",
        transition: "all 0.4s ease",
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow: `0 8px 24px rgba(92,75,63,0.08)`,
        },
      }}
    >
      {tier.popular && (
        <Box
          sx={{
            position: "absolute", top: -1, left: "50%", transform: "translateX(-50%)",
            bgcolor: tier.color, color: "#FAFAF7",
            px: 2, py: 0.25, borderRadius: "0 0 8px 8px",
            fontSize: 11, fontFamily: "Inter, sans-serif", fontWeight: 600,
            letterSpacing: "0.08em", textTransform: "uppercase",
          }}
        >
          Most Popular
        </Box>
      )}

      <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", p: 3 }}>
        <Typography variant="overline" sx={{ color: tier.color, fontWeight: 600 }}>
          {tier.name}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5, mb: 2 }}>
          <Typography variant="h3" fontWeight={700} sx={{ color: "text.primary" }}>
            {tier.price}
          </Typography>
          <Typography variant="body2" color="text.secondary">{tier.period}</Typography>
        </Box>

        <Box sx={{ flex: 1 }}>
          {tier.features.map((f) => (
            <Box key={f} sx={{ display: "flex", gap: 1, alignItems: "flex-start", mb: 1 }}>
              <CheckCircleOutlineIcon sx={{ fontSize: 16, mt: "2px", color: tier.color }} />
              <Typography variant="body2">{f}</Typography>
            </Box>
          ))}
          {tier.excluded.map((f) => (
            <Box key={f} sx={{ display: "flex", gap: 1, alignItems: "flex-start", mb: 1, opacity: 0.4 }}>
              <Typography variant="body2" sx={{ pl: "24px", textDecoration: "line-through" }}>{f}</Typography>
            </Box>
          ))}
        </Box>

        <Box sx={{ mt: 3 }}>
          {isCurrent ? (
            <Chip label="Current Plan" variant="outlined" sx={{ width: "100%", borderColor: tier.color, color: tier.color }} />
          ) : isUpgrade ? (
            <Button
              variant="contained"
              fullWidth
              disabled={loading}
              onClick={() => onSelect(tier.id)}
              sx={{
                bgcolor: tier.color,
                "&:hover": { bgcolor: tier.color, filter: "brightness(0.9)" },
              }}
            >
              {loading ? "Redirecting..." : `Upgrade to ${tier.name}`}
            </Button>
          ) : (
            <Button variant="outlined" fullWidth disabled sx={{ borderColor: "rgba(92,75,63,0.15)" }}>
              Free Tier
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

export default function SubscriptionPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    subscriptionAPI.getStatus()
      .then(({ data }) => setStatus(data))
      .catch(() => setStatus({ tier: "free", is_active: true }))
      .finally(() => setLoading(false));

    // Check for checkout success
    const params = new URLSearchParams(window.location.search);
    if (params.get("session_id")) {
      setSuccess("Subscription activated! Welcome to your new plan.");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const handleSelect = async (tier) => {
    setCheckoutLoading(true);
    setError("");
    try {
      const { data } = await subscriptionAPI.createCheckout(
        tier,
        `${window.location.origin}/subscription/success`,
        `${window.location.origin}/subscription`,
      );
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create checkout session.");
      setCheckoutLoading(false);
    }
  };

  const handleManage = async () => {
    try {
      const { data } = await subscriptionAPI.createPortal(`${window.location.origin}/subscription`);
      if (data.portal_url) window.location.href = data.portal_url;
    } catch (err) {
      setError(err.response?.data?.error || "Failed to open billing portal.");
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 6 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={3}>
          {[1, 2, 3].map((i) => <Grid item xs={12} md={4} key={i}><Skeleton variant="rounded" height={400} /></Grid>)}
        </Grid>
      </Container>
    );
  }

  const currentTier = status?.tier || "free";

  return (
    <Container maxWidth="lg" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>Membership</Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 5, maxWidth: "55ch" }}
        >
          Choose the depth of your health exploration
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }}>{success}</Alert>}

      {/* Current plan info */}
      {currentTier !== "free" && status?.is_active && (
        <Card elevation={0} sx={{ mb: 4, p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Active Plan: {currentTier.charAt(0).toUpperCase() + currentTier.slice(1)}
              </Typography>
              {status.current_period_end && (
                <Typography variant="caption" color="text.secondary">
                  Renews {new Date(status.current_period_end).toLocaleDateString()}
                  {status.cancel_at_period_end && " (cancels at period end)"}
                </Typography>
              )}
            </Box>
            <Button variant="outlined" size="small" onClick={handleManage}>
              Manage Billing
            </Button>
          </Box>
        </Card>
      )}

      {/* Tier cards */}
      <Grid container spacing={3} alignItems="stretch">
        {TIERS.map((tier, idx) => (
          <Grid item xs={12} md={4} key={tier.id}>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              style={{ height: "100%" }}
            >
              <TierCard
                tier={tier}
                currentTier={currentTier}
                onSelect={handleSelect}
                loading={checkoutLoading}
              />
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {/* FAQ / trust signals */}
      <Box sx={{ mt: 6, textAlign: "center" }}>
        <div className="wabi-divider" style={{ maxWidth: "200px", margin: "0 auto 2rem" }} />
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: "50ch", mx: "auto" }}>
          All plans include AES-256 encryption, HIPAA-compliant storage, and the ability
          to delete your data at any time. Cancel or change plans through the billing portal.
        </Typography>
      </Box>
    </Container>
  );
}
