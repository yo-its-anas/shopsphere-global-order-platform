import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { App } from "../../app/App";
import { createAppRouter } from "../../app/router";
import { createTestAuth, jsonResponse } from "../../test/auth";
import type {
  CartItem,
  OrderConfirmation,
  OrderHistory,
  OrderPage,
  ShoppingCart,
} from "../../types/order";

const cartItem: CartItem = {
  id: "20000000-0000-4000-8000-000000000001",
  product_id: "30000000-0000-4000-8000-000000000001",
  quantity: 2,
  display_sku: "TEST-SKU-1",
  display_name: "Simulated Product",
  display_unit_price: "12.5000",
  display_currency_code: "USD",
  display_quantity_available: 20,
  display_line_subtotal: "25.0000",
  snapshot_at: "2026-08-14T08:00:00Z",
  created_at: "2026-08-14T08:00:00Z",
  updated_at: "2026-08-14T08:00:00Z",
};

const cart: ShoppingCart = {
  id: "10000000-0000-4000-8000-000000000001",
  status: "ACTIVE",
  currency_code: "USD",
  version: 3,
  items: [cartItem],
  item_count: 2,
  display_subtotal: "25.0000",
  pricing_authoritative: false,
  pricing_notice: "Display estimate only. Prices and availability are revalidated at checkout.",
  created_at: "2026-08-14T08:00:00Z",
  updated_at: "2026-08-14T08:00:00Z",
};

const emptyCart: ShoppingCart = { ...cart, items: [], item_count: 0, display_subtotal: "0.0000" };

const confirmation: OrderConfirmation = {
  order_id: "40000000-0000-4000-8000-000000000001",
  order_number: "ORD-20260814-TEST01",
  status: "CONFIRMED",
  items: [
    {
      product_id: cartItem.product_id,
      sku: "TEST-SKU-1",
      product_name: "Simulated Product",
      quantity: 2,
      unit_price: "13.0000",
      currency_code: "USD",
      line_total: "26.0000",
    },
  ],
  currency_code: "USD",
  subtotal: "26.0000",
  total: "26.0000",
  created_at: "2026-08-14T08:05:00Z",
  payment_status: "not_in_scope",
};

const orderPage: OrderPage = {
  items: [
    {
      order_id: confirmation.order_id,
      order_number: confirmation.order_number,
      status: confirmation.status,
      currency_code: confirmation.currency_code,
      total: confirmation.total,
      created_at: confirmation.created_at,
      updated_at: confirmation.created_at,
    },
  ],
  offset: 0,
  limit: 20,
  total: 1,
};

const history: OrderHistory = {
  order_id: confirmation.order_id,
  current_status: "CONFIRMED",
  items: [
    {
      status: "CONFIRMED",
      actor_subject: "customer:self",
      correlation_id: "request-test-1",
      occurred_at: confirmation.created_at,
    },
  ],
};

function customerApp(path: string) {
  return render(
    <App auth={createTestAuth({ roles: ["customer"] })} router={createAppRouter([path])} />,
  );
}

describe("order customer experience", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders the empty-cart state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(emptyCart));
    customerApp("/cart");
    expect(await screen.findByRole("heading", { name: "Your cart is empty" })).toBeInTheDocument();
  });

  it("updates and removes cart items through Gateway paths", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(cart))
      .mockResolvedValueOnce(
        jsonResponse({ ...cart, version: 4, items: [{ ...cartItem, quantity: 3 }] }),
      )
      .mockResolvedValueOnce(jsonResponse(emptyCart));
    const user = userEvent.setup();
    customerApp("/cart");

    await user.click(
      await screen.findByRole("button", { name: "Increase Simulated Product quantity" }),
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const updateCall = fetchMock.mock.calls.at(1)!;
    expect(updateCall[0]).toContain(`/carts/me/items/${cartItem.id}`);
    expect((updateCall[1]?.method ?? "").toUpperCase()).toBe("PATCH");

    await user.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Your cart is empty" })).toBeInTheDocument(),
    );
    const removeCall = fetchMock.mock.calls.at(2)!;
    expect((removeCall[1]?.method ?? "").toUpperCase()).toBe("DELETE");
  });

  it("renders the server-calculated checkout confirmation", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(cart))
      .mockResolvedValueOnce(jsonResponse(confirmation, 201));
    const user = userEvent.setup();
    customerApp("/checkout");

    await user.click(await screen.findByRole("button", { name: "Place order" }));
    expect(await screen.findByRole("heading", { name: "Order Confirmed" })).toBeInTheDocument();
    expect(screen.getByText(confirmation.order_number)).toBeInTheDocument();
    expect(screen.getAllByText("$26.00").length).toBeGreaterThan(0);
  });

  it("preserves the checkout idempotency key for a timeout retry", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(cart))
      .mockRejectedValueOnce(new TypeError("network timeout"))
      .mockRejectedValueOnce(new TypeError("network timeout"));
    const user = userEvent.setup();
    customerApp("/checkout");

    await user.click(await screen.findByRole("button", { name: "Place order" }));
    await user.click(await screen.findByRole("button", { name: "Retry safely" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    const firstHeaders = new Headers(fetchMock.mock.calls.at(1)![1]?.headers);
    const retryHeaders = new Headers(fetchMock.mock.calls.at(2)![1]?.headers);
    expect(firstHeaders.get("Idempotency-Key")).toMatch(/^checkout-/);
    expect(retryHeaders.get("Idempotency-Key")).toBe(firstHeaders.get("Idempotency-Key"));
    expect(screen.getByText(/outcome may be unknown/i)).toBeInTheDocument();
  });

  it("shows the stock or price revalidation conflict flow", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(cart))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: { code: "product_unavailable", message: "The product is no longer available." },
          },
          409,
        ),
      );
    const user = userEvent.setup();
    customerApp("/checkout");
    await user.click(await screen.findByRole("button", { name: "Place order" }));
    expect(
      await screen.findByText(/stock, product availability, or pricing changed/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry safely" })).not.toBeInTheDocument();
  });

  it("renders order history and details with the status timeline", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/history")) return jsonResponse(history);
      if (url.includes(`/orders/me/${confirmation.order_id}`)) return jsonResponse(confirmation);
      return jsonResponse(orderPage);
    });

    const list = customerApp("/orders");
    expect(await screen.findByText(confirmation.order_number)).toBeInTheDocument();
    list.unmount();

    customerApp(`/orders/${confirmation.order_id}`);
    expect(
      await screen.findByRole("heading", { name: `Order ${confirmation.order_number}` }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Status timeline" })).toBeInTheDocument();
    expect(screen.getByText("customer:self")).toBeInTheDocument();
    expect(screen.getByText("$13.00")).toBeInTheDocument();
  });

  it("shows an unavailable state without exposing request internals", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("secret internal endpoint"));
    customerApp("/orders");
    expect(await screen.findByText("The API Gateway is unavailable.")).toBeInTheDocument();
    expect(screen.queryByText(/secret internal endpoint/i)).not.toBeInTheDocument();
  });

  it("denies order management to a customer role", async () => {
    const router = createAppRouter(["/order-management"]);
    render(<App auth={createTestAuth({ roles: ["customer"] })} router={router} />);
    expect(
      await screen.findByRole("heading", { name: "Access not authorized" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/unauthorized");
  });

  it("keeps support order management read-only", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/history")) return jsonResponse(history);
      if (url.endsWith("/audit")) {
        return jsonResponse({
          order_id: confirmation.order_id,
          items: [],
          offset: 0,
          limit: 25,
          total: 0,
        });
      }
      return jsonResponse(confirmation);
    });
    render(
      <App
        auth={createTestAuth({ roles: ["support"] })}
        router={createAppRouter([`/order-management/${confirmation.order_id}`])}
      />,
    );
    expect(await screen.findByText(/operational read access does not grant/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Process order" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel order" })).not.toBeInTheDocument();
  });
});
