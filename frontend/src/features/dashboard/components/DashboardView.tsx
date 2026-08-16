import { useState } from "react";

import { AsyncState } from "../../../components/AsyncState";
import type { DashboardData } from "../../../types/dashboard";
import { AlertBanner } from "./AlertBanner";
import { KpiCard } from "./KpiCard";
import { PlatformHealthPanel } from "./PlatformHealthPanel";
import { RecentOrdersTable } from "./RecentOrdersTable";

export type DashboardLoadState = "loading" | "ready" | "error";

interface DashboardViewProps {
  data: DashboardData;
  state?: DashboardLoadState;
  onRetry?: () => void;
}

export function DashboardView({ data, state = "ready", onRetry }: DashboardViewProps) {
  const [dismissedAlertIds, setDismissedAlertIds] = useState<Set<string>>(() => new Set());

  if (state === "loading") {
    return (
      <AsyncState
        kind="loading"
        title="Loading dashboard"
        message="Preparing the executive operations view."
      />
    );
  }

  if (state === "error") {
    return (
      <AsyncState
        kind="error"
        title="Dashboard unavailable"
        message="The dashboard data could not be loaded. No live data is currently connected."
        onRetry={onRetry}
      />
    );
  }

  const visibleAlerts = data.alerts.filter((alert) => !dismissedAlertIds.has(alert.id));

  return (
    <div className="dashboard">
      <header className="page-heading">
        <div>
          <nav aria-label="Breadcrumb" className="breadcrumb">
            <span>Home</span>
            <span aria-hidden="true">›</span>
            <strong>Dashboard</strong>
          </nav>
          <div className="page-heading__title">
            <h1>Executive Dashboard</h1>
          </div>
          <p>Global operations overview.</p>
        </div>
        <div className="page-actions" aria-label="Unavailable demonstration actions">
          <button className="button button--secondary" disabled type="button">
            Export Report
          </button>
          <button className="button button--primary" disabled type="button">
            + New Order
          </button>
        </div>
      </header>

      <div className="alert-stack">
        {visibleAlerts.map((alert) => (
          <AlertBanner
            alert={alert}
            key={alert.id}
            onDismiss={(id) => setDismissedAlertIds((current) => new Set(current).add(id))}
          />
        ))}
      </div>

      {data.kpis.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No KPI data"
          message="KPI values will appear after the dashboard API is integrated."
        />
      ) : (
        <section aria-label="Key performance indicators" className="kpi-grid">
          {data.kpis.map((item) => (
            <KpiCard item={item} key={item.id} />
          ))}
        </section>
      )}

      <div className="dashboard-grid">
        <RecentOrdersTable orders={data.recentOrders} />
        <PlatformHealthPanel metrics={data.platformHealth} />
      </div>
    </div>
  );
}
