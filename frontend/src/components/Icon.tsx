import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "alert"
  | "addresses"
  | "administration"
  | "audit"
  | "chevron"
  | "customers"
  | "dashboard"
  | "health"
  | "inventory"
  | "orders"
  | "products"
  | "profile"
  | "revenue"
  | "search"
  | "shipments";

interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

const paths: Record<IconName, ReactNode> = {
  alert: <path d="M12 3 2.8 20h18.4L12 3Zm0 6v5m0 3v.1" />,
  addresses: (
    <path d="M12 21s7-5.1 7-12a7 7 0 1 0-14 0c0 6.9 7 12 7 12Zm0-9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
  ),
  administration: (
    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2m7.5-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM19 8v6m3-3h-6" />
  ),
  audit: <path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5m3-3v6l4 2" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  customers: (
    <>
      <path d="M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M19 8v6m3-3h-6" />
    </>
  ),
  dashboard: <path d="M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z" />,
  health: <path d="M3 12h4l2-5 4 10 2-5h6M4 4h16v16H4V4Z" />,
  inventory: <path d="M3 9 12 4l9 5-9 5-9-5Zm0 0v10h18V9M8 21v-7h8v7" />,
  orders: <path d="M3 4h2l2.4 11h10.8l2-7H7m2 11h.1m8.9 0h.1" />,
  products: <path d="M4 4h16v5H4V4Zm2 5v11h12V9M9 13h6" />,
  profile: <path d="M20 21a8 8 0 0 0-16 0m8-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />,
  revenue: <path d="M3 7h18v10H3V7Zm4 7h.1M17 10h.1M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />,
  search: <path d="m21 21-4.4-4.4m2.4-5.1a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />,
  shipments: (
    <path d="M3 6h11v11H3V6Zm11 4h4l3 3v4h-7v-7ZM7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm11 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
  ),
};

export function Icon({ name, size = 20, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      {...props}
    >
      {paths[name]}
    </svg>
  );
}
