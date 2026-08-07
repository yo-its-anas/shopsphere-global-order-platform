import { useState } from "react";
import { RouterProvider } from "react-router-dom";

import { createAppRouter } from "./router";

type AppRouter = ReturnType<typeof createAppRouter>;

interface AppProps {
  router?: AppRouter;
}

export function App({ router }: AppProps) {
  const [applicationRouter] = useState(() => router ?? createAppRouter());

  return <RouterProvider router={applicationRouter} />;
}
