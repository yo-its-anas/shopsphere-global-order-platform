import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import { ApiClientError } from "../../../services/apiClient";
import type { ShoppingCart } from "../../../types/order";
import { checkoutKeyFor, clearCheckoutAttempt } from "../checkoutAttempt";
import { OrderError, OrderPageHeader } from "../components/OrderUi";
import { useOrderApi } from "../useOrderApi";
import { formatMoney } from "../utils";

export function CheckoutPage() {
  const api = useOrderApi();
  const navigate = useNavigate();
  const [cart, setCart] = useState<ShoppingCart | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setCart(await api.getCart());
    } catch (loadError) {
      setError(loadError);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => void Promise.resolve().then(load), [load]);

  async function placeOrder() {
    if (!cart || cart.items.length === 0) return;
    setSubmitting(true);
    setError(null);
    const idempotencyKey = checkoutKeyFor(cart);
    try {
      const confirmation = await api.checkout(idempotencyKey);
      clearCheckoutAttempt();
      navigate(`/orders/confirmation/${confirmation.order_id}`, {
        state: { confirmation },
        replace: true,
      });
    } catch (checkoutError) {
      setError(checkoutError);
    } finally {
      setSubmitting(false);
    }
  }

  const conflict = error instanceof ApiClientError && error.status === 409;
  const timeout = error instanceof ApiClientError && (error.status === 0 || error.status === 504);

  if (loading)
    return <AsyncState kind="loading" title="Loading checkout" message="Preparing order review." />;

  return (
    <section className="order-page">
      <OrderPageHeader
        title="Checkout Review"
        description="Catalogue pricing and inventory will be revalidated by the backend when you place the order."
        actions={
          <Link className="button button--secondary" to="/cart">
            Return to cart
          </Link>
        }
      />
      {error !== null && (
        <>
          <OrderError error={error} onRetry={timeout ? () => void placeOrder() : undefined} />
          {conflict && (
            <div className="order-warning" role="status">
              Stock, product availability, or pricing changed during validation. Return to your
              cart, review the refreshed catalogue information, and try a deliberate new checkout.
            </div>
          )}
          {timeout && (
            <div className="order-warning" role="status">
              The outcome may be unknown. “Retry safely” reuses the same idempotency key and cannot
              intentionally create a second order for this cart attempt.
            </div>
          )}
        </>
      )}
      {!cart || cart.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="Nothing to checkout"
          message="Add an item to your cart first."
        />
      ) : (
        <div className="order-two-column">
          <section className="panel table-panel">
            <div className="panel__header">
              <h2>Order items</h2>
              <span>{cart.item_count} units</span>
            </div>
            <div className="responsive-table">
              <table className="enterprise-table order-table">
                <thead>
                  <tr>
                    <th>Product snapshot</th>
                    <th>Quantity</th>
                    <th>Display price</th>
                    <th className="align-right">Display total</th>
                  </tr>
                </thead>
                <tbody>
                  {cart.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.display_name}</strong>
                        <small className="table-description mono-data">{item.display_sku}</small>
                      </td>
                      <td>{item.quantity}</td>
                      <td>{formatMoney(item.display_currency_code, item.display_unit_price)}</td>
                      <td className="align-right">
                        {formatMoney(item.display_currency_code, item.display_line_subtotal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <aside className="panel order-summary-card order-summary-card--dark">
            <h2>Checkout summary</h2>
            <div>
              <span>Current display estimate</span>
              <strong>{formatMoney(cart.currency_code, cart.display_subtotal)}</strong>
            </div>
            <p>
              This is not the authoritative total. The confirmation will show server-calculated
              immutable prices and totals.
            </p>
            <button
              className="button button--primary"
              disabled={submitting}
              onClick={() => void placeOrder()}
              type="button"
            >
              {submitting ? "Validating order…" : "Place order"}
            </button>
          </aside>
        </div>
      )}
    </section>
  );
}
