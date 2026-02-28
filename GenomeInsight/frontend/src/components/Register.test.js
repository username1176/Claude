import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Register from "./Register";
import { AuthProvider } from "../contexts/AuthContext";
import { authAPI } from "../services/api";

jest.mock("../services/api");

const renderRegister = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Register />
      </AuthProvider>
    </MemoryRouter>
  );

describe("Register", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the create account form", () => {
    renderRegister();
    expect(screen.getByText("Create Account")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows error when password is too short", async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "u@e.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "short" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it("shows error when passwords do not match", async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "u@e.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });

  it("calls register on valid submit", async () => {
    authAPI.register.mockResolvedValue({ data: {} });
    authAPI.login.mockResolvedValue({
      data: { access_token: "tok", refresh_token: "ref" },
    });

    renderRegister();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "securepass1" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "securepass1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(authAPI.register).toHaveBeenCalledWith("new@example.com", "securepass1");
    });
  });

  it("has a link to the login page", () => {
    renderRegister();
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });
});
