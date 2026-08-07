import { Icon, type IconName } from "../../../components/Icon";
import type { KpiData } from "../../../types/dashboard";

const iconNames: Record<KpiData["icon"], IconName> = {
  orders: "orders",
  revenue: "revenue",
  customers: "customers",
  shipments: "shipments",
};

interface KpiCardProps {
  item: KpiData;
}

export function KpiCard({ item }: KpiCardProps) {
  const trendSymbol =
    item.trend.direction === "up" ? "↑" : item.trend.direction === "down" ? "↓" : "—";

  return (
    <article className="kpi-card">
      <div className="kpi-card__header">
        <span>{item.label}</span>
        <Icon name={iconNames[item.icon]} size={23} />
      </div>
      <div className="kpi-card__value">
        <strong>{item.value}</strong>
        <span className={"tone-" + item.trend.tone}>
          <span aria-hidden="true">{trendSymbol}</span>
          {item.trend.label}
        </span>
      </div>
    </article>
  );
}
