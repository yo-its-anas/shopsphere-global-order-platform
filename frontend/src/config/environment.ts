const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export const environment = Object.freeze({
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL),
  displayName: import.meta.env.MODE === "production" ? "PoC Build" : "Development",
  usesMockData: true,
});
