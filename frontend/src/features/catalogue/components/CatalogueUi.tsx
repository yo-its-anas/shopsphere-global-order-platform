import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { ApiClientError } from "../../../services/apiClient";
import type { AvailabilityState, ProductStatus } from "../../../types/catalogue";

export function CapabilityError({ error }: { error: unknown }) {
  const requestId = error instanceof ApiClientError ? error.requestId : null;
  const message = error instanceof Error ? error.message : "The request could not be completed.";
  return (
    <div className="form-alert" role="alert">
      <strong>Request unsuccessful.</strong> {message}
      {requestId && <small className="request-reference">Reference: {requestId}</small>}
    </div>
  );
}

export function CataloguePageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-heading catalogue-heading">
      <div className="page-heading__title">
        <p className="eyebrow">Catalogue &amp; Inventory</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function StatusBadge({ status }: { status: ProductStatus | AvailabilityState | boolean }) {
  const normalized = typeof status === "boolean" ? (status ? "active" : "inactive") : status;
  const label = normalized.replaceAll("_", " ");
  return (
    <span className={`catalogue-status catalogue-status--${normalized}`}>
      <i aria-hidden="true" />
      {label}
    </span>
  );
}

export function Pagination({
  offset,
  limit,
  total,
  onChange,
}: {
  offset: number;
  limit: number;
  total: number;
  onChange(offset: number): void;
}) {
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + limit, total);
  return (
    <footer className="pagination">
      <span>
        Showing {first}–{last} of {total}
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

export function ProductLink({ id, children }: { id: string; children: ReactNode }) {
  return (
    <Link className="table-link" to={`/products/${id}`}>
      {children}
    </Link>
  );
}
