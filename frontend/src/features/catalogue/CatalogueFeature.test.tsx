import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "../../app/App";
import { createAppRouter } from "../../app/router";
import { createTestAuth, jsonResponse } from "../../test/auth";
import type { ShopSphereRole } from "../../types/auth";

const productId = "11111111-1111-4111-8111-111111111111";
const categoryId = "22222222-2222-4222-8222-222222222222";
const inventoryId = "33333333-3333-4333-8333-333333333333";
const now = "2026-08-12T10:00:00Z";

const category = {
  id: categoryId,
  name: "Enterprise Hardware",
  slug: "enterprise-hardware",
  description: "Managed equipment",
  is_active: true,
  parent_id: null,
  created_at: now,
  updated_at: now,
};

const product = {
  id: productId,
  sku: "ENT-LAPTOP-01",
  name: "Enterprise Laptop",
  description: "Managed workstation",
  category_id: categoryId,
  status: "active",
  is_searchable: true,
  created_at: now,
  updated_at: now,
};

const inventory = {
  id: inventoryId,
  product_id: productId,
  location_code: "PRIMARY",
  quantity_on_hand: 20,
  quantity_reserved: 3,
  quantity_available: 17,
  reorder_threshold: 5,
  state: "in_stock",
  version: 4,
  created_at: now,
  updated_at: now,
};

const movement = {
  id: "44444444-4444-4444-8444-444444444444",
  inventory_item_id: inventoryId,
  product_id: productId,
  movement_type: "STOCK_RECEIPT",
  quantity_delta: 5,
  reserved_delta: 0,
  previous_quantity_on_hand: 15,
  resulting_quantity_on_hand: 20,
  previous_quantity_reserved: 3,
  resulting_quantity_reserved: 3,
  reason: "Approved supplier receipt",
  reference: "PO-TEST-100",
  actor_subject: "simulated-operator",
  correlation_id: "test-correlation-100",
  idempotency_key: "test-adjustment-100",
  occurred_at: now,
};

function renderRoute(path: string, roles: ShopSphereRole[]) {
  return render(<App auth={createTestAuth({ roles })} router={createAppRouter([path])} />);
}

function installSuccessfulApi() {
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    requests.push({ url, init });
    const method = init?.method ?? "GET";

    if (url.includes(`/products/${productId}/prices/`) && method === "PUT") {
      return jsonResponse({
        id: "55555555-5555-4555-8555-555555555555",
        product_id: productId,
        amount: "1499.9900",
        currency_code: "USD",
        is_active: true,
        effective_from: now,
        effective_to: null,
        created_at: now,
        updated_at: now,
      });
    }
    if (url.includes(`/products/${productId}/prices`)) {
      return jsonResponse({
        items: [
          {
            id: "55555555-5555-4555-8555-555555555555",
            product_id: productId,
            amount: "1299.0000",
            currency_code: "USD",
            is_active: true,
            effective_from: now,
            effective_to: null,
            created_at: now,
            updated_at: now,
          },
        ],
      });
    }
    if (url.includes(`/inventory/products/${productId}/availability`)) {
      return jsonResponse({
        product_id: productId,
        quantity_available: 17,
        state: "in_stock",
        as_of: now,
      });
    }
    if (url.includes(`/inventory/products/${productId}/adjustments`) && method === "POST") {
      return jsonResponse({
        inventory: { ...inventory, quantity_on_hand: 25, version: 5 },
        movement,
      });
    }
    if (url.includes(`/inventory/products/${productId}/movements`)) {
      return jsonResponse({ items: [movement], offset: 0, limit: 25, total: 1 });
    }
    if (url.endsWith(`/inventory/products/${productId}`)) return jsonResponse(inventory);
    if (url.endsWith("/inventory/statistics")) {
      return jsonResponse({
        location_code: "PRIMARY",
        total_products_tracked: 12,
        in_stock_products: 9,
        low_stock_products: 2,
        out_of_stock_products: 1,
        total_units_on_hand: 420,
        reserved_units: 20,
        available_units: 400,
        calculated_at: now,
      });
    }
    if (url.includes("/inventory?")) {
      return jsonResponse({ items: [inventory], offset: 0, limit: 25, total: 1 });
    }
    if (url.includes(`/products/${productId}`) && method === "GET") return jsonResponse(product);
    if (url.includes("/products?") && method === "GET") {
      return jsonResponse({ items: [product], offset: 0, limit: 20, total: 1 });
    }
    if (url.endsWith("/products") && method === "POST") return jsonResponse(product, 201);
    if (url.includes(`/categories/${categoryId}`)) return jsonResponse(category);
    if (url.includes("/categories?") && method === "GET") {
      return jsonResponse({ items: [category], offset: 0, limit: 100, total: 1 });
    }
    if (url.endsWith("/categories") && method === "POST") return jsonResponse(category, 201);
    throw new Error(`Unhandled test API request: ${method} ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, requests };
}

describe("catalogue and inventory capability", () => {
  it("renders products and forwards search and category filters through the gateway client", async () => {
    const { requests } = installSuccessfulApi();
    const user = userEvent.setup();
    renderRoute("/products", ["customer"]);

    expect(await screen.findByRole("link", { name: "Enterprise Laptop" })).toBeInTheDocument();
    expect(screen.getByText("USD 1299.0000")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Add product" })).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Product search" }), "laptop");
    await user.selectOptions(screen.getByRole("combobox", { name: "Category filter" }), categoryId);
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() =>
      expect(
        requests.some(
          ({ url }) =>
            url.includes("/products?") &&
            url.includes("query=laptop") &&
            url.includes(`category_id=${categoryId}`),
        ),
      ).toBe(true),
    );
  });

  it("allows an operations administrator to register a product and denies the route to customers", async () => {
    installSuccessfulApi();
    const customerRouter = createAppRouter(["/products/new"]);
    const customerView = render(
      <App auth={createTestAuth({ roles: ["customer"] })} router={customerRouter} />,
    );
    expect(
      await screen.findByRole("heading", { name: "Access not authorized" }),
    ).toBeInTheDocument();
    customerView.unmount();

    const user = userEvent.setup();
    const { requests } = installSuccessfulApi();
    renderRoute("/products/new", ["operations_admin"]);
    await screen.findByRole("heading", { name: "Register product" });
    await user.type(screen.getByRole("textbox", { name: "SKU" }), "OPS-100");
    await user.type(screen.getByRole("textbox", { name: "Product name" }), "Operations Console");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Product category" }),
      categoryId,
    );
    await user.click(screen.getByRole("button", { name: "Register product" }));
    await waitFor(() =>
      expect(
        requests.some(({ url, init }) => url.endsWith("/products") && init?.method === "POST"),
      ).toBe(true),
    );
  });

  it("supports category creation and price updates for operations administrators", async () => {
    const user = userEvent.setup();
    const { requests } = installSuccessfulApi();
    const categoryView = renderRoute("/categories", ["operations_admin"]);
    await screen.findByRole("heading", { name: "Product Categories" });
    await user.type(screen.getByRole("textbox", { name: "Category name" }), "Office Systems");
    await user.type(screen.getByRole("textbox", { name: "Category slug" }), "office-systems");
    await user.click(screen.getByRole("button", { name: "Create category" }));
    await waitFor(() =>
      expect(
        requests.some(({ url, init }) => url.endsWith("/categories") && init?.method === "POST"),
      ).toBe(true),
    );
    categoryView.unmount();

    renderRoute(`/pricing?product=${productId}`, ["operations_admin"]);
    await screen.findByRole("heading", { name: "Pricing Management" });
    await user.type(screen.getByRole("textbox", { name: "Price amount" }), "1499.9900");
    await user.click(screen.getByRole("button", { name: "Update price" }));
    await waitFor(() =>
      expect(
        requests.some(({ url, init }) => url.includes(`/prices/USD`) && init?.method === "PUT"),
      ).toBe(true),
    );
  });

  it("renders operational inventory, movement history, and persisted statistics", async () => {
    installSuccessfulApi();
    const inventoryView = renderRoute("/inventory", ["support"]);
    expect(await screen.findByRole("heading", { name: "Global Stock Levels" })).toBeInTheDocument();
    expect(screen.getByText("Enterprise Laptop")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Adjust" })).not.toBeInTheDocument();
    inventoryView.unmount();

    const movementsView = renderRoute(`/inventory/${productId}/movements`, ["support"]);
    expect(
      await screen.findByRole("heading", { name: "Inventory Movement History" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Approved supplier receipt")).toBeInTheDocument();
    expect(screen.getByText("test-correlation-100")).toBeInTheDocument();
    movementsView.unmount();

    renderRoute("/inventory/statistics", ["operations_admin"]);
    expect(
      await screen.findByRole("heading", { name: "Inventory Statistics" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("420")).toBeInTheDocument();
    expect(screen.getByText("400")).toBeInTheDocument();
  });

  it("requires confirmation before submitting an inventory adjustment", async () => {
    const user = userEvent.setup();
    const { requests } = installSuccessfulApi();
    renderRoute(`/inventory/${productId}/adjust`, ["operations_admin"]);
    await screen.findByRole("heading", { name: "Record Inventory Adjustment" });
    await user.clear(screen.getByRole("spinbutton", { name: "Adjustment quantity" }));
    await user.type(screen.getByRole("spinbutton", { name: "Adjustment quantity" }), "5");
    await user.type(screen.getByRole("textbox", { name: "Adjustment reason" }), "Approved receipt");
    await user.click(screen.getByRole("button", { name: "Review adjustment" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirm stock change" });
    expect(requests.some(({ init }) => init?.method === "POST")).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Confirm adjustment" }));
    await waitFor(() =>
      expect(
        requests.some(({ url, init }) => url.includes("/adjustments") && init?.method === "POST"),
      ).toBe(true),
    );
  });

  it("shows safe API failures and blocks customer access to operational inventory", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "internal detail" }), {
            status: 503,
            headers: {
              "Content-Type": "application/json",
              "X-Request-ID": "safe-request-42",
            },
          }),
      ),
    );
    const failedView = renderRoute("/products", ["customer"]);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("safe-request-42");
    expect(screen.queryByText("internal detail")).not.toBeInTheDocument();
    failedView.unmount();

    const denied = renderRoute("/inventory", ["customer"]);
    expect(
      await screen.findByRole("heading", { name: "Access not authorized" }),
    ).toBeInTheDocument();
    denied.unmount();
  });
});
