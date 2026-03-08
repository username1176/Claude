import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Alert, Box, Button, Card, Container, IconButton, InputAdornment,
  TextField, Typography, CircularProgress, Chip,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import AddIcon from "@mui/icons-material/Add";
import { motion } from "framer-motion";
import { chatAPI } from "../services/api";
import { staggerChild } from "../theme/wabiSabi";

function ChatBubble({ role, content }) {
  const isUser = role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: "0.75rem",
      }}
    >
      <Box
        sx={{
          maxWidth: "75%",
          p: 2,
          borderRadius: isUser
            ? "1rem 1rem 0.25rem 1rem"
            : "1rem 1rem 1rem 0.25rem",
          bgcolor: isUser
            ? "rgba(92, 75, 63, 0.08)"
            : "rgba(139, 154, 127, 0.1)",
          border: `1px solid ${isUser ? "rgba(92,75,63,0.06)" : "rgba(139,154,127,0.15)"}`,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            display: "block", mb: 0.5, fontWeight: 600,
            color: isUser ? "#5C4B3F" : "#576450",
          }}
        >
          {isUser ? "You" : "GenomeInsight AI"}
        </Typography>
        <Typography
          variant="body2"
          sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6, color: "text.primary" }}
        >
          {content}
        </Typography>
      </Box>
    </motion.div>
  );
}

export default function AIChat() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  // Load sessions on mount
  useEffect(() => {
    chatAPI.listSessions()
      .then(({ data }) => {
        const list = data.sessions || [];
        setSessions(list);
        if (list.length > 0) {
          setSessionId(list[0].session_id);
        }
      })
      .catch(() => {});
  }, []);

  // Load history when session changes
  useEffect(() => {
    if (!sessionId) return;
    chatAPI.getHistory(sessionId)
      .then(({ data }) => setMessages(data.messages || []))
      .catch(() => {});
  }, [sessionId]);

  // Scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = useCallback(async () => {
    const text = message.trim();
    if (!text || sending) return;

    setMessage("");
    setSending(true);
    setError("");

    // Optimistic user message
    setMessages((prev) => [...prev, { role: "user", content: text, id: `tmp-${Date.now()}` }]);

    try {
      const { data } = await chatAPI.sendMessage(text, sessionId);
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response, id: `ai-${Date.now()}` },
      ]);
    } catch (err) {
      if (err.response?.status === 403) {
        setError("Premium subscription required to use AI Chat.");
      } else {
        setError(err.response?.data?.error || "Failed to send message.");
      }
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== `tmp-${Date.now()}`));
    } finally {
      setSending(false);
    }
  }, [message, sessionId, sending]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewSession = () => {
    setSessionId(null);
    setMessages([]);
  };

  const handleDeleteSession = async () => {
    if (!sessionId) return;
    try {
      await chatAPI.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setSessionId(null);
      setMessages([]);
    } catch {
      setError("Failed to delete session.");
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 6, mb: 8 }}>
      <motion.div {...staggerChild}>
        <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>Health AI</Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", fontStyle: "italic", mb: 4, maxWidth: "50ch" }}
        >
          A quiet conversation about your health — ask anything about your data
        </Typography>
      </motion.div>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Session controls */}
      <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap", alignItems: "center" }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={handleNewSession}
          sx={{ borderColor: "rgba(92,75,63,0.15)" }}
        >
          New Chat
        </Button>
        {sessionId && (
          <IconButton size="small" onClick={handleDeleteSession} sx={{ color: "text.disabled" }}>
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        )}
        <Box sx={{ flex: 1 }} />
        {sessions.length > 0 && (
          <Box sx={{ display: "flex", gap: 0.5, overflowX: "auto" }}>
            {sessions.slice(0, 5).map((s) => (
              <Chip
                key={s.session_id}
                label={`${new Date(s.started_at).toLocaleDateString()} (${s.message_count})`}
                size="small"
                variant={s.session_id === sessionId ? "filled" : "outlined"}
                onClick={() => setSessionId(s.session_id)}
                sx={{
                  cursor: "pointer",
                  borderColor: "rgba(92,75,63,0.12)",
                  ...(s.session_id === sessionId && {
                    bgcolor: "rgba(92,75,63,0.08)",
                    color: "#5C4B3F",
                  }),
                }}
              />
            ))}
          </Box>
        )}
      </Box>

      {/* Chat area */}
      <Card
        elevation={0}
        sx={{
          display: "flex", flexDirection: "column",
          height: { xs: "60vh", md: "65vh" },
          overflow: "hidden",
        }}
      >
        {/* Messages */}
        <Box
          ref={scrollRef}
          sx={{
            flex: 1, overflowY: "auto", p: 3,
            "&::-webkit-scrollbar": { width: 4 },
            "&::-webkit-scrollbar-thumb": { bgcolor: "rgba(92,75,63,0.12)", borderRadius: 2 },
          }}
        >
          {messages.length === 0 && (
            <Box sx={{ textAlign: "center", py: 8 }}>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                Ask about your health data
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, justifyContent: "center" }}>
                {[
                  "What does my cholesterol level mean?",
                  "How is my biological age calculated?",
                  "What should I improve first?",
                  "Explain my microbiome results",
                ].map((q) => (
                  <Chip
                    key={q}
                    label={q}
                    size="small"
                    variant="outlined"
                    onClick={() => { setMessage(q); }}
                    sx={{ cursor: "pointer", borderColor: "rgba(139,154,127,0.3)", color: "#576450" }}
                  />
                ))}
              </Box>
            </Box>
          )}
          {messages.map((m, i) => (
            <ChatBubble key={m.id || i} role={m.role} content={m.content} />
          ))}
          {sending && (
            <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 1 }}>
              <Box sx={{ p: 2, borderRadius: "1rem 1rem 1rem 0.25rem", bgcolor: "rgba(139,154,127,0.1)" }}>
                <CircularProgress size={18} sx={{ color: "#8B9A7F" }} />
              </Box>
            </Box>
          )}
        </Box>

        {/* Input */}
        <Box sx={{ p: 2, borderTop: "1px solid rgba(92,75,63,0.06)" }}>
          <TextField
            fullWidth
            multiline
            maxRows={3}
            placeholder="Ask about your health data..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleSend}
                    disabled={!message.trim() || sending}
                    sx={{ color: message.trim() ? "#5C4B3F" : "text.disabled" }}
                  >
                    <SendIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
            sx={{
              "& .MuiOutlinedInput-root": {
                borderRadius: "0.75rem",
                bgcolor: "rgba(255,255,255,0.5)",
              },
            }}
          />
          <Typography variant="caption" color="text.disabled" sx={{ display: "block", mt: 0.5, textAlign: "center" }}>
            AI assistant — not medical advice. Always consult a healthcare provider.
          </Typography>
        </Box>
      </Card>
    </Container>
  );
}
