import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GenomeUpload from "./GenomeUpload";
import { AuthProvider } from "../contexts/AuthContext";
import { genomeAPI } from "../services/api";

jest.mock("../services/api");

const renderGenomeUpload = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <GenomeUpload />
      </AuthProvider>
    </MemoryRouter>
  );

describe("GenomeUpload", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the upload page", () => {
    renderGenomeUpload();
    expect(screen.getByText("Upload Genome")).toBeInTheDocument();
    expect(screen.getByText(/drag & drop your vcf file/i)).toBeInTheDocument();
  });

  it("shows a source selector", () => {
    renderGenomeUpload();
    expect(screen.getByLabelText(/genotyping service/i)).toBeInTheDocument();
  });

  it("disables upload button when no file is selected", () => {
    renderGenomeUpload();
    const btn = screen.getByRole("button", { name: /upload & analyze/i });
    expect(btn).toBeDisabled();
  });

  it("shows success view after upload", async () => {
    genomeAPI.upload.mockResolvedValue({
      data: { message: "VCF uploaded", analysis_id: "abc-123" },
    });

    renderGenomeUpload();

    // Simulate file drop
    const file = new File(["##VCF\nchr1\t100\trs1\tA\tT"], "test.vcf", {
      type: "text/plain",
    });
    const dropzone = screen.getByText(/drag & drop your vcf file/i).closest("div");
    const input = dropzone.querySelector("input");
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      const uploadBtn = screen.getByRole("button", { name: /upload & analyze/i });
      expect(uploadBtn).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() => {
      expect(screen.getByText("Upload Successful!")).toBeInTheDocument();
    });
  });

  it("shows error on upload failure", async () => {
    genomeAPI.upload.mockRejectedValue({
      response: { data: { error: "File too large." } },
    });

    renderGenomeUpload();

    const file = new File(["data"], "test.vcf", { type: "text/plain" });
    const dropzone = screen.getByText(/drag & drop your vcf file/i).closest("div");
    const input = dropzone.querySelector("input");
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /upload & analyze/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() => {
      expect(screen.getByText("File too large.")).toBeInTheDocument();
    });
  });
});
