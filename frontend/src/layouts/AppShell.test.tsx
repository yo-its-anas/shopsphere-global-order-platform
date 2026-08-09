import { render, screen } from "@testing-library/react";

import { App } from "../app/App";
import { createAppRouter } from "../app/router";
import { createTestAuth } from "../test/auth";

describe("role-aware navigation", () => {
  it("shows customer self-service links without administration for customers", async () => {
    render(
      <App
        auth={createTestAuth({ roles: ["customer"] })}
        router={createAppRouter(["/dashboard"])}
      />,
    );

    expect(await screen.findByRole("link", { name: "My Profile" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Addresses" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Customer Administration" })).not.toBeInTheDocument();
  });

  it("shows administration without customer self-service for support", async () => {
    render(
      <App
        auth={createTestAuth({ roles: ["support"] })}
        router={createAppRouter(["/dashboard"])}
      />,
    );

    expect(
      await screen.findByRole("link", { name: "Customer Administration" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "My Profile" })).not.toBeInTheDocument();
  });
});
