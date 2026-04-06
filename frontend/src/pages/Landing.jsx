import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

/**
 * Public marketing surface (ADR-007 / ROADMAP M3.1). Operators are redirected to /market.
 */
export default function Landing() {
  const { ready, authenticated, login } = useAuth();

  if (!ready) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <p className="text-frost-dim text-sm">Loading…</p>
      </div>
    );
  }

  if (authenticated) {
    return <Navigate to="/market" replace />;
  }

  return (
    <div className="min-h-screen bg-surface text-frost-light">
      <header className="border-b border-surface-border bg-surface-card/60 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-12 h-12 sm:w-14 sm:h-14 shrink-0">
              <img src="/logo.png" alt="" className="w-full h-full object-contain" aria-hidden />
            </div>
            <span className="font-display font-semibold text-frost-light tracking-wide uppercase truncate text-sm sm:text-base">
              Ragnarok <span className="text-ember">Gaming</span>
            </span>
          </div>
          <button
            type="button"
            onClick={() => login()}
            className="shrink-0 px-4 py-2 rounded-lg bg-ember hover:bg-ember-glow text-white text-sm font-medium transition-colors"
          >
            Sign in
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <p className="text-label mb-3">Trading cards, curated for collectors</p>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-display font-semibold text-frost-light tracking-tight max-w-3xl leading-tight">
          The public home for <span className="text-ember">Ragnarok</span> — retail, brand, and what we choose to show the hobby.
        </h1>
        <p className="mt-6 text-frost-dim text-base sm:text-lg max-w-2xl leading-relaxed">
          We are building a storefront and customer-facing experience here: browse what we sell, learn about breaks and events when we publish them, and shop with confidence. Internal buying tools and pipeline data stay private — this site is for fans and buyers, not a clone of our ops stack.
        </p>

        <div className="mt-10 grid sm:grid-cols-2 gap-4 sm:gap-6">
          <div className="card-surface p-5 sm:p-6">
            <h2 className="text-sm font-semibold text-frost-light uppercase tracking-wider mb-2">Storefront</h2>
            <p className="text-sm text-frost-dim leading-relaxed">
              Browse inventory synced from our channels — coming as we wire listings and checkout (see roadmap). No arbitrage console on this path.
            </p>
          </div>
          <div className="card-surface p-5 sm:p-6">
            <h2 className="text-sm font-semibold text-frost-light uppercase tracking-wider mb-2">Operator access</h2>
            <p className="text-sm text-frost-dim leading-relaxed mb-4">
              Market research, opportunities, and business tools are invite-only behind sign-in.
            </p>
            <button
              type="button"
              onClick={() => login()}
              className="text-sm font-medium text-ember-light hover:underline"
            >
              Sign in to the trading desk →
            </button>
          </div>
        </div>

        <p className="mt-12 text-xs text-frost-dim max-w-xl leading-relaxed">
          After sign-in, operators can open{' '}
          <Link to="/market" className="text-ember-light hover:underline">
            Market movers
          </Link>{' '}
          (trending cards) and{' '}
          <Link to="/opportunities" className="text-ember-light hover:underline">
            Opportunities
          </Link>
          . Public storefront and checkout are on the{' '}
          <a href="https://ragnarokgamez.com" className="text-ember-light hover:underline" target="_blank" rel="noopener noreferrer">
            main site
          </a>{' '}
          as we ship them.
        </p>
      </main>
    </div>
  );
}
