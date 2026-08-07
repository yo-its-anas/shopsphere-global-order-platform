import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <span className="eyebrow">404</span>
        <h1>Page not found</h1>
        <p>The requested ShopSphere route does not exist.</p>
        <Link className="button button--primary" to="/dashboard">
          Return to dashboard
        </Link>
      </section>
    </main>
  );
}
