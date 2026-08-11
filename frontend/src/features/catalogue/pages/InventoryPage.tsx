import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type {
  AvailabilityState,
  InventoryItem,
  PageResponse,
  Product,
} from "../../../types/catalogue";
import { useAuth } from "../../auth/useAuth";
import {
  CapabilityError,
  CataloguePageHeader,
  Pagination,
  StatusBadge,
} from "../components/CatalogueUi";
import { useCatalogueApi } from "../useCatalogueApi";
import { formatNumber } from "../utils";

const PAGE_SIZE = 25;

export function InventoryPage() {
  const api = useCatalogueApi();
  const auth = useAuth();
  const canManage = auth.hasRole("operations_admin");
  const [result, setResult] = useState<PageResponse<InventoryItem> | null>(null);
  const [products, setProducts] = useState<Map<string, Product>>(new Map());
  const [state, setState] = useState<AvailabilityState | "">("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const inventory = await api.listInventory(state || undefined, offset, PAGE_SIZE);
      const productResults = await Promise.allSettled(
        inventory.items.map((item) => api.getProduct(item.product_id)),
      );
      const productMap = new Map<string, Product>();
      productResults.forEach((entry) => {
        if (entry.status === "fulfilled") productMap.set(entry.value.id, entry.value);
      });
      setProducts(productMap);
      setResult(inventory);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, offset, state]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  return (
    <section className="catalogue-page">
      <CataloguePageHeader
        title="Global Stock Levels"
        description="Operational balances from PostgreSQL. Available quantity is derived, never edited directly."
        actions={
          <Link className="button button--secondary" to="/inventory/statistics">
            View statistics
          </Link>
        }
      />
      <div className="panel catalogue-toolbar catalogue-toolbar--single">
        <label>
          <span>Availability state</span>
          <select
            aria-label="Inventory state filter"
            onChange={(event) => {
              setState(event.target.value as AvailabilityState | "");
              setOffset(0);
            }}
            value={state}
          >
            <option value="">All inventory</option>
            <option value="in_stock">In stock</option>
            <option value="low_stock">Low stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>
        </label>
      </div>
      {error !== null && <CapabilityError error={error} />}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading inventory"
          message="Retrieving authoritative stock balances."
        />
      ) : !result || result.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No inventory found"
          message="No tracked inventory matches this filter."
        />
      ) : (
        <div className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table catalogue-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>On hand</th>
                  <th>Reserved</th>
                  <th>Available</th>
                  <th>Threshold</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => {
                  const product = products.get(item.product_id);
                  return (
                    <tr key={item.id}>
                      <td>
                        <Link className="table-link" to={`/products/${item.product_id}`}>
                          {product?.name ?? item.product_id}
                        </Link>
                      </td>
                      <td className="mono-data">{product?.sku ?? "—"}</td>
                      <td className="mono-data">{formatNumber(item.quantity_on_hand)}</td>
                      <td className="mono-data">{formatNumber(item.quantity_reserved)}</td>
                      <td className="mono-data">
                        <strong>{formatNumber(item.quantity_available)}</strong>
                      </td>
                      <td className="mono-data">{formatNumber(item.reorder_threshold)}</td>
                      <td>
                        <StatusBadge status={item.state} />
                      </td>
                      <td className="table-actions">
                        <Link
                          className="button-link"
                          to={`/inventory/${item.product_id}/movements`}
                        >
                          History
                        </Link>
                        {canManage && (
                          <Link className="button-link" to={`/inventory/${item.product_id}/adjust`}>
                            Adjust
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })}
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
