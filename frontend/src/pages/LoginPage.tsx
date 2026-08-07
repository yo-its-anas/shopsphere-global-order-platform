import { Link } from "react-router-dom";

import { DemoDataBadge } from "../components/DemoDataBadge";

export function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <span className="brand__mark brand__mark--large" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </span>
        <span className="eyebrow">ShopSphere Global</span>
        <h1>Enterprise Operations</h1>
        <DemoDataBadge />
        <p>
          Authentication is intentionally not implemented. Keycloak integration and protected routes
          are future work.
        </p>
        <Link className="button button--primary" to="/dashboard">
          Open demonstration dashboard
        </Link>
      </section>
    </main>
  );
}
