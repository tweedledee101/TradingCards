import { getCognitoConfig } from './cognitoConfig';
import {
  setTokens,
  clearTokens,
  setPkceVerifier,
  getPkceVerifier,
  clearPkceVerifier,
  getRefreshToken,
} from './tokenStorage';
import { createPkcePair } from './pkce';

const STATE_KEY = 'rg_oauth_state';

export async function redirectToHostedLogin() {
  const cfg = getCognitoConfig();
  const { verifier, challenge } = await createPkcePair();
  setPkceVerifier(verifier);
  const state = crypto.randomUUID();
  sessionStorage.setItem(STATE_KEY, state);
  const params = new URLSearchParams({
    client_id: cfg.clientId,
    response_type: 'code',
    scope: 'openid email profile',
    redirect_uri: cfg.redirectUri,
    code_challenge_method: 'S256',
    code_challenge: challenge,
    state,
  });
  window.location.assign(`${cfg.authorizeUrl}?${params.toString()}`);
}

export async function exchangeCodeForTokens(code, state) {
  const expected = sessionStorage.getItem(STATE_KEY);
  sessionStorage.removeItem(STATE_KEY);
  if (!expected || state !== expected) {
    throw new Error('Invalid OAuth state');
  }
  const verifier = getPkceVerifier();
  if (!verifier) throw new Error('Missing PKCE verifier');
  const cfg = getCognitoConfig();
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: cfg.clientId,
    code,
    redirect_uri: cfg.redirectUri,
    code_verifier: verifier,
  });
  const res = await fetch(cfg.tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  clearPkceVerifier();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${text}`);
  }
  const tok = await res.json();
  setTokens({
    access_token: tok.access_token,
    id_token: tok.id_token,
    refresh_token: tok.refresh_token,
    expires_in: tok.expires_in,
  });
  return tok;
}

export async function refreshAccessToken() {
  const rt = getRefreshToken();
  if (!rt) return false;
  const cfg = getCognitoConfig();
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    client_id: cfg.clientId,
    refresh_token: rt,
  });
  const res = await fetch(cfg.tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!res.ok) {
    clearTokens();
    return false;
  }
  const tok = await res.json();
  setTokens({
    access_token: tok.access_token,
    id_token: tok.id_token,
    refresh_token: tok.refresh_token || rt,
    expires_in: tok.expires_in,
  });
  return true;
}

export function redirectToLogout() {
  clearTokens();
  clearPkceVerifier();
  const cfg = getCognitoConfig();
  const logoutUri = window.location.origin + '/';
  const params = new URLSearchParams({
    client_id: cfg.clientId,
    logout_uri: logoutUri,
  });
  window.location.assign(`${cfg.logoutUrl}?${params.toString()}`);
}
