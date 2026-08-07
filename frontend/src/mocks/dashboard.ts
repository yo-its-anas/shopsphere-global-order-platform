import type { DashboardData } from "../types/dashboard";

/**
 * Development-only values derived from the Stitch layout. These are intentionally
 * fictional and must be replaced by typed API responses when integration begins.
 */
export const mockDashboardData: DashboardData = {
  kpis: [
    {
      id: "orders",
      label: "Demo Orders",
      value: "1,284",
      icon: "orders",
      trend: { direction: "up", label: "8% demo trend", tone: "positive" },
    },
    {
      id: "revenue",
      label: "Demo Revenue",
      value: "$284K",
      icon: "revenue",
      trend: { direction: "flat", label: "0% demo trend", tone: "neutral" },
    },
    {
      id: "customers",
      label: "Demo Customers",
      value: "932",
      icon: "customers",
      trend: { direction: "up", label: "5% demo trend", tone: "positive" },
    },
    {
      id: "shipments",
      label: "Demo Pending Shipments",
      value: "42",
      icon: "shipments",
      trend: { direction: "up", label: "3% demo trend", tone: "warning" },
    },
  ],
  recentOrders: [
    {
      id: "DEMO-1042",
      customer: "Northstar Demo Ltd",
      placedAt: "Today, 10:42",
      status: "Fulfilled",
      amount: "$1,240.00",
    },
    {
      id: "DEMO-1041",
      customer: "Globex Sandbox",
      placedAt: "Today, 09:15",
      status: "Processing",
      amount: "$895.50",
    },
    {
      id: "DEMO-1040",
      customer: "Example Industries",
      placedAt: "Yesterday, 16:30",
      status: "Exception",
      amount: "$4,500.00",
    },
    {
      id: "DEMO-1039",
      customer: "Wayfinder Test Group",
      placedAt: "Yesterday, 14:12",
      status: "Fulfilled",
      amount: "$2,050.00",
    },
    {
      id: "DEMO-1038",
      customer: "Sample Systems",
      placedAt: "Yesterday, 11:05",
      status: "Fulfilled",
      amount: "$340.25",
    },
  ],
  platformHealth: [
    {
      id: "gateway",
      label: "API Gateway (simulated)",
      displayValue: "145ms",
      utilizationPercent: 85,
      tone: "critical",
    },
    {
      id: "read",
      label: "Database Read (simulated)",
      displayValue: "12ms",
      utilizationPercent: 20,
      tone: "positive",
    },
    {
      id: "write",
      label: "Database Write (simulated)",
      displayValue: "45ms",
      utilizationPercent: 40,
      tone: "positive",
    },
    {
      id: "cache",
      label: "Cache Hit Rate (simulated)",
      displayValue: "98.2%",
      utilizationPercent: 98,
      tone: "neutral",
    },
  ],
  alerts: [
    {
      id: "demo-load",
      title: "Simulated Load Alert",
      message:
        "Demonstration latency is above its mock threshold. This alert is not connected to live telemetry.",
      tone: "critical",
    },
  ],
};
