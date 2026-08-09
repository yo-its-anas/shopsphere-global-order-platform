import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import type { ShopSphereRole } from "../../types/auth";
import { useAuth } from "./useAuth";

export function AuthenticatedRoute({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();

  if (!auth.authenticated) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }
  return children;
}

export function RoleRoute({ children, roles }: { children: ReactNode; roles: ShopSphereRole[] }) {
  const auth = useAuth();
  if (!roles.some((role) => auth.hasRole(role))) {
    return <Navigate replace to="/unauthorized" />;
  }
  return children;
}
