import {
  Navigate,
  createBrowserRouter,
  createMemoryRouter,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../layouts/AppShell";
import { AuthenticatedRoute, RoleRoute } from "../features/auth/RouteGuards";
import { CategoriesPage } from "../features/catalogue/pages/CategoriesPage";
import { InventoryAdjustmentPage } from "../features/catalogue/pages/InventoryAdjustmentPage";
import { InventoryMovementsPage } from "../features/catalogue/pages/InventoryMovementsPage";
import { InventoryPage } from "../features/catalogue/pages/InventoryPage";
import { InventoryStatisticsPage } from "../features/catalogue/pages/InventoryStatisticsPage";
import { PricingPage } from "../features/catalogue/pages/PricingPage";
import { ProductDetailsPage } from "../features/catalogue/pages/ProductDetailsPage";
import { ProductFormPage } from "../features/catalogue/pages/ProductFormPage";
import { ProductsPage } from "../features/catalogue/pages/ProductsPage";
import { CheckoutPage } from "../features/orders/pages/CheckoutPage";
import { MyOrdersPage } from "../features/orders/pages/MyOrdersPage";
import { OrderConfirmationPage } from "../features/orders/pages/OrderConfirmationPage";
import { OrderDetailsPage } from "../features/orders/pages/OrderDetailsPage";
import { OrderManagementPage } from "../features/orders/pages/OrderManagementPage";
import { ShoppingCartPage } from "../features/orders/pages/ShoppingCartPage";
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
          <RoleRoute roles={["customer", "support", "operations_admin"]}>
            <ProductsPage />
          </RoleRoute>
        ),
      },
      {
        path: "products/new",
        element: (
          <RoleRoute roles={["operations_admin"]}>
            <ProductFormPage />
          </RoleRoute>
        ),
      },
      {
        path: "products/:productId",
        element: (
          <RoleRoute roles={["customer", "support", "operations_admin"]}>
            <ProductDetailsPage />
          </RoleRoute>
        ),
      },
      {
        path: "products/:productId/edit",
        element: (
          <RoleRoute roles={["operations_admin"]}>
            <ProductFormPage />
          </RoleRoute>
        ),
      },
      {
        path: "categories",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <CategoriesPage />
          </RoleRoute>
        ),
      },
      {
        path: "pricing",
        element: (
          <RoleRoute roles={["customer", "support", "operations_admin"]}>
            <PricingPage />
          </RoleRoute>
        ),
      },
      {
        path: "inventory",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <InventoryPage />
          </RoleRoute>
        ),
      },
      {
        path: "inventory/statistics",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <InventoryStatisticsPage />
          </RoleRoute>
        ),
      },
      {
        path: "inventory/:productId/adjust",
        element: (
          <RoleRoute roles={["operations_admin"]}>
            <InventoryAdjustmentPage />
          </RoleRoute>
        ),
      },
      {
        path: "inventory/:productId/movements",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <InventoryMovementsPage />
          </RoleRoute>
        ),
      },
      {
        path: "cart",
        element: (
          <RoleRoute roles={["customer"]}>
            <ShoppingCartPage />
          </RoleRoute>
        ),
      },
      {
        path: "checkout",
        element: (
          <RoleRoute roles={["customer"]}>
            <CheckoutPage />
          </RoleRoute>
        ),
      },
      {
        path: "orders",
        element: (
          <RoleRoute roles={["customer"]}>
            <MyOrdersPage />
          </RoleRoute>
        ),
      },
      {
        path: "orders/confirmation/:orderId",
        element: (
          <RoleRoute roles={["customer"]}>
            <OrderConfirmationPage />
          </RoleRoute>
        ),
      },
      {
        path: "orders/:orderId",
        element: (
          <RoleRoute roles={["customer"]}>
            <OrderDetailsPage />
          </RoleRoute>
        ),
      },
      {
        path: "order-management",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <OrderManagementPage />
          </RoleRoute>
        ),
      },
      {
        path: "order-management/:orderId",
        element: (
          <RoleRoute roles={["support", "operations_admin"]}>
            <OrderDetailsPage operational />
          </RoleRoute>
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
