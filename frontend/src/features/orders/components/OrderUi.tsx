import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { ApiClientError } from "../../../services/apiClient";
import type { OrderStatus } from "../../../types/order";

export function OrderPageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-heading order-heading">
      <div className="page-heading__title">
        <p className="eyebrow">Enterprise Order Processing</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function OrderError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = error instanceof ApiClientError ? error : null;
  return (
    <div className="form-alert" role="alert">
      <strong>Order request unsuccessful.</strong>{" "}
      {error instanceof Error ? error.message : "The request could not be completed."}
      {apiError?.requestId && (
        <small className="request-reference">Reference: {apiError.requestId}</small>
      )}
      {onRetry && (
        <button
          className="button button--secondary button--compact"
          onClick={onRetry}
          type="button"
        >
          Retry safely
        </button>
      )}
    </div>
  );
}

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`order-status order-status--${status.toLowerCase()}`}>
      <i aria-hidden="true" />
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function OrderPagination({
  offset,
  limit,
  total,
  onChange,
}: {
  offset: number;
  limit: number;
  total: number;
  onChange(value: number): void;
}) {
  return (
    <footer className="pagination">
      <span>
        Showing {total === 0 ? 0 : offset + 1}–{Math.min(offset + limit, total)} of {total}
      </span>
      <div>
        <button
          className="button button--secondary button--compact"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
          type="button"
        >
          Previous
        </button>
        <button
          className="button button--secondary button--compact"
          disabled={offset + limit >= total}
          onClick={() => onChange(offset + limit)}
          type="button"
        >
          Next
        </button>
      </div>
    </footer>
  );
}

export function ViewOrderLink({
  orderId,
  operational = false,
}: {
  orderId: string;
  operational?: boolean;
}) {
  return (
    <Link
      className="button-link"
      to={`${operational ? "/order-management" : "/orders"}/${orderId}`}
    >
      View details
    </Link>
  );
}
