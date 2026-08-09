import { Navigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function CustomerLandingPage() {
  const auth = useAuth();
  if (auth.hasRole("customer")) return <Navigate replace to="/profile" />;
  if (auth.hasRole("support") || auth.hasRole("operations_admin")) {
    return <Navigate replace to="/customer-administration" />;
  }
  return <Navigate replace to="/unauthorized" />;
}
