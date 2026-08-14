# Order Processing User Guide

This guide covers the implemented customer order workflow. Use simulated data in PoC
demonstrations. Sign in through Keycloak with a `customer` account; all business requests
travel through API Gateway, and backend ownership checks use the verified JWT subject.

## Cart and checkout

1. Open `/products`, find an active product and use the available add-to-cart action.
2. Open `/cart`. Increase or decrease quantity, remove a line, or clear the cart.
3. Treat the displayed cart subtotal as an estimate. It is clearly marked as
   non-authoritative because checkout re-reads current Catalogue prices and availability.
4. Open `/checkout`, review the lines and select **Place order**. The frontend sends no
   accepted price or total. It creates one idempotency key for this deliberate attempt.
5. If a transport timeout makes the outcome unknown, use **Retry safely**. The same key is
   reused so the service returns the existing result rather than creating another order.
6. On success, `/orders/confirmation/{orderId}` displays the server-generated order
   number, status, immutable item snapshots and calculated total. Payment is not in scope.

A stock/product/price conflict returns a reviewable conflict state rather than silently
accepting stale browser data. A final-unit race may legitimately allow one customer and
reject another; inventory must never become negative.

## Order history and cancellation

- `/orders` lists the authenticated customer's orders.
- `/orders/{orderId}` displays the checkout-time SKU, name, quantity, unit price, line
  total, current status and status timeline. Later Catalogue changes do not rewrite it.
- An eligible CONFIRMED or PROCESSING order can be cancelled. Cancellation is idempotent
  and completes only after active inventory reservations are released. On an eligible
  order detail page, the red **Cancel order** button performs this action after explicit
  confirmation. It does not perform a payment refund because payments are outside scope.

A customer cannot retrieve another customer's cart or order by changing an identifier;
the service returns restricted/not-found behavior. Frontend navigation is only a UX
control—the backend remains authoritative.

## Evidence boundary

React order component tests pass. The retained API-driven E2E suite passed cart,
checkout, confirmation, history, audit, IDOR, inventory race, cancellation, Kafka recovery
and Redis fallback scenarios through the deployed Gateway. The Firefox happy path was
manually validated on 2026-08-14 with synthetic SKU `ORDER-DEMO-HAPPY-001`, quantity 2,
and confirmed order number `SS-20260814-1EA297D4F967`. The other manual demonstration
scenarios remain separate evidence and must not be inferred from that browser run.
