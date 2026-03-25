import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import LoginGate from './LoginGate';

export default function PrivateLayout() {
  const { ready, authenticated, logout } = useAuth();

  const navLinkClass = ({ isActive }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-ember-glow text-ember-light'
        : 'text-frost-dim hover:text-frost-light hover:bg-surface-raised'
    }`;

  if (!ready) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <p className="text-frost-dim text-sm">Loading…</p>
      </div>
    );
  }

  if (!authenticated) {
    return <LoginGate />;
  }

  return (
    <div className="min-h-screen bg-surface">
      <nav
        className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50"
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2.5">
            <div
              className="w-24 h-24 shrink-0"
              style={{
                maskImage: 'radial-gradient(circle, black 40%, transparent 70%)',
                WebkitMaskImage: 'radial-gradient(circle, black 40%, transparent 70%)',
              }}
            >
              <img src="/logo.png" alt="Ragnarok Games" className="w-full h-full object-contain" />
            </div>
            <span className="text-lg font-display font-semibold text-frost-light tracking-wide uppercase">
              Ragnarok <span className="text-ember">Gaming</span>
            </span>
          </NavLink>
          <div className="flex items-center gap-1">
            <NavLink to="/" className={navLinkClass} end>
              Trending
            </NavLink>
            <NavLink to="/opportunities" className={navLinkClass}>
              Opportunities
            </NavLink>
            <NavLink to="/inventory" className={navLinkClass}>
              Inventory
            </NavLink>
            <NavLink to="/watchlist" className={navLinkClass}>
              Watchlist
            </NavLink>
            <NavLink to="/business" className={navLinkClass}>
              Business
            </NavLink>
            <button
              type="button"
              onClick={() => logout()}
              className="ml-2 px-3 py-1.5 rounded-lg text-sm text-frost-dim hover:text-frost-light hover:bg-surface-raised"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
