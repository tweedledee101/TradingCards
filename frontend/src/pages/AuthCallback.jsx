import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { exchangeCodeForTokens } from '../auth/cognitoOAuth';
import { useAuth } from '../auth/AuthContext';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const err = searchParams.get('error');
    const desc = searchParams.get('error_description');
    if (err) {
      setError(desc || err);
      return;
    }
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    if (!code || !state) {
      setError('Missing authorization code');
      return;
    }
    const guardKey = `rg_oauth_${code}`;
    const phase = sessionStorage.getItem(guardKey);
    if (phase === 'done') {
      navigate('/', { replace: true });
      return;
    }
    if (phase === 'pending') {
      return;
    }
    sessionStorage.setItem(guardKey, 'pending');
    let cancelled = false;
    (async () => {
      try {
        await exchangeCodeForTokens(code, state);
        sessionStorage.setItem(guardKey, 'done');
        if (!cancelled) {
          await refreshSession();
          navigate('/', { replace: true });
        }
      } catch (e) {
        sessionStorage.removeItem(guardKey);
        if (!cancelled) setError(e.message || 'Sign-in failed');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchParams, navigate, refreshSession]);

  if (error) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="max-w-md text-center space-y-4">
          <p className="text-red-400 text-sm">{error}</p>
          <button
            type="button"
            onClick={() => navigate('/', { replace: true })}
            className="px-4 py-2 rounded-lg bg-ember text-white text-sm"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <p className="text-frost-dim text-sm">Signing you in…</p>
    </div>
  );
}
