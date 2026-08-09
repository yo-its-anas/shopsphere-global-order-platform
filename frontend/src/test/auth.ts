import type { AuthContextValue, AuthenticatedUser, ShopSphereRole } from "../types/auth";

export function createTestAuth(
  options: {
    authenticated?: boolean;
    roles?: ShopSphereRole[];
    user?: AuthenticatedUser | null;
  } = {},
): AuthContextValue {
  const roles = new Set(options.roles ?? []);
  return {
    initialized: true,
    authenticated: options.authenticated ?? true,
    roles,
    user: options.user ?? { firstName: "Test", lastName: "User", email: "test@example.invalid" },
    login: async () => undefined,
    register: async () => undefined,
    logout: async () => undefined,
    getAccessToken: async () => "test-access-token",
    hasRole: (role) => roles.has(role),
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
