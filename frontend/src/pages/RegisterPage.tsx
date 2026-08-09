import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function RegisterPage() {
  const auth = useAuth();
  if (auth.authenticated) return <Navigate replace to="/profile" />;

  return (
    <main className="identity-page">
      <section className="identity-card" aria-labelledby="registration-title">
        <span className="identity-card__mark" aria-hidden="true">
          SG
        </span>
        <h1 id="registration-title">Create your ShopSphere account</h1>
        <p>
          Registration continues securely in Keycloak. Your ShopSphere customer profile is
          provisioned after successful authentication.
        </p>
        <button
          className="button button--primary identity-card__action"
          onClick={() => void auth.register()}
          type="button"
        >
          Continue to secure registration
        </button>
        <div className="identity-card__divider" />
        <Link className="identity-card__back" to="/login">
          Back to sign in
        </Link>
        <small>No password, token, or credential is collected by the ShopSphere frontend.</small>
      </section>
    </main>
  );
}
