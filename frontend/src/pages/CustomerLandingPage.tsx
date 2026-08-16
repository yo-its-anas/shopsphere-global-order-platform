import { Navigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function CustomerLandingPage() {
  const auth = useAuth();
  if (auth.hasRole("support") || auth.hasRole("operations_admin")) {
    return <Navigate replace to="/customer-administration" />;
  }
  if (auth.hasRole("customer")) return <Navigate replace to="/profile" />;
  return <Navigate replace to="/unauthorized" />;
}
