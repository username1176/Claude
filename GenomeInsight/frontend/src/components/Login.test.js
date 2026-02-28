import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "./Login";
import { AuthProvider } from "../contexts/AuthContext";
import { authAPI } from "../services/api";

jest.mock("../services/api");

const renderLogin = () =>
  render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>
  );

describe("Login", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the sign-in form", () => {
    renderLogin();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows the GenomeInsight branding", () => {
    renderLogin();
    expect(screen.getByText("GenomeInsight")).toBeInTheDocument();
  });

  it("has a link to the register page", () => {
    renderLogin();
    expect(screen.getByText(/create one/i)).toBeInTheDocument();
  });

  it("calls login on form submit", async () => {
    authAPI.login.mockResolvedValue({
      data: { access_token: "tok", refresh_token: "ref", email: "a@b.com" },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(authAPI.login).toHaveBeenCalledWith("user@example.com", "password123");
    });
  });

  it("displays an error on failed login", async () => {
    authAPI.login.mockRejectedValue({
      response: { data: { error: "Invalid credentials" } },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "bad@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });
});
