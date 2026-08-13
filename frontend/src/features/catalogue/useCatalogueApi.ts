import { useMemo } from "react";

import { environment } from "../../config/environment";
import { createApiClient } from "../../services/apiClient";
import { CatalogueApi } from "../../services/catalogueApi";
import { useAuth } from "../auth/useAuth";

export function useCatalogueApi(): CatalogueApi {
  const auth = useAuth();
  return useMemo(
    () => new CatalogueApi(createApiClient(environment.apiBaseUrl, auth.getAccessToken)),
    [auth.getAccessToken],
  );
}
