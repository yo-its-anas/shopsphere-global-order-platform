import { render, screen } from "@testing-library/react";

import { App } from "./App";
import { createAppRouter } from "./router";
import { createTestAuth } from "../test/auth";

describe("App", () => {
  it("renders the enterprise application shell and dashboard", async () => {
    render(
      <App
        auth={createTestAuth({ roles: ["customer"] })}
        router={createAppRouter(["/dashboard"])}
      />,
    );

    expect(await screen.findByText("ShopSphere Global")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeInTheDocument();
    expect(screen.getAllByText("Demo Data").length).toBeGreaterThan(0);
  });
});
