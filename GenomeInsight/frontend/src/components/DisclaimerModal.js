import React, { useState, useEffect } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Typography,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

const STORAGE_KEY = "genomeinsight_disclaimer_accepted";

export default function DisclaimerModal() {
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem(STORAGE_KEY);
    if (!accepted) {
      setOpen(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setOpen(false);
  };

  return (
    <Dialog open={open} maxWidth="sm" fullWidth disableEscapeKeyDown>
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <WarningAmberIcon color="warning" />
        Important Medical Disclaimer
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body1" paragraph>
          <strong>GenomeInsight</strong> is designed for{" "}
          <strong>informational and educational purposes only</strong>.
        </Typography>
        <Typography variant="body2" paragraph>
          This application uses publicly available genome research databases and
          AI-generated analysis. The results provided are{" "}
          <strong>NOT medical advice</strong> and should{" "}
          <strong>NOT</strong> be used to diagnose, treat, cure, or prevent any
          disease or health condition.
        </Typography>
        <Typography variant="body2" paragraph>
          Genetic associations represent statistical probabilities across
          populations, not individual certainties. Many factors beyond
          genetics — including environment, lifestyle, and epigenetics — influence
          health outcomes.
        </Typography>
        <Typography variant="body2" paragraph>
          <strong>Wearable Data:</strong> Activity, sleep, heart rate, and other
          metrics are pulled from connected devices on a daily schedule. This
          data is encrypted at rest and used only for cross-domain insights. It
          is not shared with third parties.
        </Typography>
        <Typography variant="body2" paragraph>
          <strong>Epigenetic Analysis:</strong> Histone modification and DNA
          methylation analyses are experimental and based on publicly available
          reference datasets (ENCODE, Roadmap Epigenomics). Results may not
          reflect your current epigenetic state.
        </Typography>
        <Typography variant="body2" paragraph sx={{ fontWeight: 600 }}>
          Always consult a qualified healthcare provider before making any
          health decisions based on genetic, blood, epigenetic, or wearable
          data.
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              color="primary"
            />
          }
          label="I understand that this tool is not a substitute for professional medical advice"
        />
      </DialogContent>
      <DialogActions>
        <Button
          onClick={handleAccept}
          disabled={!checked}
          variant="contained"
          size="large"
        >
          I Understand — Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
