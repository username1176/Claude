import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import BloodUpload from "./BloodUpload";
import { AuthProvider } from "../contexts/AuthContext";
import { bloodAPI } from "../services/api";

jest.mock("../services/api");

const renderBloodUpload = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <BloodUpload />
      </AuthProvider>
    </MemoryRouter>
  );

describe("BloodUpload", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the upload page", () => {
    renderBloodUpload();
    expect(screen.getByText("Upload Blood Test")).toBeInTheDocument();
    expect(screen.getByText(/drag & drop your blood test file/i)).toBeInTheDocument();
  });

  it("shows test date and lab name fields", () => {
    renderBloodUpload();
    expect(screen.getByLabelText(/test date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lab name/i)).toBeInTheDocument();
  });

  it("disables upload button when no file is selected", () => {
    renderBloodUpload();
    const btn = screen.getByRole("button", { name: /upload & parse/i });
    expect(btn).toBeDisabled();
  });

  it("shows success view after upload", async () => {
    bloodAPI.upload.mockResolvedValue({
      data: { message: "Parsed OK", status: "parsed", markers_parsed: 15 },
    });

    renderBloodUpload();

    const file = new File(["marker,value\nHGB,14.2"], "blood.csv", {
      type: "text/csv",
    });
    const dropzone = screen.getByText(/drag & drop your blood test file/i).closest("div");
    const input = dropzone.querySelector("input");
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /upload & parse/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: /upload & parse/i }));

    await waitFor(() => {
      expect(screen.getByText("Upload Successful!")).toBeInTheDocument();
      expect(screen.getByText("15 markers parsed")).toBeInTheDocument();
    });
  });

  it("shows error on upload failure", async () => {
    bloodAPI.upload.mockRejectedValue({
      response: { data: { error: "Invalid CSV format." } },
    });

    renderBloodUpload();

    const file = new File(["bad data"], "test.csv", { type: "text/csv" });
    const dropzone = screen.getByText(/drag & drop your blood test file/i).closest("div");
    const input = dropzone.querySelector("input");
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /upload & parse/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: /upload & parse/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid CSV format.")).toBeInTheDocument();
    });
  });
});
