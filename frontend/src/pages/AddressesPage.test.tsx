import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "../app/App";
import { createAppRouter } from "../app/router";
import { createTestAuth, jsonResponse } from "../test/auth";

const savedAddress = {
  id: "fa11b120-1ba4-474a-9539-ab6961119528",
  label: "Head Office",
  recipient_name: "Amina Khan",
  line1: "100 Enterprise Way",
  line2: null,
  city: "Lahore",
  region: "Punjab",
  postal_code: "54000",
  country_code: "PK",
  phone: null,
  is_default: true,
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

describe("address workflow", () => {
  it("creates and then deletes an address through gateway endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(savedAddress, 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const user = userEvent.setup();
    render(
      <App
        auth={createTestAuth({ roles: ["customer"] })}
        router={createAppRouter(["/addresses"])}
      />,
    );

    expect(await screen.findByRole("heading", { name: "No addresses yet" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add new address" }));
    await user.type(screen.getByLabelText("Address label"), "Head Office");
    await user.type(screen.getByLabelText("Recipient name"), "Amina Khan");
    await user.type(screen.getByLabelText("Address line 1"), "100 Enterprise Way");
    await user.type(screen.getByLabelText("City"), "Lahore");
    await user.type(screen.getByLabelText("Region"), "Punjab");
    await user.type(screen.getByLabelText("Postal code"), "54000");
    await user.type(screen.getByLabelText("Country code"), "PK");
    await user.click(screen.getByLabelText("Make this the default address"));
    await user.click(screen.getByRole("button", { name: "Save address" }));

    expect(await screen.findByRole("heading", { name: "Head Office" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete Head Office" }));
    await user.click(screen.getByRole("button", { name: "Delete address" }));
    expect(await screen.findByRole("heading", { name: "No addresses yet" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain("/api/v1/customers/me/addresses");
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("POST");
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe("DELETE");
  });
});
