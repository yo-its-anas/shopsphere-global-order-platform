import {
  Navigate,
  createBrowserRouter,
  createMemoryRouter,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../layouts/AppShell";
import { AuthenticatedRoute, RoleRoute } from "../features/auth/RouteGuards";
import { AccountActivityPage } from "../pages/AccountActivityPage";
import { AddressesPage } from "../pages/AddressesPage";
import { CustomerAdministrationPage } from "../pages/CustomerAdministrationPage";
import { CustomerLandingPage } from "../pages/CustomerLandingPage";
import { CustomerProfilePage } from "../pages/CustomerProfilePage";
import { DashboardPage } from "../pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";
import { RegisterPage } from "../pages/RegisterPage";
import { UnauthorizedPage } from "../pages/UnauthorizedPage";

export const appRoutes: RouteObject[] = [
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/",
    element: (
      <AuthenticatedRoute>
        <AppShell />
      </AuthenticatedRoute>
    ),
    children: [
      { index: true, element: <Navigate replace to="/dashboard" /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "customers", element: <CustomerLandingPage /> },
      {
        path: "profile",
        element: (
          <RoleRoute roles={["customer"]}>
            <CustomerProfilePage />
          </RoleRoute>
        ),
      },
      {
        path: "addresses",
        element: (
          <RoleRoute roles={["customer"]}>
            <AddressesPage />
          </RoleRoute>
        ),
      },
      {
        path: "account-activity",
        element: (
          <RoleRoute roles={["customer"]}>
            <AccountActivityPage />
          </RoleRoute>
        ),
      },
      {
        path: "customer-administration",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <CustomerAdministrationPage />
          </RoleRoute>
        ),
      },
      { path: "unauthorized", element: <UnauthorizedPage /> },
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
