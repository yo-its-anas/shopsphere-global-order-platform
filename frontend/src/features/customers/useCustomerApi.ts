import { useMemo } from "react";

import { environment } from "../../config/environment";
import { useAuth } from "../auth/useAuth";
import { createApiClient } from "../../services/apiClient";
import { CustomerApi } from "../../services/customerApi";

export function useCustomerApi(): CustomerApi {
  const auth = useAuth();
  return useMemo(
    () => new CustomerApi(createApiClient(environment.apiBaseUrl, auth.getAccessToken)),
    [auth.getAccessToken],
  );
}
