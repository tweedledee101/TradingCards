import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import SiteFooter from '../components/SiteFooter';
import { SOCIAL_LINKS } from '../config/social';

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
    <div className="min-h-screen bg-surface text-frost-light flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-surface-border/60 bg-surface/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="font-display font-bold text-frost-light tracking-wide uppercase text-sm sm:text-base">
              Ragnarok <span className="text-ember">Gamez</span>
            </span>
          </div>
          <nav className="flex items-center gap-4">
            <a href="/shop" className="text-sm text-frost-dim hover:text-frost-light transition-colors">Shop</a>
            <button
              type="button"
              onClick={() => login()}
              className="px-4 py-2 rounded-lg bg-ember hover:bg-ember-glow text-white text-sm font-medium transition-colors"
            >
              Sign In
            </button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-ember/5 via-transparent to-surface-card/30" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-20 sm:py-32 flex flex-col lg:flex-row items-center gap-12">
          <div className="flex-1 text-center lg:text-left">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold tracking-tight leading-tight">
              Cards You Won't<br />
              Find <span className="text-ember">Anywhere Else</span>
            </h1>
            <p className="mt-5 text-base sm:text-lg text-frost-dim max-w-lg leading-relaxed">
              Ragnarok Exclusive: hand-picked cards listed directly by the collector who pulled them.
              Fixed prices, no bidding wars, no dealer markup — teased on Discord, TikTok, and Whatnot,
              sold only here.
            </p>
            <div className="mt-8 flex flex-wrap gap-3 justify-center lg:justify-start">
              <a
                href="/shop"
                className="px-6 py-3 rounded-xl bg-ember hover:bg-ember-glow text-white font-semibold text-sm transition-colors"
              >
                Browse the Shop
              </a>
              <button
                type="button"
                onClick={() => login()}
                className="px-6 py-3 rounded-xl border border-surface-border hover:border-frost-dim text-frost-light font-medium text-sm transition-colors"
              >
                Create Account
              </button>
            </div>

            {(SOCIAL_LINKS.discord || SOCIAL_LINKS.tiktok || SOCIAL_LINKS.whatnot) && (
              <div className="mt-6 flex items-center gap-4 justify-center lg:justify-start">
                <span className="text-xs text-frost-dim">Watch drops go live:</span>
                <div className="flex gap-3">
                  {SOCIAL_LINKS.discord && (
                    <a href={SOCIAL_LINKS.discord} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-frost-dim hover:text-ember-light transition-colors">Discord</a>
                  )}
                  {SOCIAL_LINKS.tiktok && (
                    <a href={SOCIAL_LINKS.tiktok} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-frost-dim hover:text-ember-light transition-colors">TikTok</a>
                  )}
                  {SOCIAL_LINKS.whatnot && (
                    <a href={SOCIAL_LINKS.whatnot} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-frost-dim hover:text-ember-light transition-colors">Whatnot</a>
                  )}
                </div>
              </div>
            )}
          </div>
          <div className="flex-1 max-w-md w-full flex items-center justify-center">
            <img
              src="/logo.png"
              alt="Ragnarok Gamez"
              className="w-64 h-64 sm:w-80 sm:h-80 object-contain"
            />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-surface-border/40 bg-surface-card/30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-display font-bold text-center mb-12">
            Why Ragnarok?
          </h2>
          <div className="grid sm:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-ember/10 flex items-center justify-center">
                <svg className="w-8 h-8 text-ember" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
                </svg>
              </div>
              <h3 className="font-display font-semibold text-frost-light mb-2">No Auction Fees</h3>
              <p className="text-sm text-frost-dim leading-relaxed">
                Buy direct at fixed prices. No bidding wars, no sniping, no surprise fees.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-ember/10 flex items-center justify-center">
                <svg className="w-8 h-8 text-ember" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
                </svg>
              </div>
              <h3 className="font-display font-semibold text-frost-light mb-2">Direct From the Source</h3>
              <p className="text-sm text-frost-dim leading-relaxed">
                No dropshippers, no unknown warehouses. Every card is pulled, photographed, and shipped personally.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-ember/10 flex items-center justify-center">
                <svg className="w-8 h-8 text-ember" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                </svg>
              </div>
              <h3 className="font-display font-semibold text-frost-light mb-2">Market Data</h3>
              <p className="text-sm text-frost-dim leading-relaxed">
                Real-time pricing from SportsCardsPro, eBay comps, and trend tracking so you know what cards are worth.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Social proof / secondary image */}
      <section className="border-t border-surface-border/40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24 flex flex-col lg:flex-row-reverse items-center gap-12">
          <div className="flex-1 text-center lg:text-left">
            <h2 className="text-2xl sm:text-3xl font-display font-bold">
              Built for Collectors<br />
              <span className="text-ember">Who Flip</span>
            </h2>
            <p className="mt-4 text-sm sm:text-base text-frost-dim leading-relaxed max-w-md">
              Track your portfolio, see what's trending, find undervalued cards, and move inventory fast. Whether you're flipping singles or building a collection, Ragnarok gives you the tools.
            </p>
            <button
              type="button"
              onClick={() => login()}
              className="mt-6 px-6 py-3 rounded-xl bg-ember hover:bg-ember-glow text-white font-semibold text-sm transition-colors"
            >
              Get Started Free
            </button>
          </div>
          <div className="flex-1 max-w-md w-full">
            <div className="rounded-2xl border border-surface-border/50 bg-surface-card shadow-2xl shadow-black/40 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-surface-border bg-surface-raised/60 flex items-center justify-between">
                <span className="text-xs font-medium text-frost-dim uppercase tracking-wide">Volume Leaders</span>
                <span className="text-[10px] text-frost-dim">preview</span>
              </div>
              <div className="p-4 space-y-2.5">
                {[
                  { name: 'Bobby Witt Jr', tag: 'Daily', price: '$71', color: 'text-gain' },
                  { name: 'Julio Rodriguez', tag: 'Weekly', price: '$54', color: 'text-ember-light' },
                  { name: 'Gunnar Henderson', tag: 'Weekly', price: '$38', color: 'text-ember-light' },
                ].map((row) => (
                  <div key={row.name} className="flex items-center justify-between bg-surface-raised/50 rounded-lg px-3 py-2.5">
                    <div>
                      <div className="text-sm font-medium text-frost-light">{row.name}</div>
                      <div className={`text-[10px] font-medium ${row.color}`}>{row.tag} sales</div>
                    </div>
                    <div className="text-sm font-mono font-bold text-frost-light">{row.price}</div>
                  </div>
                ))}
              </div>
              <div className="px-4 py-2.5 border-t border-surface-border text-[10px] text-frost-dim text-center">
                Real market data, updated daily
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-surface-border/40 bg-gradient-to-b from-surface-card/50 to-surface">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="text-2xl sm:text-3xl font-display font-bold">
            Ready to trade?
          </h2>
          <p className="mt-3 text-frost-dim text-sm sm:text-base">
            Create your free account and start buying in minutes.
          </p>
          <button
            type="button"
            onClick={() => login()}
            className="mt-8 px-8 py-3.5 rounded-xl bg-ember hover:bg-ember-glow text-white font-semibold text-base transition-colors"
          >
            Sign Up Free
          </button>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
