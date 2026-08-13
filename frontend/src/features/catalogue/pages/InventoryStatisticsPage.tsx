import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { InventoryStatistics } from "../../../types/catalogue";
import { CapabilityError, CataloguePageHeader } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatNumber, formatTimestamp } from "../utils";

export function InventoryStatisticsPage() {
  const api = useCatalogueApi();
  const [statistics, setStatistics] = useState<InventoryStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setStatistics(await api.getStatistics());
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Inventory Statistics"
        description="Calculated directly from persisted PoC inventory balances."
        actions={
          <Link className="button button--secondary" to="/inventory">
            Stock levels
          </Link>
        }
      />
      {error !== null && <CapabilityError error={error} />}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Calculating statistics"
          message="Retrieving persisted inventory metrics."
        />
      ) : !statistics ? (
        <AsyncState
          kind="empty"
          title="Statistics unavailable"
          message="No statistics were returned."
        />
      ) : (
        <>
          <div className="statistics-grid">
            <StatisticCard label="Tracked products" value={statistics.total_products_tracked} />
            <StatisticCard label="In stock" tone="positive" value={statistics.in_stock_products} />
            <StatisticCard label="Low stock" tone="warning" value={statistics.low_stock_products} />
            <StatisticCard
              label="Out of stock"
              tone="critical"
              value={statistics.out_of_stock_products}
            />
          </div>
          <div className="panel unit-statistics">
            <div className="panel__header">
              <h2>Unit volumes</h2>
              <span className="panel__meta">Location {statistics.location_code}</span>
            </div>
            <dl>
              <div>
                <dt>Units on hand</dt>
                <dd>{formatNumber(statistics.total_units_on_hand)}</dd>
              </div>
              <div>
                <dt>Reserved units</dt>
                <dd>{formatNumber(statistics.reserved_units)}</dd>
              </div>
              <div>
                <dt>Available units</dt>
                <dd>{formatNumber(statistics.available_units)}</dd>
              </div>
            </dl>
            <p className="muted-copy">
              Calculated {formatTimestamp(statistics.calculated_at)}. Values are returned by the
              inventory statistics API and are not mock data.
            </p>
          </div>
        </>
      )}
    </section>
  );
}

function StatisticCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "positive" | "warning" | "critical";
}) {
  return (
    <article className={`panel statistic-card statistic-card--${tone}`}>
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </article>
  );
}
