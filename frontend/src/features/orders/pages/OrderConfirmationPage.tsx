import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { OrderConfirmation } from "../../../types/order";
import { OrderError, OrderPageHeader, OrderStatusBadge } from "../components/OrderUi";
import { useOrderApi } from "../useOrderApi";
import { formatMoney, formatOrderDate } from "../utils";

export function OrderConfirmationPage() {
  const { orderId = "" } = useParams();
  const location = useLocation();
  const api = useOrderApi();
  const state = location.state as { confirmation?: OrderConfirmation } | null;
  const [confirmation, setConfirmation] = useState<OrderConfirmation | null>(
    state?.confirmation ?? null,
  );
  const [loading, setLoading] = useState(confirmation === null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setConfirmation(await api.getMyOrder(orderId));
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api, orderId]);

  useEffect(() => {
    if (!confirmation) void Promise.resolve().then(load);
  }, [confirmation, load]);

  if (loading)
    return (
      <AsyncState kind="loading" title="Loading confirmation" message="Retrieving your order." />
    );
  if (error) return <OrderError error={error} onRetry={() => void load()} />;
  if (!confirmation)
    return (
      <AsyncState kind="empty" title="Confirmation unavailable" message="No order was returned." />
    );

  return (
    <section className="order-page">
      <OrderPageHeader
        title="Order Confirmed"
        description="Your order was accepted and its commercial snapshot is now preserved."
      />
      <article className="panel confirmation-card">
        <div className="confirmation-card__mark" aria-hidden="true">
          ✓
        </div>
        <dl className="order-facts">
          <div>
            <dt>Order number</dt>
            <dd>{confirmation.order_number}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatOrderDate(confirmation.created_at)}</dd>
          </div>
          <div>
            <dt>Total</dt>
            <dd>{formatMoney(confirmation.currency_code, confirmation.total)}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <OrderStatusBadge status={confirmation.status} />
            </dd>
          </div>
        </dl>
        <p className="role-notice">Payment processing is not part of this capability.</p>
        <div className="page-actions">
          <Link className="button button--secondary" to={`/orders/${confirmation.order_id}`}>
            View order details
          </Link>
          <Link className="button button--primary" to="/products">
            Continue shopping
          </Link>
        </div>
      </article>
    </section>
  );
}
