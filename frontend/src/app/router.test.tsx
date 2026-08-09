import { render, screen } from "@testing-library/react";

import { App } from "./App";
import { createAppRouter } from "./router";
import { createTestAuth } from "../test/auth";

describe("authenticated application routing", () => {
  it("renders an authenticated route inside the application shell", async () => {
    const router = createAppRouter(["/products"]);
    render(<App auth={createTestAuth({ roles: ["customer"] })} router={router} />);

    expect(await screen.findByRole("heading", { name: "Product Catalogue" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/products");
  });

  it("redirects an unauthenticated visitor to sign in", async () => {
    const router = createAppRouter(["/dashboard"]);
    render(<App auth={createTestAuth({ authenticated: false, user: null })} router={router} />);

    expect(
      await screen.findByRole("heading", { name: "Sign in to ShopSphere Global" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("denies customer administration to a customer role", async () => {
    const router = createAppRouter(["/customer-administration"]);
    render(<App auth={createTestAuth({ roles: ["customer"] })} router={router} />);

    expect(
      await screen.findByRole("heading", { name: "Access not authorized" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/unauthorized");
  });
});
