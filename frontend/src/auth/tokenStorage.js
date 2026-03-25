const KEYS = {
  access: 'rg_access_token',
  id: 'rg_id_token',
  refresh: 'rg_refresh_token',
  expiresAt: 'rg_expires_at',
  pkceVerifier: 'rg_pkce_verifier',
};

export function setTokens({ access_token, id_token, refresh_token, expires_in }) {
  if (access_token) sessionStorage.setItem(KEYS.access, access_token);
  if (id_token) sessionStorage.setItem(KEYS.id, id_token);
  if (refresh_token) sessionStorage.setItem(KEYS.refresh, refresh_token);
  if (expires_in != null) {
    const at = Date.now() + Number(expires_in) * 1000 - 60_000;
    sessionStorage.setItem(KEYS.expiresAt, String(at));
  }
}

export function clearTokens() {
  Object.values(KEYS).forEach((k) => sessionStorage.removeItem(k));
}

export function getAccessToken() {
  return sessionStorage.getItem(KEYS.access);
}

export function getRefreshToken() {
  return sessionStorage.getItem(KEYS.refresh);
}

export function getExpiresAt() {
  const v = sessionStorage.getItem(KEYS.expiresAt);
  return v ? Number(v) : 0;
}

export function hasFreshAccessToken() {
  const t = getAccessToken();
  if (!t) return false;
  const exp = getExpiresAt();
  if (!exp) return true;
  return Date.now() < exp;
}

export function setPkceVerifier(v) {
  sessionStorage.setItem(KEYS.pkceVerifier, v);
}

export function getPkceVerifier() {
  return sessionStorage.getItem(KEYS.pkceVerifier);
}

export function clearPkceVerifier() {
  sessionStorage.removeItem(KEYS.pkceVerifier);
}
