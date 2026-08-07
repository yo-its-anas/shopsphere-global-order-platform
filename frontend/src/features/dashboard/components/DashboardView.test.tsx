import { render, screen } from "@testing-library/react";

import { mockDashboardData } from "../../../mocks/dashboard";
import { DashboardView } from "./DashboardView";

describe("DashboardView", () => {
  it("renders typed mock KPIs, orders, health metrics, and demo disclosure", () => {
    render(<DashboardView data={mockDashboardData} />);

    expect(screen.getByText("Demo Orders")).toBeInTheDocument();
    expect(screen.getByText("DEMO-1042")).toBeInTheDocument();
    expect(screen.getByText("API Gateway (simulated)")).toBeInTheDocument();
    expect(screen.getByText(/not live metrics/i)).toBeInTheDocument();
  });
});
