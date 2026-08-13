import { useMemo } from "react";

import { environment } from "../../config/environment";
import { createApiClient } from "../../services/apiClient";
import { OrderApi } from "../../services/orderApi";
import { useAuth } from "../auth/useAuth";

export function useOrderApi(): OrderApi {
  const auth = useAuth();
  return useMemo(
    () => new OrderApi(createApiClient(environment.apiBaseUrl, auth.getAccessToken)),
    [auth.getAccessToken],
  );
}
