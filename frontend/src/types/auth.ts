export type ShopSphereRole = "customer" | "support" | "operations_admin";

export interface AuthenticatedUser {
  username?: string;
  email?: string;
  firstName?: string;
  lastName?: string;
}

export interface AuthContextValue {
  initialized: boolean;
  authenticated: boolean;
  user: AuthenticatedUser | null;
  roles: ReadonlySet<ShopSphereRole>;
  login(): Promise<void>;
  register(): Promise<void>;
  logout(): Promise<void>;
  getAccessToken(): Promise<string>;
  hasRole(role: ShopSphereRole): boolean;
}
