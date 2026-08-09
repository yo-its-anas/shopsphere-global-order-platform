import { Link } from "react-router-dom";

export function UnauthorizedPage() {
  return (
    <div className="customer-page">
      <section className="async-state async-state--error" aria-live="polite">
        <div>
          <h1>Access not authorized</h1>
          <p>
            Your current role does not provide access to this capability. Backend authorization
            remains authoritative.
          </p>
          <Link className="button button--secondary" to="/dashboard">
            Return to dashboard
          </Link>
        </div>
      </section>
    </div>
  );
}
