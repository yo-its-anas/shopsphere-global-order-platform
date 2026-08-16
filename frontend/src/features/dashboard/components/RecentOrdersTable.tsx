import { AsyncState } from "../../../components/AsyncState";
import type { DashboardOrderStatus, RecentOrder } from "../../../types/dashboard";

const statusTone: Record<DashboardOrderStatus, string> = {
  Fulfilled: "positive",
  Processing: "warning",
  Exception: "critical",
  Pending: "neutral",
  Cancelled: "neutral",
};

interface RecentOrdersTableProps {
  orders: RecentOrder[];
}

export function RecentOrdersTable({ orders }: RecentOrdersTableProps) {
  return (
    <section className="panel orders-panel" aria-labelledby="recent-orders-title">
      <header className="panel__header">
        <div>
          <h2 id="recent-orders-title">Recent Orders</h2>
        </div>
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
