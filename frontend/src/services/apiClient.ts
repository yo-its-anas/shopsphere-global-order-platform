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

type AccessTokenProvider = () => Promise<string>;

function messageForStatus(status: number): string {
  if (status === 400 || status === 422) return "Please review the submitted information.";
  if (status === 401) return "Your session is not authorized for this request.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested record was not found.";
  if (status === 409) return "The request conflicts with the current record.";
  if (status === 503 || status === 504)
    return "The requested capability is temporarily unavailable.";
  return "The API request could not be completed.";
}

export function createApiClient(
  baseUrl = environment.apiBaseUrl,
  accessTokenProvider?: AccessTokenProvider,
): ApiClient {
  return {
    async request<TResponse>(path: string, init: RequestInit = {}): Promise<TResponse> {
      const normalizedPath = path.startsWith("/") ? path : "/" + path;
      const headers = new Headers(init.headers);
      if (!headers.has("Accept")) headers.set("Accept", "application/json");
      if (init.body && !headers.has("Content-Type"))
        headers.set("Content-Type", "application/json");
      if (!headers.has("X-Request-ID") && globalThis.crypto?.randomUUID) {
        headers.set("X-Request-ID", globalThis.crypto.randomUUID());
      }
      if (accessTokenProvider) {
        headers.set("Authorization", `Bearer ${await accessTokenProvider()}`);
      }

      let response: Response;
      try {
        response = await fetch(baseUrl + normalizedPath, { ...init, headers });
      } catch {
        throw new ApiClientError("The API Gateway is unavailable.", 0, null);
      }

      if (!response.ok) {
        throw new ApiClientError(
          messageForStatus(response.status),
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
