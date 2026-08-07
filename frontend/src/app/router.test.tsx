import { render, screen } from "@testing-library/react";
import { RouterProvider } from "react-router-dom";

import { createAppRouter } from "./router";

describe("application routing", () => {
  it("renders a requested placeholder route inside the application shell", async () => {
    const router = createAppRouter(["/products"]);

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "Product Catalogue" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Product Catalogue is not connected" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/products");
  });
});
