import Keycloak, { type KeycloakProfile } from "keycloak-js";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { AsyncState } from "../../components/AsyncState";
import { environment } from "../../config/environment";
import type { AuthContextValue, AuthenticatedUser, ShopSphereRole } from "../../types/auth";
import { AuthContext } from "./context";

const supportedRoles: ShopSphereRole[] = ["customer", "support", "operations_admin"];

export interface KeycloakAdapter {
  authenticated?: boolean;
  token?: string;
  onAuthLogout?: () => void;
  onAuthRefreshSuccess?: () => void;
  onAuthRefreshError?: () => void;
  onTokenExpired?: () => void;
  init(options: {
    onLoad: "check-sso";
    flow: "standard";
    pkceMethod: "S256";
    checkLoginIframe: boolean;
    enableLogging: boolean;
  }): Promise<boolean>;
  login(options: { redirectUri: string }): Promise<void>;
  register(options: { redirectUri: string }): Promise<void>;
  logout(options: { redirectUri: string }): Promise<void>;
  updateToken(minValidity: number): Promise<boolean>;
  clearToken(): void;
  hasRealmRole(role: string): boolean;
  loadUserProfile(): Promise<KeycloakProfile>;
}

function createKeycloakAdapter(): KeycloakAdapter {
  return new Keycloak(environment.keycloak);
}

function currentUrl(path: string): string {
  return new URL(path, window.location.origin).toString();
}

function toUser(profile: KeycloakProfile): AuthenticatedUser {
  return {
    username: profile.username,
    email: profile.email,
    firstName: profile.firstName,
    lastName: profile.lastName,
  };
}

interface AuthProviderProps {
  children: ReactNode;
  adapterFactory?: () => KeycloakAdapter;
}

export function AuthProvider({
  children,
  adapterFactory = createKeycloakAdapter,
}: AuthProviderProps) {
  const adapterRef = useRef<KeycloakAdapter | null>(null);
  const initializationRef = useRef<Promise<boolean> | null>(null);
  const getAdapter = useCallback(() => {
    if (adapterRef.current === null) adapterRef.current = adapterFactory();
    return adapterRef.current;
  }, [adapterFactory]);
  const [initialized, setInitialized] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [roles, setRoles] = useState<ReadonlySet<ShopSphereRole>>(new Set());
  const [initializationFailed, setInitializationFailed] = useState(false);

  const clearSession = useCallback(() => {
    const adapter = getAdapter();
    adapter.clearToken();
    setAuthenticated(false);
    setUser(null);
    setRoles(new Set());
  }, [getAdapter]);

  const refreshIdentity = useCallback(async () => {
    const adapter = getAdapter();
    const activeRoles = new Set(supportedRoles.filter((role) => adapter.hasRealmRole(role)));
    const profile = await adapter.loadUserProfile();
    setRoles(activeRoles);
    setUser(toUser(profile));
    setAuthenticated(true);
  }, [getAdapter]);

  useEffect(() => {
    let active = true;
    const adapter = getAdapter();

    adapter.onAuthLogout = clearSession;
    adapter.onAuthRefreshSuccess = () => {
      void refreshIdentity().catch(clearSession);
    };
    adapter.onAuthRefreshError = clearSession;
    adapter.onTokenExpired = () => {
      void adapter.updateToken(30).catch(clearSession);
    };

    if (initializationRef.current === null) {
      initializationRef.current = adapter.init({
        onLoad: "check-sso",
        flow: "standard",
        pkceMethod: "S256",
        checkLoginIframe: true,
        enableLogging: false,
      });
    }

    void initializationRef.current
      .then(async (isAuthenticated) => {
        if (!active) return;
        if (isAuthenticated) {
          await refreshIdentity();
        }
        if (active) {
          setAuthenticated(isAuthenticated);
          setInitialized(true);
        }
      })
      .catch(() => {
        if (active) {
          setInitializationFailed(true);
          setInitialized(true);
        }
      });

    const refreshTimer = window.setInterval(() => {
      if (adapter.authenticated) {
        void adapter.updateToken(30).catch(clearSession);
      }
    }, 20_000);

    return () => {
      active = false;
      window.clearInterval(refreshTimer);
      adapter.onAuthLogout = undefined;
      adapter.onAuthRefreshSuccess = undefined;
      adapter.onAuthRefreshError = undefined;
      adapter.onTokenExpired = undefined;
    };
  }, [clearSession, getAdapter, refreshIdentity]);

  const value = useMemo<AuthContextValue>(
    () => ({
      initialized,
      authenticated,
      user,
      roles,
      login: () => getAdapter().login({ redirectUri: currentUrl("/dashboard") }),
      register: () => getAdapter().register({ redirectUri: currentUrl("/profile") }),
      logout: () => getAdapter().logout({ redirectUri: currentUrl("/login") }),
      getAccessToken: async () => {
        const adapter = getAdapter();
        try {
          await adapter.updateToken(30);
        } catch {
          clearSession();
          throw new Error("The authentication session has expired.");
        }
        if (!adapter.token) {
          clearSession();
          throw new Error("No authenticated access token is available.");
        }
        return adapter.token;
      },
      hasRole: (role) => roles.has(role),
    }),
    [authenticated, clearSession, getAdapter, initialized, roles, user],
  );

  if (!initialized) {
    return (
      <main className="auth-state-page">
        <AsyncState
          kind="loading"
          title="Checking your session"
          message="Connecting securely to ShopSphere identity services."
        />
      </main>
    );
  }

  if (initializationFailed) {
    return (
      <main className="auth-state-page">
        <AsyncState
          kind="error"
          title="Identity service unavailable"
          message="ShopSphere could not initialize secure sign-in. Please try again when Keycloak is available."
          onRetry={() => window.location.reload()}
        />
      </main>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
