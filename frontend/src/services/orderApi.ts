import type { ApiClient } from "./apiClient";
import type {
  OrderAuditPage,
  OrderConfirmation,
  OrderHistory,
  OrderPage,
  OrderStatus,
  OrderSummary,
  ShoppingCart,
} from "../types/order";

function queryString(values: Record<string, string | number | undefined>): string {
  const parameters = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") parameters.set(key, String(value));
  });
  const encoded = parameters.toString();
  return encoded ? `?${encoded}` : "";
}

export interface OrderListParameters {
  status?: OrderStatus | "";
  customerSubject?: string;
  offset?: number;
  limit?: number;
  sort?: "created_at_desc" | "created_at_asc";
}

export class OrderApi {
  constructor(private readonly client: ApiClient) {}

  getCart(): Promise<ShoppingCart> {
    return this.client.request("/carts/me");
  }

  addItem(productId: string, quantity: number): Promise<ShoppingCart> {
    return this.client.request("/carts/me/items", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    });
  }

  updateItem(itemId: string, quantity: number): Promise<ShoppingCart> {
    return this.client.request(`/carts/me/items/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    });
  }

  removeItem(itemId: string): Promise<ShoppingCart> {
    return this.client.request(`/carts/me/items/${encodeURIComponent(itemId)}`, {
      method: "DELETE",
    });
  }

  clearCart(): Promise<ShoppingCart> {
    return this.client.request("/carts/me/items", { method: "DELETE" });
  }

  checkout(idempotencyKey: string): Promise<OrderConfirmation> {
    return this.client.request("/orders/checkout", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  }

  listMyOrders(parameters: OrderListParameters = {}): Promise<OrderPage> {
    return this.client.request(
      `/orders/me${queryString({
        status: parameters.status,
        offset: parameters.offset,
        limit: parameters.limit,
        sort: parameters.sort,
      })}`,
    );
  }

  getMyOrder(orderId: string): Promise<OrderConfirmation> {
    return this.client.request(`/orders/me/${encodeURIComponent(orderId)}`);
  }

  getMyHistory(orderId: string): Promise<OrderHistory> {
    return this.client.request(`/orders/me/${encodeURIComponent(orderId)}/history`);
  }

  cancelMyOrder(orderId: string): Promise<OrderSummary> {
    return this.client.request(`/orders/me/${encodeURIComponent(orderId)}/cancellation`, {
      method: "POST",
    });
  }

  listOperationalOrders(parameters: OrderListParameters = {}): Promise<OrderPage> {
    return this.client.request(
      `/orders/admin${queryString({
        customer_subject: parameters.customerSubject,
        status: parameters.status,
        offset: parameters.offset,
        limit: parameters.limit,
        sort: parameters.sort,
      })}`,
    );
  }

  getOperationalOrder(orderId: string): Promise<OrderConfirmation> {
    return this.client.request(`/orders/admin/${encodeURIComponent(orderId)}`);
  }

  getOperationalHistory(orderId: string): Promise<OrderHistory> {
    return this.client.request(`/orders/admin/${encodeURIComponent(orderId)}/history`);
  }

  getOperationalAudit(orderId: string): Promise<OrderAuditPage> {
    return this.client.request(`/orders/admin/${encodeURIComponent(orderId)}/audit`);
  }

  transition(orderId: string, targetStatus: "PROCESSING" | "FULFILLED"): Promise<OrderSummary> {
    return this.client.request(`/orders/admin/${encodeURIComponent(orderId)}/status`, {
      method: "POST",
      body: JSON.stringify({ target_status: targetStatus }),
    });
  }

  cancelOperationalOrder(orderId: string): Promise<OrderSummary> {
    return this.client.request(`/orders/admin/${encodeURIComponent(orderId)}/cancellation`, {
      method: "POST",
    });
  }
}
