import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { OrderAuditPage, OrderConfirmation, OrderHistory } from "../../../types/order";
import { useAuth } from "../../auth/useAuth";
import { OrderError, OrderPageHeader, OrderStatusBadge } from "../components/OrderUi";
import { useOrderApi } from "../useOrderApi";
import { formatMoney, formatOrderDate } from "../utils";

export function OrderDetailsPage({ operational = false }: { operational?: boolean }) {
  const { orderId = "" } = useParams();
  const api = useOrderApi();
  const auth = useAuth();
  const [order, setOrder] = useState<OrderConfirmation | null>(null);
  const [history, setHistory] = useState<OrderHistory | null>(null);
  const [audit, setAudit] = useState<OrderAuditPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const canManage = operational && auth.hasRole("operations_admin");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, statusHistory, auditHistory] = await Promise.all([
        operational ? api.getOperationalOrder(orderId) : api.getMyOrder(orderId),
        operational ? api.getOperationalHistory(orderId) : api.getMyHistory(orderId),
        operational ? api.getOperationalAudit(orderId) : Promise.resolve(null),
      ]);
      setOrder(detail);
      setHistory(statusHistory);
      setAudit(auditHistory);
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, operational, orderId]);

  useEffect(() => void Promise.resolve().then(load), [load]);

  async function command(action: "cancel" | "process" | "fulfil") {
    if (!order) return;
    const confirmed = window.confirm(`Confirm ${action} for ${order.order_number}?`);
    if (!confirmed) return;
    setBusy(true);
    setError(null);
    try {
      if (action === "cancel") {
        if (operational) await api.cancelOperationalOrder(order.order_id);
        else await api.cancelMyOrder(order.order_id);
      } else {
        await api.transition(order.order_id, action === "process" ? "PROCESSING" : "FULFILLED");
      }
      await load();
    } catch (commandError) {
      setError(commandError);
    } finally {
      setBusy(false);
    }
  }

  if (loading)
    return (
      <AsyncState
        kind="loading"
        title="Loading order"
        message="Retrieving order details and history."
      />
    );
  if (!order && error) return <OrderError error={error} onRetry={() => void load()} />;
  if (!order)
    return (
      <AsyncState
        kind="empty"
        title="Order not found"
        message="No authorized order was returned."
      />
    );

  const cancellable = order.status === "PENDING" || order.status === "CONFIRMED";
  const actions = operational ? (
    canManage ? (
      <>
        {order.status === "CONFIRMED" && (
          <button
            className="button button--primary"
            disabled={busy}
            onClick={() => void command("process")}
            type="button"
          >
            Process order
          </button>
        )}
        {order.status === "PROCESSING" && (
          <button
            className="button button--primary"
            disabled={busy}
            onClick={() => void command("fulfil")}
            type="button"
          >
            Mark fulfilled
          </button>
        )}
        {cancellable && (
          <button
            className="button button--danger"
            disabled={busy}
            onClick={() => void command("cancel")}
            type="button"
          >
            Cancel order
          </button>
        )}
      </>
    ) : undefined
  ) : (
    <>
      <Link className="button button--secondary" to="/orders">
        Back to orders
      </Link>
      {cancellable && (
        <button
          className="button button--danger"
          disabled={busy}
          onClick={() => void command("cancel")}
          type="button"
        >
          Cancel order
        </button>
      )}
    </>
  );

  return (
    <section className="order-page">
      <OrderPageHeader
        title={`Order ${order.order_number}`}
        description={`Created ${formatOrderDate(order.created_at)}`}
        actions={actions}
      />
      {error !== null && <OrderError error={error} />}
      {cancellable && (
        <p className="role-notice">
          The red <strong>Cancel order</strong> action cancels this order and releases its active
          inventory reservations. Payment refunds are not part of this capability.
        </p>
      )}
      {!canManage && operational && (
        <p className="role-notice">
          Operational read access does not grant order modification permission.
        </p>
      )}
      <div className="order-detail-grid">
        <section className="panel table-panel order-items-panel">
          <div className="panel__header">
            <h2>Ordered item snapshots</h2>
            <OrderStatusBadge status={order.status} />
          </div>
          <div className="responsive-table">
            <table className="enterprise-table order-table">
              <thead>
                <tr>
                  <th>SKU / Product</th>
                  <th>Quantity</th>
                  <th>Unit price</th>
                  <th className="align-right">Line total</th>
                </tr>
              </thead>
              <tbody>
                {order.items.map((item) => (
                  <tr key={`${item.product_id}-${item.sku}`}>
                    <td>
                      <strong>{item.product_name}</strong>
                      <small className="table-description mono-data">{item.sku}</small>
                    </td>
                    <td>{item.quantity}</td>
                    <td>{formatMoney(item.currency_code, item.unit_price)}</td>
                    <td className="align-right">
                      {formatMoney(item.currency_code, item.line_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <aside className="panel order-summary-card">
          <h2>Financial snapshot</h2>
          <div>
            <span>Subtotal</span>
            <strong>{formatMoney(order.currency_code, order.subtotal)}</strong>
          </div>
          <div className="order-summary-total">
            <span>Total</span>
            <strong>{formatMoney(order.currency_code, order.total)}</strong>
          </div>
          <p>Historical values captured at checkout; current catalogue pricing is not used.</p>
        </aside>
        <section className="panel order-timeline-panel">
          <div className="panel__header">
            <h2>Status timeline</h2>
            <span>{history?.current_status}</span>
          </div>
          {history?.items.length ? (
            <ol className="order-timeline">
              {history.items.map((entry, index) => (
                <li key={`${entry.status}-${entry.occurred_at}-${index}`}>
                  <i aria-hidden="true" />
                  <div>
                    <OrderStatusBadge status={entry.status} />
                    <strong>{formatOrderDate(entry.occurred_at)}</strong>
                    <small>{entry.actor_subject}</small>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted-copy">No status history was returned.</p>
          )}
        </section>
        {operational && (
          <section className="panel order-audit-panel">
            <div className="panel__header">
              <h2>Transaction audit</h2>
              <span>{audit?.total ?? 0} entries</span>
            </div>
            {audit?.items.length ? (
              <ol className="audit-list">
                {audit.items.map((entry, index) => (
                  <li key={`${entry.action}-${entry.occurred_at}-${index}`}>
                    <strong>{entry.action.replaceAll("_", " ")}</strong>
                    <span>{formatOrderDate(entry.occurred_at)}</span>
                    <small>Actor: {entry.actor_subject}</small>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted-copy">No audit entries were returned.</p>
            )}
          </section>
        )}
      </div>
    </section>
  );
}
