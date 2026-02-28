import React, { useState, useEffect } from "react";
import {
  Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControlLabel, Typography,
} from "@mui/material";

const STORAGE_KEY = "genomeinsight_disclaimer_accepted";

export default function DisclaimerModal() {
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
  }, []);

  const handleAccept = () => {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setOpen(false);
  };

  return (
    <Dialog
      open={open}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown
      PaperProps={{
        sx: {
          bgcolor: "#FAFAF7",
          borderRadius: "0.5rem 0.75rem 0.45rem 0.625rem",
          p: 1,
        },
      }}
    >
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1.5, fontWeight: 600 }}>
        <span style={{ fontSize: "1.5rem", opacity: 0.4 }}>&#9670;</span>
        A Mindful Note
      </DialogTitle>
      <DialogContent dividers sx={{ borderColor: "rgba(92,75,63,0.08)" }}>
        <Typography variant="body1" paragraph sx={{ fontWeight: 500 }}>
          GenomeInsight is for <strong>informational and educational purposes only</strong>.
        </Typography>
        <Typography variant="body2" paragraph sx={{ lineHeight: 1.8, color: "text.secondary" }}>
          This application uses publicly available genome research databases and
          AI-generated analysis. The results are <strong>not medical advice</strong> and
          should not be used to diagnose, treat, cure, or prevent any disease.
        </Typography>
        <Typography variant="body2" paragraph sx={{ lineHeight: 1.8, color: "text.secondary" }}>
          Genetic associations represent statistical probabilities across populations,
          not individual certainties. Environment, lifestyle, and epigenetics all shape
          health outcomes beyond genetics alone.
        </Typography>
        <Typography variant="body2" paragraph sx={{ lineHeight: 1.8, color: "text.secondary" }}>
          Wearable, blood, epigenetic, and microbiome data are encrypted at rest and used
          solely for cross-domain insights. They are not shared with third parties.
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 500, fontStyle: "italic", color: "text.primary" }}>
          Always consult a qualified healthcare provider before making health decisions.
        </Typography>
        <FormControlLabel
          sx={{ mt: 2 }}
          control={
            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              sx={{ color: "rgba(92,75,63,0.3)", "&.Mui-checked": { color: "#8B9A7F" } }}
            />
          }
          label={
            <Typography variant="body2" color="text.secondary">
              I understand this is not a substitute for professional medical advice
            </Typography>
          }
        />
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleAccept} disabled={!checked} variant="contained" size="large" sx={{ px: 4 }}>
          I Understand — Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
