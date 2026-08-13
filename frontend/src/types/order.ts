export type OrderStatus = "PENDING" | "CONFIRMED" | "PROCESSING" | "FULFILLED" | "CANCELLED";

export interface CartItem {
  id: string;
  product_id: string;
  quantity: number;
  display_sku: string;
  display_name: string;
  display_unit_price: string;
  display_currency_code: string;
  display_quantity_available: number | null;
  display_line_subtotal: string;
  snapshot_at: string;
  created_at: string;
  updated_at: string;
}

export interface ShoppingCart {
  id: string;
  status: string;
  currency_code: string;
  version: number;
  items: CartItem[];
  item_count: number;
  display_subtotal: string;
  pricing_authoritative: false;
  pricing_notice: string;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  product_id: string;
  sku: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  currency_code: string;
  line_total: string;
}

export interface OrderConfirmation {
  order_id: string;
  order_number: string;
  status: OrderStatus;
  items: OrderItem[];
  currency_code: string;
  subtotal: string;
  total: string;
  created_at: string;
  payment_status: "not_in_scope";
}

export interface OrderSummary {
  order_id: string;
  order_number: string;
  status: OrderStatus;
  currency_code: string;
  total: string;
  created_at: string;
  updated_at: string;
}

export interface OrderPage {
  items: OrderSummary[];
  offset: number;
  limit: number;
  total: number;
}

export interface OrderStatusEntry {
  status: OrderStatus;
  actor_subject: string;
  correlation_id: string;
  occurred_at: string;
}

export interface OrderHistory {
  order_id: string;
  current_status: OrderStatus;
  items: OrderStatusEntry[];
}

export interface OrderAuditEvent {
  action: string;
  actor_subject: string;
  correlation_id: string;
  contextual_information: Record<string, unknown>;
  occurred_at: string;
}

export interface OrderAuditPage {
  order_id: string;
  items: OrderAuditEvent[];
  offset: number;
  limit: number;
  total: number;
}
