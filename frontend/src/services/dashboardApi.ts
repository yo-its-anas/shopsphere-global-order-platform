import type { ApiClient } from "./apiClient";

export interface BusinessSummaryResponse {
  metadata: { data_status: string };
  total_orders: number | null;
  total_revenue_simulated: string | null;
  revenue_currency: string | null;
  customer_count: number | null;
  product_count: number | null;
  available_product_count: number | null;
  low_stock_count: number | null;
  out_of_stock_count: number | null;
  fulfilled_orders: number | null;
  processing_orders: number | null;
  cancelled_orders: number | null;
  fulfilment_rate: string | null;
  revenue_label: string;
}

export interface ServiceHealth {
  service_name: string;
  status: string;
  availability_state: "available" | "degraded" | "unavailable" | "unknown";
  latency_ms: number | null;
}

export interface OperationalAlert {
  alert_type: string;
  classification: "business" | "application" | "infrastructure";
  message: string;
}

export interface OperationsDashboardResponse {
  services_health: ServiceHealth[];
  active_alerts: OperationalAlert[];
  system_performance: {
    api_availability: number | null;
    overall_request_rate: number | null;
    overall_error_rate: number | null;
    healthy_service_count: number;
    degraded_service_count: number;
    unavailable_service_count: number;
  };
}

export class DashboardApi {
  constructor(private readonly client: ApiClient) {}

  getSummary(): Promise<BusinessSummaryResponse> {
    return this.client.request("/dashboard/summary");
  }

  getOperations(): Promise<OperationsDashboardResponse> {
    return this.client.request("/operations/dashboard");
  }
}
