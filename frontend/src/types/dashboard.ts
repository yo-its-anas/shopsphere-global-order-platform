export type KpiTrendDirection = "up" | "down" | "flat";
export type SemanticTone = "positive" | "warning" | "critical" | "neutral";
export type DashboardOrderStatus =
  "Fulfilled" | "Processing" | "Exception" | "Pending" | "Cancelled";

export interface KpiData {
  id: string;
  label: string;
  value: string;
  icon: "orders" | "revenue" | "customers" | "shipments";
  trend: {
    direction: KpiTrendDirection;
    label: string;
    tone: SemanticTone;
  };
}

export interface RecentOrder {
  id: string;
  customer: string;
  placedAt: string;
  status: DashboardOrderStatus;
  amount: string;
}

export interface PlatformHealthMetric {
  id: string;
  label: string;
  displayValue: string;
  utilizationPercent: number;
  tone: SemanticTone;
}

export interface AlertData {
  id: string;
  title: string;
  message: string;
  tone: "warning" | "critical";
}

export interface DashboardData {
  kpis: KpiData[];
  recentOrders: RecentOrder[];
  platformHealth: PlatformHealthMetric[];
  alerts: AlertData[];
}
