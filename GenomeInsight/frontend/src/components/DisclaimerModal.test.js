import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DisclaimerModal from "./DisclaimerModal";

describe("DisclaimerModal", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("opens the modal when disclaimer has not been accepted", () => {
    render(<DisclaimerModal />);
    expect(screen.getByText("Important Medical Disclaimer")).toBeInTheDocument();
  });

  it("does not show the modal when already accepted", () => {
    localStorage.setItem("genomeinsight_disclaimer_accepted", new Date().toISOString());
    render(<DisclaimerModal />);
    expect(screen.queryByText("Important Medical Disclaimer")).not.toBeInTheDocument();
  });

  it("disables the continue button until checkbox is checked", () => {
    render(<DisclaimerModal />);
    const btn = screen.getByRole("button", { name: /i understand/i });
    expect(btn).toBeDisabled();
  });

  it("enables the continue button once checkbox is checked", () => {
    render(<DisclaimerModal />);
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    const btn = screen.getByRole("button", { name: /i understand/i });
    expect(btn).toBeEnabled();
  });

  it("stores acceptance in localStorage and closes modal on accept", async () => {
    render(<DisclaimerModal />);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: /i understand/i }));

    await waitFor(() => {
      expect(localStorage.getItem("genomeinsight_disclaimer_accepted")).toBeTruthy();
    });
  });

  it("shows key disclaimer text about not being medical advice", () => {
    render(<DisclaimerModal />);
    expect(screen.getByText(/NOT medical advice/i)).toBeInTheDocument();
  });
});
