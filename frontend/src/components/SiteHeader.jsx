import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

/**
 * Single site-wide header used by both the public storefront and the
 * authenticated app, so the top bar never changes shape as you move between
 * them. It adapts to auth + role:
 *   - logged out: Market + Sign In
 *   - buyer/seller: Market · Sell · Orders · Help + Sign out
 *   - operator: also Opportunities · Market Intel · Inventory · Watchlist · Business
 * Operator links are gated on isOperator (defense in depth is enforced backend-side).
 */
export default function SiteHeader() {
  const { authenticated, isOperator, login, logout } = useAuth();

  const linkClass = ({ isActive }) =>
    `px-2 py-1.5 sm:px-3 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
      isActive
        ? 'bg-ember-glow text-ember-light'
        : 'text-frost-dim hover:text-frost-light hover:bg-surface-raised'
    }`;

  return (
    <nav
      className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2 sm:py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between min-w-0">
        <NavLink to="/" className="flex items-center gap-2 sm:gap-2.5 min-w-0 shrink-0">
          <img src="/logo.png" alt="Ragnarok Gamez" className="w-10 h-10 sm:w-12 sm:h-12 object-contain shrink-0" />
          <span className="text-base sm:text-lg font-display font-semibold text-frost-light tracking-wide uppercase truncate">
            Ragnarok <span className="text-ember">Gamez</span>
          </span>
        </NavLink>

        <div className="flex flex-wrap items-center justify-center gap-1 md:justify-end w-full md:w-auto min-w-0">
          {/* Consumer surface */}
          <NavLink to="/market" className={linkClass}>Market</NavLink>
          {authenticated && <NavLink to="/sell" className={linkClass}>Sell</NavLink>}
          {authenticated && <NavLink to="/orders" className={linkClass}>Orders</NavLink>}

          {/* Private operator surface — never rendered for buyers/sellers */}
          {isOperator && (
            <>
              <NavLink to="/opportunities" className={linkClass}>Opportunities</NavLink>
              <NavLink to="/intel" className={linkClass}>Market Intel</NavLink>
              <NavLink to="/inventory" className={linkClass}>Inventory</NavLink>
              <NavLink to="/watchlist" className={linkClass}>Watchlist</NavLink>
              <NavLink to="/business" className={linkClass}>Business</NavLink>
              <NavLink to="/help" className={linkClass}>Help</NavLink>
            </>
          )}

          {authenticated ? (
            <button
              type="button"
              onClick={() => logout()}
              className="px-2 py-1.5 sm:px-3 sm:ml-1 rounded-lg text-xs sm:text-sm text-frost-dim hover:text-frost-light hover:bg-surface-raised"
            >
              Sign out
            </button>
          ) : (
            <button
              type="button"
              onClick={() => login()}
              className="px-4 py-2 sm:ml-1 rounded-lg bg-ember hover:bg-ember-glow text-white text-xs sm:text-sm font-medium transition-colors"
            >
              Sign In
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
