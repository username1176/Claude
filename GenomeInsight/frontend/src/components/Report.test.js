import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Report from "./Report";
import { AuthProvider } from "../contexts/AuthContext";
import { genomeAPI } from "../services/api";

jest.mock("../services/api");

// Mock recharts
jest.mock("recharts", () => ({
  RadarChart: ({ children }) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Cell: () => null,
}));

const renderReport = (analysisId = "test-123") =>
  render(
    <MemoryRouter initialEntries={[`/report/${analysisId}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/report/:analysisId" element={<Report />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );

describe("Report", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows loading state initially", () => {
    genomeAPI.getUpload.mockReturnValue(new Promise(() => {}));
    genomeAPI.getAnalysis.mockReturnValue(new Promise(() => {}));
    genomeAPI.getRisks.mockReturnValue(new Promise(() => {}));
    genomeAPI.getRecommendations.mockReturnValue(new Promise(() => {}));

    renderReport();
    expect(screen.getByText("Loading report...")).toBeInTheDocument();
  });

  it("shows error on fetch failure", async () => {
    genomeAPI.getUpload.mockRejectedValue(new Error("Not found"));
    genomeAPI.getAnalysis.mockRejectedValue(new Error("Not found"));
    genomeAPI.getRisks.mockRejectedValue(new Error("Not found"));
    genomeAPI.getRecommendations.mockRejectedValue(new Error("Not found"));

    renderReport();

    await waitFor(() => {
      expect(screen.getByText(/failed to load report/i)).toBeInTheDocument();
    });
  });

  it("renders risk overview tab with data", async () => {
    genomeAPI.getUpload.mockRejectedValue(new Error("nope"));
    genomeAPI.getAnalysis.mockResolvedValue({
      data: {
        status: "complete",
        variant_count: 500000,
        annotated_variant_count: 1200,
        completed_at: "2025-01-15T12:00:00Z",
      },
    });
    genomeAPI.getRisks.mockResolvedValue({
      data: {
        risk_categories: {
          cardiovascular: {
            label: "Cardiovascular Health",
            score: 6.5,
            level: "elevated",
            key_variants: [],
          },
          metabolic: {
            label: "Metabolic Health",
            score: 3.2,
            level: "low",
            key_variants: [],
          },
        },
      },
    });
    genomeAPI.getRecommendations.mockResolvedValue({
      data: { recommendations: [] },
    });
    genomeAPI.getReport.mockRejectedValue(new Error("not ready"));

    renderReport();

    await waitFor(() => {
      expect(screen.getByText("Genome Analysis Report")).toBeInTheDocument();
    });
    expect(screen.getByText("500,000")).toBeInTheDocument();
    expect(screen.getByText("Cardiovascular Health")).toBeInTheDocument();
    expect(screen.getByText("Metabolic Health")).toBeInTheDocument();
  });

  it("shows disclaimer at the bottom", async () => {
    genomeAPI.getUpload.mockRejectedValue(new Error("nope"));
    genomeAPI.getAnalysis.mockResolvedValue({
      data: { status: "complete", variant_count: 100 },
    });
    genomeAPI.getRisks.mockResolvedValue({ data: { risk_categories: {} } });
    genomeAPI.getRecommendations.mockResolvedValue({
      data: { recommendations: [] },
    });
    genomeAPI.getReport.mockRejectedValue(new Error("not ready"));

    renderReport();

    await waitFor(() => {
      expect(screen.getByText(/disclaimer/i)).toBeInTheDocument();
    });
  });

  it("shows pending analysis alert", async () => {
    genomeAPI.getUpload.mockRejectedValue(new Error("nope"));
    genomeAPI.getAnalysis.mockResolvedValue({
      data: { status: "analyzing", variant_count: 100 },
    });
    genomeAPI.getRisks.mockResolvedValue({ data: { risk_categories: {} } });
    genomeAPI.getRecommendations.mockResolvedValue({ data: { recommendations: [] } });
    genomeAPI.getReport.mockRejectedValue(new Error("not ready"));

    renderReport();

    await waitFor(() => {
      expect(screen.getByText(/analysis is still running/i)).toBeInTheDocument();
    });
  });
});
