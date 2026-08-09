import { useState } from "react";
import { RouterProvider } from "react-router-dom";

import { createAppRouter } from "./router";
import { AuthProvider } from "../features/auth/AuthContext";
import { AuthContext } from "../features/auth/context";
import type { AuthContextValue } from "../types/auth";

type AppRouter = ReturnType<typeof createAppRouter>;

interface AppProps {
  router?: AppRouter;
  auth?: AuthContextValue;
}

export function App({ router, auth }: AppProps) {
  const [applicationRouter] = useState(() => router ?? createAppRouter());
  const routerView = <RouterProvider router={applicationRouter} />;

  if (auth) {
    return <AuthContext.Provider value={auth}>{routerView}</AuthContext.Provider>;
  }

  return <AuthProvider>{routerView}</AuthProvider>;
}
