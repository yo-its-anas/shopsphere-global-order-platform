import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { useDashboardApi } from "../features/dashboard/useDashboardApi";
import { useOrderApi } from "../features/orders/useOrderApi";
import type { DashboardApi } from "../services/dashboardApi";
import type { OrderApi } from "../services/orderApi";
import { DashboardPage } from "./DashboardPage";

// Mock the hooks
vi.mock("../features/dashboard/useDashboardApi");
vi.mock("../features/orders/useOrderApi");

const mockSummaryResponse = {
  metadata: { data_status: "complete" },
  total_orders: 1450,
  total_revenue_simulated: "72500.50",
  revenue_currency: "USD",
  customer_count: 980,
  product_count: 120,
  available_product_count: 115,
  low_stock_count: 5,
  out_of_stock_count: 2,
  fulfilled_orders: 1400,
  processing_orders: 40,
  cancelled_orders: 10,
  fulfilment_rate: "96.5",
  revenue_label: "Simulated Revenue",
};

const mockOperationsResponse = {
  services_health: [
    {
      service_name: "customer-service",
      status: "Service is healthy",
      availability_state: "available" as const,
      latency_ms: 12,
    },
    {
      service_name: "order-service",
      status: "Service is healthy",
      availability_state: "available" as const,
      latency_ms: 18,
    },
    {
      service_name: "catalogue-service",
      status: "Service is degraded",
      availability_state: "degraded" as const,
      latency_ms: null,
    },
    {
      service_name: "api-gateway",
      status: "Service is down or unreachable",
      availability_state: "unavailable" as const,
      latency_ms: null,
    },
  ],
  active_alerts: [
    {
      alert_type: "DatabaseLatencyWarning",
      classification: "application" as const,
      message: "Database read latency has crossed its threshold.",
    },
    {
      alert_type: "KafkaBrokerOutage",
      classification: "infrastructure" as const,
      message: "Single-node Kafka broker is unreachable.",
    },
  ],
  system_performance: {
    api_availability: 98.4,
    overall_request_rate: 15.2,
    overall_error_rate: 0.12,
    healthy_service_count: 2,
    degraded_service_count: 1,
    unavailable_service_count: 1,
  },
};

const mockOrdersResponse = {
  items: [
    {
      order_id: "order-1",
      order_number: "ORD-9988",
      status: "FULFILLED" as const,
      created_at: "2026-08-16T12:00:00Z",
      total: "150.00",
      currency_code: "USD",
    },
    {
      order_id: "order-2",
      order_number: "ORD-9987",
      status: "PROCESSING" as const,
      created_at: "2026-08-16T11:45:00Z",
      total: "85.50",
      currency_code: "USD",
    },
  ],
  metadata: { total: 2, limit: 5, offset: 0 },
};

describe("DashboardPage Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. binds live analytics response KPIs, platform health, and active alerts correctly", async () => {
    vi.mocked(useDashboardApi).mockReturnValue({
      getSummary: vi.fn().mockResolvedValue(mockSummaryResponse),
      getOperations: vi.fn().mockResolvedValue(mockOperationsResponse),
    } as unknown as DashboardApi);

    vi.mocked(useOrderApi).mockReturnValue({
      listOperationalOrders: vi.fn().mockResolvedValue(mockOrdersResponse),
    } as unknown as OrderApi);

    render(<DashboardPage />);

    // 1. Live analytics response binding & KPI formatting
    expect(await screen.findByText("Orders Processed")).toBeInTheDocument();
    expect(screen.getByText("1,450")).toBeInTheDocument();

    // 2. Simulated Revenue label
    expect(screen.getAllByText("Simulated Revenue")[0]).toBeInTheDocument();
    expect(screen.getByText("$72,500.5")).toBeInTheDocument();

    // 3. Customer Registrations
    expect(screen.getByText("Customer Registrations")).toBeInTheDocument();
    expect(screen.getByText("980")).toBeInTheDocument();

    // 4. Inventory status & Product availability
    expect(screen.getByText("Products Available")).toBeInTheDocument();
    expect(screen.getByText("115")).toBeInTheDocument();
    expect(screen.getByText("2 OOS")).toBeInTheDocument();

    // 5. Order status history
    expect(screen.getByText("ORD-9988")).toBeInTheDocument();
    expect(screen.getByText("ORD-9987")).toBeInTheDocument();
    expect(screen.getAllByText("Fulfilled")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Processing")[0]).toBeInTheDocument();

    // 6. Application health state tones
    expect(screen.getByText("customer-service")).toBeInTheDocument();
    expect(screen.getByText("Service is degraded")).toBeInTheDocument();
    expect(screen.getByText("Service is down or unreachable")).toBeInTheDocument();

    // 7. Operational alerts
    expect(screen.getByText("DatabaseLatencyWarning")).toBeInTheDocument();
    expect(screen.getByText("KafkaBrokerOutage")).toBeInTheDocument();

    // 8. Absence of runtime hard-coded KPI values (from mockDashboardData)
    expect(screen.queryByText("Demo Orders")).not.toBeInTheDocument();
    expect(screen.queryByText("DEMO-1042")).not.toBeInTheDocument();
  });

  it("9. renders partial responses gracefully when only summary is available", async () => {
    vi.mocked(useDashboardApi).mockReturnValue({
      getSummary: vi.fn().mockResolvedValue(mockSummaryResponse),
      getOperations: vi.fn().mockRejectedValue(new Error("API Outage")),
    } as unknown as DashboardApi);

    vi.mocked(useOrderApi).mockReturnValue({
      listOperationalOrders: vi.fn().mockResolvedValue(mockOrdersResponse),
    } as unknown as OrderApi);

    render(<DashboardPage />);

    // Renders KPIs but health is missing/empty
    expect(await screen.findByText("Orders Processed")).toBeInTheDocument();
    expect(screen.queryByText("customer-service")).not.toBeInTheDocument();
  });

  it("10. displays secure error state when both API calls fail", async () => {
    vi.mocked(useDashboardApi).mockReturnValue({
      getSummary: vi.fn().mockRejectedValue(new Error("API Outage")),
      getOperations: vi.fn().mockRejectedValue(new Error("API Outage")),
    } as unknown as DashboardApi);

    vi.mocked(useOrderApi).mockReturnValue({
      listOperationalOrders: vi.fn().mockRejectedValue(new Error("API Outage")),
    } as unknown as OrderApi);

    render(<DashboardPage />);

    expect(await screen.findByText("Dashboard unavailable")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The dashboard data could not be loaded. No live data is currently connected.",
      ),
    ).toBeInTheDocument();
  });
});
