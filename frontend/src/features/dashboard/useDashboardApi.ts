import { useMemo } from "react";

import { environment } from "../../config/environment";
import { createApiClient } from "../../services/apiClient";
import { DashboardApi } from "../../services/dashboardApi";
import { useAuth } from "../auth/useAuth";

export function useDashboardApi(): DashboardApi {
  const auth = useAuth();
  return useMemo(
    () => new DashboardApi(createApiClient(environment.apiBaseUrl, auth.getAccessToken)),
    [auth.getAccessToken],
  );
}
