import { useCallback, useEffect, useState, type FormEvent } from "react";

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

export function OrderManagementPage() {
  const api = useOrderApi();
  const [orders, setOrders] = useState<OrderPage | null>(null);
  const [subjectInput, setSubjectInput] = useState("");
  const [subject, setSubject] = useState("");
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setOrders(
        await api.listOperationalOrders({
          customerSubject: subject || undefined,
          status,
          offset,
          limit: PAGE_SIZE,
        }),
      );
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, offset, status, subject]);

  useEffect(() => void Promise.resolve().then(load), [load]);

  function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setSubject(subjectInput.trim());
  }

  return (
    <section className="order-page">
      <OrderPageHeader
        title="Order Management"
        description="Governed operational order lookup and explicitly controlled lifecycle actions."
      />
      <form className="panel order-management-filter" onSubmit={search}>
        <label>
          <span>Customer identity subject</span>
          <input
            aria-label="Customer identity subject"
            maxLength={255}
            onChange={(event) => setSubjectInput(event.target.value)}
            placeholder="Exact identity subject (optional)"
            value={subjectInput}
          />
        </label>
        <label>
          <span>Status</span>
          <select
            aria-label="Operational status filter"
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
        <button className="button button--secondary" type="submit">
          Search
        </button>
      </form>
      {error !== null && <OrderError error={error} onRetry={() => void load()} />}
      {loading ? (
        <AsyncState
          kind="loading"
          title="Loading operational orders"
          message="Retrieving authorized order records."
        />
      ) : !orders || orders.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No operational orders"
          message="No orders match the governed filters."
        />
      ) : (
        <section className="panel table-panel">
          <div className="responsive-table">
            <table className="enterprise-table order-table">
              <thead>
                <tr>
                  <th>Order number</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th className="align-right">Total</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {orders.items.map((order) => (
                  <tr key={order.order_id}>
                    <td className="mono-data">{order.order_number}</td>
                    <td>{formatOrderDate(order.created_at)}</td>
                    <td>
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="align-right">{formatMoney(order.currency_code, order.total)}</td>
                    <td>
                      <ViewOrderLink operational orderId={order.order_id} />
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
