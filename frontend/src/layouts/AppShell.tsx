import { NavLink, Outlet } from "react-router-dom";

import { DemoDataBadge } from "../components/DemoDataBadge";
import { Icon, type IconName } from "../components/Icon";
import { environment } from "../config/environment";
import { useAuth } from "../features/auth/useAuth";
import type { ShopSphereRole } from "../types/auth";

interface NavigationItem {
  label: string;
  path: string;
  icon: IconName;
  roles?: ShopSphereRole[];
}

const navigationItems: NavigationItem[] = [
  { label: "Executive Dashboard", path: "/dashboard", icon: "dashboard" },
  { label: "Customers", path: "/customers", icon: "customers" },
  { label: "My Profile", path: "/profile", icon: "profile", roles: ["customer"] },
  { label: "Addresses", path: "/addresses", icon: "addresses", roles: ["customer"] },
  { label: "Account Activity", path: "/account-activity", icon: "audit", roles: ["customer"] },
  {
    label: "Customer Administration",
    path: "/customer-administration",
    icon: "administration",
    roles: ["support", "operations_admin"],
  },
  { label: "Product Catalogue", path: "/products", icon: "products" },
  {
    label: "Categories",
    path: "/categories",
    icon: "products",
    roles: ["support", "operations_admin"],
  },
  { label: "Pricing", path: "/pricing", icon: "revenue" },
  {
    label: "Inventory",
    path: "/inventory",
    icon: "inventory",
    roles: ["support", "operations_admin"],
  },
  {
    label: "Inventory Statistics",
    path: "/inventory/statistics",
    icon: "health",
    roles: ["support", "operations_admin"],
  },
  { label: "Orders", path: "/orders", icon: "orders" },
  { label: "Platform Health", path: "/platform-health", icon: "health" },
  { label: "Audit Logs", path: "/audit-logs", icon: "audit" },
];

export function AppShell() {
  const auth = useAuth();
  const visibleNavigation = navigationItems.filter(
    (item) => !item.roles || item.roles.some((role) => auth.hasRole(role)),
  );
  const displayName =
    [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(" ") ||
    auth.user?.username ||
    "Authenticated user";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>
            <strong>ShopSphere Global</strong>
            <small>Enterprise Operations</small>
          </span>
        </div>

        <nav aria-label="Primary navigation" className="sidebar__nav">
          {visibleNavigation.map((item) => (
            <NavLink
              className={({ isActive }) => "nav-link" + (isActive ? " nav-link--active" : "")}
              key={item.path}
              to={item.path}
            >
              <Icon name={item.icon} size={21} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__notice">
          <DemoDataBadge />
          <p>
            Badge applies only to dashboard fixtures. Customer and catalogue pages use gateway APIs.
          </p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <label className="global-search">
            <span className="sr-only">Global search</span>
            <Icon name="search" size={21} />
            <input
              aria-describedby="search-help"
              disabled
              placeholder="Global Search..."
              type="search"
            />
          </label>
          <span className="sr-only" id="search-help">
            Search is a visual placeholder and is not connected.
          </span>

          <div className="topbar__context">
            <span>
              Environment: <strong>{environment.displayName}</strong>
            </span>
            {environment.usesMockData && <DemoDataBadge />}
            <span className="topbar__user">{displayName}</span>
            <button
              className="button button--secondary topbar__logout"
              onClick={() => void auth.logout()}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
