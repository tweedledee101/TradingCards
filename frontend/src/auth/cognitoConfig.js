/**
 * Cognito Hosted UI (OAuth2 + PKCE). Values from Vite env at build time.
 */
export function getCognitoConfig() {
  let domain = import.meta.env.VITE_COGNITO_DOMAIN || '';
  domain = domain.replace(/^https?:\/\//, '').replace(/\/$/, '');
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
  const redirectUri =
    import.meta.env.VITE_COGNITO_REDIRECT_URI || `${window.location.origin}/auth/callback`;

  if (!domain || !clientId) {
    throw new Error('Missing VITE_COGNITO_DOMAIN or VITE_COGNITO_CLIENT_ID');
  }
  return {
    domain,
    clientId,
    redirectUri,
    authorizeUrl: `https://${domain}/oauth2/authorize`,
    tokenUrl: `https://${domain}/oauth2/token`,
    logoutUrl: `https://${domain}/logout`,
  };
}
