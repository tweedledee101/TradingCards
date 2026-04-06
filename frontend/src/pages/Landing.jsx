import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import SiteFooter from '../components/SiteFooter';

/**
 * Public entry (ADR-007). Minimal, mobile-first — no long product copy.
 */
export default function Landing() {
  const { ready, authenticated, login } = useAuth();

  if (!ready) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center px-4">
        <p className="text-frost-dim text-sm">Loading…</p>
      </div>
    );
  }

  if (authenticated) {
    return <Navigate to="/market" replace />;
  }

  return (
    <div className="min-h-screen bg-surface text-frost-light flex flex-col">
      <header className="border-b border-surface-border/80 bg-surface-card/50 backdrop-blur-sm pt-[max(0.75rem,env(safe-area-inset-top,0px))]">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <img src="/logo.png" alt="" className="w-10 h-10 sm:w-11 sm:h-11 object-contain shrink-0" width={44} height={44} />
            <span className="font-display font-semibold text-frost-light tracking-wide uppercase truncate text-xs sm:text-sm">
              Ragnarok <span className="text-ember">Gaming</span>
            </span>
          </div>
          <button
            type="button"
            onClick={() => login()}
            className="shrink-0 min-h-[44px] px-4 rounded-xl bg-ember active:bg-ember-glow text-white text-sm font-medium transition-colors [touch-action:manipulation]"
          >
            Sign in
          </button>
        </div>
      </header>

      <main className="flex-1 flex flex-col justify-center px-4 py-10 sm:py-14 max-w-lg mx-auto w-full">
        <h1 className="text-2xl sm:text-3xl font-display font-semibold text-frost-light tracking-tight text-center leading-snug">
          Trading cards.
          <span className="block text-ember mt-1">Serious collectors.</span>
        </h1>
        <p className="mt-4 text-center text-sm text-frost-dim max-w-xs mx-auto leading-relaxed">
          Sign in for the desk. This page is the public front door.
        </p>
        <button
          type="button"
          onClick={() => login()}
          className="mt-8 w-full max-w-xs mx-auto min-h-[48px] rounded-xl bg-ember hover:bg-ember-glow active:opacity-95 text-white text-sm font-semibold transition-colors [touch-action:manipulation]"
        >
          Sign in to continue
        </button>
      </main>

      <SiteFooter />
    </div>
  );
}
