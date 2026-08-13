import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AsyncState } from "../../../components/AsyncState";
import type { ShoppingCart } from "../../../types/order";
import { clearCheckoutAttempt } from "../checkoutAttempt";
import { OrderError, OrderPageHeader } from "../components/OrderUi";
import { useOrderApi } from "../useOrderApi";
import { formatMoney } from "../utils";

export function ShoppingCartPage() {
  const api = useOrderApi();
  const [cart, setCart] = useState<ShoppingCart | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyItem, setBusyItem] = useState<string | null>(null);
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

  async function mutate(action: () => Promise<ShoppingCart>, marker: string) {
    setBusyItem(marker);
    setError(null);
    try {
      const updated = await action();
      clearCheckoutAttempt();
      setCart(updated);
    } catch (mutationError) {
      setError(mutationError);
    } finally {
      setBusyItem(null);
    }
  }

  if (loading)
    return (
      <AsyncState kind="loading" title="Loading cart" message="Retrieving your active cart." />
    );

  return (
    <section className="order-page">
      <OrderPageHeader
        title="Shopping Cart"
        description="Review display estimates before authoritative price and stock validation at checkout."
        actions={
          <Link className="button button--secondary" to="/products">
            Continue shopping
          </Link>
        }
      />
      {error !== null && <OrderError error={error} onRetry={() => void load()} />}
      {!cart || cart.items.length === 0 ? (
        <AsyncState
          kind="empty"
          title="Your cart is empty"
          message="Browse the product catalogue and add an active product to begin an order."
        />
      ) : (
        <div className="order-two-column">
          <section className="panel table-panel">
            <div className="responsive-table">
              <table className="enterprise-table order-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Display unit price</th>
                    <th>Quantity</th>
                    <th className="align-right">Display subtotal</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {cart.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <Link className="table-link" to={`/products/${item.product_id}`}>
                          {item.display_name}
                        </Link>
                        <small className="table-description mono-data">{item.display_sku}</small>
                      </td>
                      <td className="mono-data">
                        {formatMoney(item.display_currency_code, item.display_unit_price)}
                      </td>
                      <td>
                        <div className="quantity-control">
                          <button
                            aria-label={`Decrease ${item.display_name} quantity`}
                            disabled={item.quantity <= 1 || busyItem !== null}
                            onClick={() =>
                              void mutate(() => api.updateItem(item.id, item.quantity - 1), item.id)
                            }
                            type="button"
                          >
                            −
                          </button>
                          <span aria-label={`${item.display_name} quantity`}>{item.quantity}</span>
                          <button
                            aria-label={`Increase ${item.display_name} quantity`}
                            disabled={item.quantity >= 1000 || busyItem !== null}
                            onClick={() =>
                              void mutate(() => api.updateItem(item.id, item.quantity + 1), item.id)
                            }
                            type="button"
                          >
                            +
                          </button>
                        </div>
                      </td>
                      <td className="align-right mono-data">
                        {formatMoney(item.display_currency_code, item.display_line_subtotal)}
                      </td>
                      <td>
                        <button
                          className="button-link button-link--danger"
                          disabled={busyItem !== null}
                          onClick={() => void mutate(() => api.removeItem(item.id), item.id)}
                          type="button"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <aside className="panel order-summary-card">
            <h2>Order summary</h2>
            <div>
              <span>Items</span>
              <strong>{cart.item_count}</strong>
            </div>
            <div>
              <span>Display subtotal</span>
              <strong>{formatMoney(cart.currency_code, cart.display_subtotal)}</strong>
            </div>
            <p>{cart.pricing_notice}</p>
            <Link className="button button--primary" to="/checkout">
              Review checkout
            </Link>
            <button
              className="button button--secondary"
              disabled={busyItem !== null}
              onClick={() => void mutate(() => api.clearCart(), "clear")}
              type="button"
            >
              Clear cart
            </button>
          </aside>
        </div>
      )}
    </section>
  );
}
