import { Link } from 'react-router-dom';
import { VerificationBadge, ConfidenceBadge } from '../components/TrustBadges';

/**
 * Operator-facing reference: listing verification, price sources, funnel metrics (moved off Opportunities banner).
 */
export default function Help() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 min-w-0 pb-16">
      <Link to="/opportunities" className="text-xs text-frost-dim hover:text-ember-light mb-6 inline-block">
        ← Opportunities
      </Link>
      <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Help &amp; trust</h1>
      <p className="text-sm text-frost-dim mb-8">
        How we think about card identity, reference prices, and badges on the trading desk.
      </p>

      <section className="space-y-4 text-sm text-frost-dim leading-relaxed mb-10">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-frost-light">Listing identity</h2>
        <p>
          Card identity is treated as <strong className="text-amber-400/90">unverified</strong> until automated cross-checks pass, or{' '}
          <strong className="text-loss/90">conflict</strong> if sources disagree. Profit math alone does not prove the photo matches the
          catalog row.
        </p>
        <p>
          <span className="text-frost-light font-medium">Price source</span> (SCP vs sold comps vs market comps) is where the{' '}
          <em>reference price</em> came from — not the same as photo or title verification.
        </p>
      </section>

      <section className="rounded-xl border border-surface-border bg-surface-card/50 p-4 sm:p-5 mb-6">
        <div className="text-[10px] uppercase tracking-wide text-frost-dim mb-3">Listing verification badges</div>
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <VerificationBadge status="pending" />
            <span className="text-xs">Automated identity pass not recorded yet</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <VerificationBadge status="verified" />
            <span className="text-xs">Cross-source check succeeded (when jobs set this)</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <VerificationBadge status="conflict" />
            <span className="text-xs">Open listing + SCP before acting</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <VerificationBadge status="skipped" />
            <span className="text-xs">No automated pass run for this row</span>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-surface-border bg-surface-card/50 p-4 sm:p-5 mb-10">
        <div className="text-[10px] uppercase tracking-wide text-frost-dim mb-3">Price reference</div>
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge source="scp" />
          <ConfidenceBadge source="sold_comps" />
          <ConfidenceBadge source="ebay_comps" />
        </div>
      </section>

      <p className="text-xs text-frost-dim/90">
        Funnel and disagreement metrics in repo:{' '}
        <a
          href="https://github.com/tweedledee101/TradingCards/blob/main/docs/testing/strategy.md"
          className="text-ember-light hover:underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          docs/testing/strategy.md
        </a>
        . Amber borders on cards mean lower match confidence — still verify manually.
      </p>
    </div>
  );
}
