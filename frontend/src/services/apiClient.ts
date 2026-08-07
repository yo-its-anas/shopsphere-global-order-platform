import { environment } from "../config/environment";

export class ApiClientError extends Error {
  readonly status: number;
  readonly requestId: string | null;

  constructor(message: string, status: number, requestId: string | null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.requestId = requestId;
  }
}

export interface ApiClient {
  request<TResponse>(path: string, init?: RequestInit): Promise<TResponse>;
}

export function createApiClient(baseUrl = environment.apiBaseUrl): ApiClient {
  return {
    async request<TResponse>(path: string, init: RequestInit = {}): Promise<TResponse> {
      const normalizedPath = path.startsWith("/") ? path : "/" + path;
      const response = await fetch(baseUrl + normalizedPath, {
        ...init,
        headers: {
          Accept: "application/json",
          ...init.headers,
        },
      });

      if (!response.ok) {
        throw new ApiClientError(
          "API request failed with status " + response.status + ".",
          response.status,
          response.headers.get("X-Request-ID"),
        );
      }

      if (response.status === 204) {
        return undefined as TResponse;
      }

      return (await response.json()) as TResponse;
    },
  };
}

export const apiClient = createApiClient();
