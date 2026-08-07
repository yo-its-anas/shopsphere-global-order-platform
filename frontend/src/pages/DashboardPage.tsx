import { DashboardView } from "../features/dashboard/components/DashboardView";
import { mockDashboardData } from "../mocks/dashboard";

export function DashboardPage() {
  return <DashboardView data={mockDashboardData} />;
}
