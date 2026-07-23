import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  hasFreshAccessToken,
  getAccessToken,
  clearTokens,
} from './tokenStorage';
import { redirectToHostedLogin, refreshAccessToken, redirectToLogout } from './cognitoOAuth';
import { getMe } from '../api/client';

const AuthContext = createContext(null);

const OPERATOR_ROLES = ['owner', 'admin'];

export function AuthProvider({ children }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [role, setRole] = useState(null);

  const bootstrap = useCallback(async () => {
    try {
      let ok = hasFreshAccessToken();
      if (!ok) {
        ok = await refreshAccessToken();
      }
      setAuthenticated(ok);

      if (ok) {
        // Fetch the user's role so the UI can gate the private operator surface.
        // A failure here degrades safely to "no role" (treated as non-operator).
        try {
          const me = await getMe();
          setRole(me?.role ?? null);
        } catch {
          setRole(null);
        }
      } else {
        setRole(null);
      }
    } catch {
      clearTokens();
      setAuthenticated(false);
      setRole(null);
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(() => {
    redirectToHostedLogin();
  }, []);

  const logout = useCallback(() => {
    redirectToLogout();
  }, []);

  const getToken = useCallback(() => getAccessToken(), []);

  const value = useMemo(
    () => ({
      ready,
      authenticated,
      role,
      isOperator: OPERATOR_ROLES.includes(role),
      login,
      logout,
      getToken,
      refreshSession: bootstrap,
    }),
    [ready, authenticated, role, login, logout, getToken, bootstrap]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}
