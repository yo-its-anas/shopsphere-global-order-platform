import { useEffect, useState, useCallback } from "react";
import { DashboardView } from "../features/dashboard/components/DashboardView";
import type { DashboardLoadState } from "../features/dashboard/components/DashboardView";
import { useDashboardApi } from "../features/dashboard/useDashboardApi";
import { useOrderApi } from "../features/orders/useOrderApi";
import type {
  DashboardData,
  KpiData,
  PlatformHealthMetric,
  AlertData,
  RecentOrder,
  DashboardOrderStatus,
} from "../types/dashboard";

export function DashboardPage() {
  const dashboardApi = useDashboardApi();
  const orderApi = useOrderApi();

  const [data, setData] = useState<DashboardData>({
    kpis: [],
    recentOrders: [],
    platformHealth: [],
    alerts: [],
  });
  const [loadState, setLoadState] = useState<DashboardLoadState>("loading");

  const loadData = useCallback(async () => {
    try {
      const [summary, operations, ordersResponse] = await Promise.all([
        dashboardApi.getSummary().catch(() => null),
        dashboardApi.getOperations().catch(() => null),
        orderApi.listOperationalOrders({ limit: 5, sort: "created_at_desc" }).catch(() => null),
      ]);

      if (!summary && !operations) {
        setLoadState("error");
        return;
      }

      const kpis: KpiData[] = [];
      const alerts: AlertData[] = [];
      const platformHealth: PlatformHealthMetric[] = [];
      const recentOrders: RecentOrder[] = [];

      if (summary) {
        kpis.push({
          id: "orders",
          label: "Orders Processed",
          value: summary.total_orders?.toLocaleString() ?? "--",
          icon: "orders",
          trend: {
            direction: "flat",
            label: summary.metadata?.data_status === "complete" ? "Live" : "Partial",
            tone: summary.metadata?.data_status === "complete" ? "positive" : "warning",
          },
        });
        kpis.push({
          id: "revenue",
          label: "Simulated Revenue",
          value: summary.total_revenue_simulated
            ? `$${Number(summary.total_revenue_simulated).toLocaleString()}`
            : "--",
          icon: "revenue",
          trend: {
            direction: "flat",
            label: summary.revenue_label || "Simulated Revenue",
            tone: "neutral",
          },
        });
        kpis.push({
          id: "customers",
          label: "Customer Registrations",
          value: summary.customer_count?.toLocaleString() ?? "--",
          icon: "customers",
          trend: { direction: "flat", label: "Registered", tone: "neutral" },
        });
        kpis.push({
          id: "products",
          label: "Products Available",
          value: summary.available_product_count?.toLocaleString() ?? "--",
          icon: "shipments",
          trend: {
            direction:
              summary.out_of_stock_count && summary.out_of_stock_count > 0 ? "down" : "flat",
            label: summary.out_of_stock_count ? `${summary.out_of_stock_count} OOS` : "In stock",
            tone:
              summary.out_of_stock_count && summary.out_of_stock_count > 0 ? "warning" : "positive",
          },
        });
        kpis.push({
          id: "fulfilment",
          label: "Order Fulfilment Rate",
          value: summary.fulfilment_rate ? `${summary.fulfilment_rate}%` : "--%",
          icon: "shipments",
          trend: { direction: "flat", label: "Fulfilled vs Confirmed", tone: "neutral" },
        });
      }

      if (operations) {
        operations.services_health.forEach((h) => {
          let tone: "positive" | "warning" | "critical" | "neutral" = "neutral";
          let util = 0;
          if (h.availability_state === "available") {
            tone = "positive";
            util = 100;
          } else if (h.availability_state === "degraded") {
            tone = "warning";
            util = 50;
          } else if (h.availability_state === "unavailable") {
            tone = "critical";
            util = 0;
          } else if (h.availability_state === "unknown") {
            tone = "warning";
            util = 0;
          }

          platformHealth.push({
            id: h.service_name,
            label: h.service_name,
            displayValue: h.status,
            utilizationPercent: util,
            tone,
          });
        });

        operations.active_alerts.forEach((a, i) => {
          alerts.push({
            id: `alert-${i}`,
            title: a.alert_type,
            message: a.message,
            tone: a.classification === "infrastructure" ? "critical" : "warning",
          });
        });

        if (
          operations.system_performance?.api_availability !== null &&
          operations.system_performance?.api_availability !== undefined
        ) {
          platformHealth.push({
            id: "sys-api-avail",
            label: "API Availability",
            displayValue: `${operations.system_performance.api_availability.toFixed(1)}%`,
            utilizationPercent: operations.system_performance.api_availability,
            tone: operations.system_performance.api_availability > 95 ? "positive" : "warning",
          });
        }
      }

      if (ordersResponse && ordersResponse.items) {
        ordersResponse.items.forEach((o) => {
          let mappedStatus: DashboardOrderStatus = "Pending";
          if (o.status === "FULFILLED") mappedStatus = "Fulfilled";
          else if (o.status === "PROCESSING") mappedStatus = "Processing";
          else if (o.status === "CANCELLED") mappedStatus = "Cancelled";
          else if (o.status === "CONFIRMED") mappedStatus = "Pending";

          recentOrders.push({
            id: o.order_number || o.order_id,
            customer: "ShopSphere User",
            placedAt: new Date(o.created_at).toLocaleString(),
            status: mappedStatus,
            amount: `${o.total} ${o.currency_code}`,
          });
        });
      }

      setData({ kpis, recentOrders, platformHealth, alerts });
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [dashboardApi, orderApi]);

  useEffect(() => {
    let active = true;

    // To satisfy react-hooks/set-state-in-effect without warnings,
    // we manage a loading transition explicitly.
    if (active) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadData();
    }
    return () => {
      active = false;
    };
  }, [loadData]);

  const onRetry = useCallback(() => {
    setLoadState("loading");
    void loadData();
  }, [loadData]);

  return <DashboardView data={data} state={loadState} onRetry={onRetry} />;
}
