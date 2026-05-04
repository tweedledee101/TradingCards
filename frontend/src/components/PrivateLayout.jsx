import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import LoginGate from './LoginGate';
import SiteFooter from './SiteFooter';

export default function PrivateLayout() {
  const { ready, authenticated, logout } = useAuth();

  const navLinkClass = ({ isActive }) =>
    `px-2 py-1.5 sm:px-3 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
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
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2 sm:py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between min-w-0">
          <NavLink to="/" className="flex items-center gap-2 sm:gap-2.5 min-w-0 shrink-0">
            <div
              className="w-14 h-14 sm:w-20 sm:h-20 md:w-24 md:h-24 shrink-0"
              style={{
                maskImage: 'radial-gradient(circle, black 40%, transparent 70%)',
                WebkitMaskImage: 'radial-gradient(circle, black 40%, transparent 70%)',
              }}
            >
              <img src="/logo.png" alt="Ragnarok Games" className="w-full h-full object-contain" />
            </div>
            <span className="text-base sm:text-lg font-display font-semibold text-frost-light tracking-wide uppercase truncate">
              Ragnarok <span className="text-ember">Gaming</span>
            </span>
          </NavLink>
          <div className="flex flex-wrap items-center justify-center gap-1 sm:gap-1 md:justify-end w-full md:w-auto min-w-0">
            <NavLink to="/shop" className={navLinkClass}>
              Shop
            </NavLink>
            <NavLink to="/market" className={navLinkClass}>
              Market
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
            <NavLink to="/help" className={navLinkClass}>
              Help
            </NavLink>
            <button
              type="button"
              onClick={() => logout()}
              className="px-2 py-1.5 sm:px-3 sm:ml-1 rounded-lg text-xs sm:text-sm text-frost-dim hover:text-frost-light hover:bg-surface-raised"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>
      <main className="flex-1 w-full min-w-0">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
