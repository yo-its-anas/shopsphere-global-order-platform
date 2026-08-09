import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider, type KeycloakAdapter } from "./AuthContext";
import { useAuth } from "./useAuth";

function AuthActions() {
  const auth = useAuth();
  return (
    <div>
      <span>{auth.authenticated ? "authenticated" : "signed out"}</span>
      <button onClick={() => void auth.login()} type="button">
        Login
      </button>
      <button onClick={() => void auth.register()} type="button">
        Register
      </button>
      <button onClick={() => void auth.logout()} type="button">
        Logout
      </button>
    </div>
  );
}

describe("Keycloak authentication provider", () => {
  it("initializes standard flow with S256 PKCE once and delegates identity redirects", async () => {
    const adapter: KeycloakAdapter = {
      authenticated: false,
      init: vi.fn().mockResolvedValue(false),
      login: vi.fn().mockResolvedValue(undefined),
      register: vi.fn().mockResolvedValue(undefined),
      logout: vi.fn().mockResolvedValue(undefined),
      updateToken: vi.fn().mockResolvedValue(false),
      clearToken: vi.fn(),
      hasRealmRole: vi.fn().mockReturnValue(false),
      loadUserProfile: vi.fn().mockResolvedValue({}),
    };
    const adapterFactory = () => adapter;
    const user = userEvent.setup();

    render(
      <StrictMode>
        <AuthProvider adapterFactory={adapterFactory}>
          <AuthActions />
        </AuthProvider>
      </StrictMode>,
    );

    expect(await screen.findByText("signed out")).toBeInTheDocument();
    expect(adapter.init).toHaveBeenCalledTimes(1);
    expect(adapter.init).toHaveBeenCalledWith({
      onLoad: "check-sso",
      flow: "standard",
      pkceMethod: "S256",
      checkLoginIframe: true,
      enableLogging: false,
    });

    await user.click(screen.getByRole("button", { name: "Login" }));
    await user.click(screen.getByRole("button", { name: "Register" }));
    await user.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() =>
      expect(adapter.login).toHaveBeenCalledWith({
        redirectUri: "http://localhost:3000/dashboard",
      }),
    );
    expect(adapter.register).toHaveBeenCalledWith({ redirectUri: "http://localhost:3000/profile" });
    expect(adapter.logout).toHaveBeenCalledWith({ redirectUri: "http://localhost:3000/login" });
  });
});
