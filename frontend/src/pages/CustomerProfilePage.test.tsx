import { render, screen } from "@testing-library/react";

import { App } from "../app/App";
import { createAppRouter } from "../app/router";
import { createTestAuth, jsonResponse } from "../test/auth";

const profile = {
  id: "50eb502c-d53b-471f-a61c-8d67976bb72d",
  first_name: "Amina",
  last_name: "Khan",
  email: "amina@example.invalid",
  phone: "+92 300 1234567",
  status: "active",
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

describe("customer profile", () => {
  it("renders a profile loaded through the gateway API client", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(profile));
    render(
      <App auth={createTestAuth({ roles: ["customer"] })} router={createAppRouter(["/profile"])} />,
    );

    expect(await screen.findByRole("heading", { name: "Amina Khan" })).toBeInTheDocument();
    expect(screen.getByText("amina@example.invalid")).toBeInTheDocument();
    const request = fetchMock.mock.calls[0];
    expect(String(request?.[0])).toContain("/api/v1/customers/me");
    const headers = new Headers(request?.[1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-access-token");
  });

  it("shows an API unavailable state without leaking internal details", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("connection refused at internal host"),
    );
    render(
      <App auth={createTestAuth({ roles: ["customer"] })} router={createAppRouter(["/profile"])} />,
    );

    expect(await screen.findByRole("heading", { name: "Profile unavailable" })).toBeInTheDocument();
    expect(screen.getByText("The API Gateway is unavailable.")).toBeInTheDocument();
    expect(screen.queryByText(/internal host/i)).not.toBeInTheDocument();
  });
});
