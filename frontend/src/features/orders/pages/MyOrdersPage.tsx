import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { OrderPage, OrderStatus } from "../../../types/order";
import {
  OrderError,
  OrderPageHeader,
  OrderPagination,
  OrderStatusBadge,
  ViewOrderLink,
} from "../components/OrderUi";
import { useOrderApi } from "../useOrderApi";
import { formatMoney, formatOrderDate } from "../utils";

const PAGE_SIZE = 20;

export function MyOrdersPage() {
  const api = useOrderApi();
  const [orders, setOrders] = useState<OrderPage | null>(null);
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setOrders(await api.listMyOrders({ status, offset, limit: PAGE_SIZE }));
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, offset, status]);

  useEffect(() => void Promise.resolve().then(load), [load]);

  return (
    <section className="order-page">
      <OrderPageHeader
        title="My Orders"
        description="Review your immutable order snapshots and current lifecycle status."
        actions={
          <Link className="button button--primary" to="/products">
            New order
          </Link>
        }
      />
      <div className="panel order-filter">
        <label>
          <span>Status</span>
          <select
            aria-label="Order status filter"
            onChange={(event) => {
              setStatus(event.target.value as OrderStatus | "");
              setOffset(0);
            }}
            value={status}
          >
            <option value="">All statuses</option>
            {(["PENDING", "CONFIRMED", "PROCESSING", "FULFILLED", "CANCELLED"] as const).map(
              (value) => (
                <option key={value}>{value}</option>
              ),
            )}
          </select>
        </label>
      </div>
      {error !== null && <OrderError error={error} onRetry={() => void load()} />}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading orders"
          message="Retrieving your order history."
        />
      ) : !orders || orders.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No orders found"
          message="No orders match the selected status."
        />
      ) : (
        <section className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table order-table">
              <thead>
                <tr>
                  <th>Order number</th>
                  <th>Created</th>
                  <th className="align-right">Total</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {orders.items.map((order) => (
                  <tr key={order.order_id}>
                    <td className="mono-data">{order.order_number}</td>
                    <td>{formatOrderDate(order.created_at)}</td>
                    <td className="align-right mono-data">
                      {formatMoney(order.currency_code, order.total)}
                    </td>
                    <td>
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td>
                      <ViewOrderLink orderId={order.order_id} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <OrderPagination {...orders} onChange={setOffset} />
        </section>
      )}
    </section>
  );
}
