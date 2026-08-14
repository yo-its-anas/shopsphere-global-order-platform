import { vi } from "vitest";

import type { ApiClient } from "./apiClient";
import { OrderApi } from "./orderApi";

describe("OrderApi Gateway contract", () => {
  it("uses fixed Gateway paths for add, clear, and operational transitions", async () => {
    const request = vi.fn().mockResolvedValue({});
    const api = new OrderApi({ request } as ApiClient);

    await api.addItem("product/id", 2);
    await api.clearCart();
    await api.transition("order/id", "PROCESSING");

    expect(request).toHaveBeenNthCalledWith(1, "/carts/me/items", {
      method: "POST",
      body: JSON.stringify({ product_id: "product/id", quantity: 2 }),
    });
    expect(request).toHaveBeenNthCalledWith(2, "/carts/me/items", { method: "DELETE" });
    expect(request).toHaveBeenNthCalledWith(3, "/orders/admin/order%2Fid/status", {
      method: "POST",
      body: JSON.stringify({ target_status: "PROCESSING" }),
    });
  });

  it("forwards the caller-owned idempotency key without replacement", async () => {
    const request = vi.fn().mockResolvedValue({});
    const api = new OrderApi({ request } as ApiClient);
    await api.checkout("checkout-stable-test-key");
    expect(request).toHaveBeenCalledWith("/orders/checkout", {
      method: "POST",
      headers: { "Idempotency-Key": "checkout-stable-test-key" },
    });
  });
});
