import { NavLink, Outlet } from "react-router-dom";

import { DemoDataBadge } from "../components/DemoDataBadge";
import { Icon, type IconName } from "../components/Icon";
import { environment } from "../config/environment";

interface NavigationItem {
  label: string;
  path: string;
  icon: IconName;
}

const navigationItems: NavigationItem[] = [
  { label: "Executive Dashboard", path: "/dashboard", icon: "dashboard" },
  { label: "Customers", path: "/customers", icon: "customers" },
  { label: "Product Catalogue", path: "/products", icon: "products" },
  { label: "Inventory", path: "/inventory", icon: "inventory" },
  { label: "Orders", path: "/orders", icon: "orders" },
  { label: "Platform Health", path: "/platform-health", icon: "health" },
  { label: "Audit Logs", path: "/audit-logs", icon: "audit" },
];

export function AppShell() {
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
          {navigationItems.map((item) => (
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
          <p>No live services connected</p>
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
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
