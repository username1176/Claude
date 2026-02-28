import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard";
import { AuthProvider } from "../contexts/AuthContext";
import { genomeAPI, bloodAPI } from "../services/api";

jest.mock("../services/api");

// Mock recharts to avoid rendering issues in jsdom
jest.mock("recharts", () => ({
  LineChart: ({ children }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  ReferenceLine: () => null,
}));

const renderDashboard = () => {
  // Set up auth so ProtectedRoute doesn't redirect
  localStorage.setItem("access_token", "test-token");
  localStorage.setItem("user_email", "test@test.com");
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Dashboard />
      </AuthProvider>
    </MemoryRouter>
  );
};

describe("Dashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("shows loading skeleton initially", () => {
    genomeAPI.listUploads.mockReturnValue(new Promise(() => {})); // never resolves
    bloodAPI.listUploads.mockReturnValue(new Promise(() => {}));

    renderDashboard();
    // Skeleton elements should be present during loading
    expect(document.querySelector(".MuiSkeleton-root")).toBeInTheDocument();
  });

  it("renders summary cards after data loads", async () => {
    genomeAPI.listUploads.mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] });
    bloodAPI.listUploads.mockResolvedValue({ data: [{ id: 10 }] });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
    expect(screen.getByText("2")).toBeInTheDocument(); // genome count
    expect(screen.getByText("1")).toBeInTheDocument(); // blood count
  });

  it("shows empty state for genome history", async () => {
    genomeAPI.listUploads.mockResolvedValue({ data: [] });
    bloodAPI.listUploads.mockResolvedValue({ data: [] });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
    expect(screen.getByText(/no genome uploads yet/i)).toBeInTheDocument();
  });

  it("displays error alert on API failure", async () => {
    genomeAPI.listUploads.mockRejectedValue(new Error("Network error"));
    bloodAPI.listUploads.mockRejectedValue(new Error("Network error"));

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it("renders four tabs", async () => {
    genomeAPI.listUploads.mockResolvedValue({ data: [] });
    bloodAPI.listUploads.mockResolvedValue({ data: [] });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
    expect(screen.getByText("Genome History")).toBeInTheDocument();
    expect(screen.getByText("Blood History")).toBeInTheDocument();
    expect(screen.getByText("Blood Trends")).toBeInTheDocument();
    expect(screen.getByText("Change Analysis")).toBeInTheDocument();
  });
});
