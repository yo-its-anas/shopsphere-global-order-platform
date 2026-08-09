const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_KEYCLOAK_URL = "http://localhost:8081";

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export const environment = Object.freeze({
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL),
  keycloak: Object.freeze({
    url: normalizeBaseUrl(import.meta.env.VITE_KEYCLOAK_URL ?? DEFAULT_KEYCLOAK_URL),
    realm: import.meta.env.VITE_KEYCLOAK_REALM ?? "shopsphere",
    clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "shopsphere-frontend",
  }),
  displayName: import.meta.env.MODE === "production" ? "PoC Build" : "Development",
  usesMockData: true,
});
