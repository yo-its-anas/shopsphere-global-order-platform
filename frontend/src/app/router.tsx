import {
  Navigate,
  createBrowserRouter,
  createMemoryRouter,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../layouts/AppShell";
import { DashboardPage } from "../pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";

export const appRoutes: RouteObject[] = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate replace to="/dashboard" /> },
      { path: "dashboard", element: <DashboardPage /> },
      {
        path: "customers",
        element: (
          <PlaceholderPage
            title="Customers"
            description="Customer identity and account presentation will be integrated later."
          />
        ),
      },
      {
        path: "products",
        element: (
          <PlaceholderPage
            title="Product Catalogue"
            description="Product catalogue presentation will be integrated later."
          />
        ),
      },
      {
        path: "inventory",
        element: (
          <PlaceholderPage
            title="Inventory"
            description="Inventory visibility and controls will be integrated later."
          />
        ),
      },
      {
        path: "orders",
        element: (
          <PlaceholderPage
            title="Orders"
            description="Enterprise order workflow presentation will be integrated later."
          />
        ),
      },
      {
        path: "platform-health",
        element: (
          <PlaceholderPage
            title="Platform Health"
            description="Live observability metrics are not connected in this foundation."
          />
        ),
      },
      {
        path: "audit-logs",
        element: (
          <PlaceholderPage
            title="Audit Logs"
            description="Audit search and security-event integration are future work."
          />
        ),
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export function createAppRouter(initialEntries?: string[]) {
  return initialEntries
    ? createMemoryRouter(appRoutes, { initialEntries })
    : createBrowserRouter(appRoutes);
}
