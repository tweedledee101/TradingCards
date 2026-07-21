import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const MarketDetailModal = ({ card, onClose }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    axios.get(`${API_BASE}/api/players/${encodeURIComponent(card.player_name)}/stats`)
      .then(resp => { if (active) setStats(resp.data); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [card.player_name]);

  const hasRealStats = stats && (stats.total_sales > 0 || stats.active_listings > 0);

  const ebaySearch = `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(
    card.player_name + ' ' + card.card_year + ' ' + card.card_set +
    (card.card_number ? ' #' + card.card_number : '') +
    (card.parallel && card.parallel !== 'Base' ? ' ' + card.parallel : '')
  )}&LH_BIN=1&_sop=15`;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-surface-card rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto border border-surface-border"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface-card/95 backdrop-blur-sm border-b border-surface-border px-5 py-3 flex items-center justify-between">
          <span className="text-xs font-medium text-frost-dim uppercase tracking-wide">Volume Leader</span>
          <button onClick={onClose} className="text-frost-dim hover:text-frost-light text-sm px-2">✕ Close</button>
        </div>

        <div className="p-5">
          <h2 className="text-lg font-display font-semibold text-frost-light leading-snug">
            {card.player_name}
          </h2>
          <div className="text-xs text-frost-dim mt-1">
            {card.card_year} {card.card_set} #{card.card_number}
            {card.parallel && card.parallel !== 'Base' && (
              <span className="ml-1.5 text-ember-light">{card.parallel}</span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3 mt-4">
            <StatBox label="Ungraded" value={card.price ? `$${card.price.toFixed(2)}` : '—'} />
            <StatBox label="Grade 9" value={card.grade_9 ? `$${Number(card.grade_9).toFixed(0)}` : '—'} />
            <StatBox label="PSA 10" value={card.psa_10 ? `$${Number(card.psa_10).toFixed(0)}` : '—'} />
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs">
            <span className="text-frost-dim">Sales volume:</span>
            <span className="text-frost-light font-medium">{card.volume}</span>
          </div>

          <div className="mt-5 border-t border-surface-border pt-4">
            <div className="text-label mb-2">Market Stats</div>
            {loading ? (
              <div className="text-xs text-frost-dim">Loading market data...</div>
            ) : hasRealStats ? (
              <div className="grid grid-cols-2 gap-3">
                <StatBox label="Avg Sale (30d)" value={stats.avg_sale_price_30d ? `$${stats.avg_sale_price_30d}` : '—'} />
                <StatBox label="Sales (30d)" value={stats.recent_sales_30d} />
                <StatBox label="Active Listings" value={stats.active_listings} />
                <StatBox label="Velocity" value={stats.velocity} />
              </div>
            ) : (
              <div className="text-xs text-frost-dim">No deeper sales history tracked for this player yet.</div>
            )}
          </div>

          <div className="mt-5 flex gap-2">
            {card.scp_url && (
              <a href={card.scp_url} target="_blank" rel="noopener noreferrer"
                 className="flex-1 text-center px-4 py-2 rounded-lg text-sm bg-surface-raised border border-surface-border text-frost-light hover:border-ember/30 transition-colors">
                View on SCP
              </a>
            )}
            <a href={ebaySearch} target="_blank" rel="noopener noreferrer"
               className="flex-1 text-center px-4 py-2 rounded-lg text-sm bg-ember/10 text-ember hover:bg-ember/20 transition-colors">
              Find on eBay
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatBox = ({ label, value }) => (
  <div className="bg-surface-raised rounded-lg p-2.5 text-center">
    <div className="text-[10px] text-frost-dim mb-1">{label}</div>
    <div className="text-sm font-mono font-bold text-frost-light">{value ?? '—'}</div>
  </div>
);

export default MarketDetailModal;
