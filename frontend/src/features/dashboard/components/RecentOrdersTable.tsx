import { AsyncState } from "../../../components/AsyncState";
import type { OrderStatus, RecentOrder } from "../../../types/dashboard";

const statusTone: Record<OrderStatus, string> = {
  Fulfilled: "positive",
  Processing: "warning",
  Exception: "critical",
};

interface RecentOrdersTableProps {
  orders: RecentOrder[];
}

export function RecentOrdersTable({ orders }: RecentOrdersTableProps) {
  return (
    <section className="panel orders-panel" aria-labelledby="recent-orders-title">
      <header className="panel__header">
        <div>
          <span className="eyebrow">Development fixture</span>
          <h2 id="recent-orders-title">Recent Orders</h2>
        </div>
        <span className="panel__meta">Mock records</span>
      </header>

      {orders.length === 0 ? (
        <AsyncState
          kind="empty"
          title="No recent orders"
          message="Orders returned by the API will appear here after integration."
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Date</th>
                <th>Status</th>
                <th className="align-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="mono order-id">{order.id}</td>
                  <td>{order.customer}</td>
                  <td className="muted">{order.placedAt}</td>
                  <td>
                    <span className="status">
                      <span
                        aria-hidden="true"
                        className={"status__dot tone-bg-" + statusTone[order.status]}
                      />
                      {order.status}
                    </span>
                  </td>
                  <td className="align-right mono">{order.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
