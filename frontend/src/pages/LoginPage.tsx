import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function LoginPage() {
  const auth = useAuth();
  if (auth.authenticated) return <Navigate replace to="/dashboard" />;

  return (
    <main className="identity-page">
      <section className="identity-card" aria-labelledby="sign-in-title">
        <span className="identity-card__mark" aria-hidden="true">
          SG
        </span>
        <h1 id="sign-in-title">Sign in to ShopSphere Global</h1>
        <p>Continue through the secure ShopSphere identity service.</p>
        <button
          className="button button--primary identity-card__action"
          onClick={() => void auth.login()}
          type="button"
        >
          Continue to secure sign in
        </button>
        <div className="identity-card__divider">
          <span>or</span>
        </div>
        <p className="identity-card__link">
          Don&apos;t have an account? <Link to="/register">Create an account</Link>
        </p>
        <small>
          Passwords and authentication are managed by Keycloak and are never handled by this
          application.
        </small>
      </section>
    </main>
  );
}
