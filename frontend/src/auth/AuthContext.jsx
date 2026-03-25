import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  hasFreshAccessToken,
  getAccessToken,
  clearTokens,
} from './tokenStorage';
import { redirectToHostedLogin, refreshAccessToken, redirectToLogout } from './cognitoOAuth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const bootstrap = useCallback(async () => {
    try {
      if (hasFreshAccessToken()) {
        setAuthenticated(true);
        setReady(true);
        return;
      }
      const ok = await refreshAccessToken();
      setAuthenticated(ok);
    } catch {
      clearTokens();
      setAuthenticated(false);
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
      login,
      logout,
      getToken,
      refreshSession: bootstrap,
    }),
    [ready, authenticated, login, logout, getToken, bootstrap]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}
