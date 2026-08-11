import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { InventoryMovement, PageResponse, Product } from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import { CapabilityError, CataloguePageHeader, Pagination } from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatTimestamp } from "../utils";

const PAGE_SIZE = 25;

export function InventoryMovementsPage() {
  const { productId = "" } = useParams();
  const api = useCatalogueApi();
  const auth = useAuth();
  const [product, setProduct] = useState<Product | null>(null);
  const [result, setResult] = useState<PageResponse<InventoryMovement> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [loadedProduct, movements] = await Promise.all([
        api.getProduct(productId),
        api.listMovements(productId, offset, PAGE_SIZE),
      ]);
      setProduct(loadedProduct);
      setResult(movements);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, offset, productId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Inventory Movement History"
        description={
          product
            ? `${product.name} · ${product.sku}`
            : "Append-only stock history and audit context."
        }
        actions={
          auth.hasRole("operations_admin") ? (
            <Link className="button button--primary" to={`/inventory/${productId}/adjust`}>
              Adjust inventory
            </Link>
          ) : undefined
        }
      />
      {error !== null && <CapabilityError error={error} />}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading movements"
          message="Retrieving inventory history."
        />
      ) : !result || result.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No movement history"
          message="No inventory movements exist for this product."
        />
      ) : (
        <div className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table catalogue-table movement-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Type</th>
                  <th>Delta</th>
                  <th>Previous</th>
                  <th>Result</th>
                  <th>Reason / reference</th>
                  <th>Correlation</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((movement) => (
                  <tr key={movement.id}>
                    <td>{formatTimestamp(movement.occurred_at)}</td>
                    <td>{movement.movement_type.replaceAll("_", " ")}</td>
                    <td
                      className={`mono-data ${movement.quantity_delta < 0 ? "negative-value" : "positive-value"}`}
                    >
                      {movement.quantity_delta > 0 ? "+" : ""}
                      {movement.quantity_delta}
                    </td>
                    <td className="mono-data">{movement.previous_quantity_on_hand}</td>
                    <td className="mono-data">
                      <strong>{movement.resulting_quantity_on_hand}</strong>
                    </td>
                    <td>
                      {movement.reason}
                      <small className="table-description">{movement.reference}</small>
                    </td>
                    <td className="mono-data movement-correlation">{movement.correlation_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            limit={result.limit}
            offset={result.offset}
            onChange={setOffset}
            total={result.total}
          />
        </div>
      )}
    </section>
  );
}
