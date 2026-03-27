import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTrendingCards } from '../api/client';

const Home = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('hotness');
  const [page, setPage] = useState(1);
  const perPage = 20;

  useEffect(() => {
    fetchCards();
  }, []);

  const fetchCards = async () => {
    setLoading(true);
    try {
      const data = await getTrendingCards(200);
      setCards(data.cards || []);
    } catch (err) {
      const st = err.response?.status;
      setError(
        st
          ? `Failed to load trending cards (HTTP ${st})`
          : 'Failed to load trending cards',
      );
    } finally {
      setLoading(false);
    }
  };

  const sorted = [...cards].sort((a, b) => {
    if (sortBy === 'volume') return b.sales_count - a.sales_count;
    if (sortBy === 'velocity') return b.velocity_score - a.velocity_score;
    if (sortBy === 'price') return b.avg_price - a.avg_price;
    return b.hotness_score - a.hotness_score;
  });

  const totalPages = Math.ceil(sorted.length / perPage);
  const display = sorted.slice((page - 1) * perPage, page * perPage);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Loading market data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-loss text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Market Movers</h1>
        <p className="text-sm text-frost-dim">
          {cards.length} cards ranked by market activity
        </p>
        {cards.length === 0 && (
          <p className="mt-3 text-xs text-frost-dim max-w-xl leading-relaxed border border-surface-border rounded-lg px-3 py-2 bg-surface-card/50">
            This list only includes cards with <span className="text-frost-light">sold eBay listings in the last 30 days</span>.
            If your database has catalog rows but no recent sales, you will see nothing here — run the sales/card import pipeline (e.g.{' '}
            <code className="text-[10px] font-mono text-frost-light">python -m backend.run_pipeline_full</code>
            ) or check the <Link to="/opportunities" className="text-ember-light hover:underline">Opportunities</Link> tab (separate data).
          </p>
        )}
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-2 mb-6">
        <span className="text-label">Sort by</span>
        {['hotness', 'volume', 'velocity', 'price'].map((key) => (
          <button
            key={key}
            onClick={() => { setSortBy(key); setPage(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              sortBy === key
                ? 'bg-ember-glow text-ember-light border border-ember/20'
                : 'bg-surface-card text-frost-dim border border-surface-border hover:text-frost-light'
            }`}
          >
            {key === 'hotness' ? 'Hotness' : key === 'volume' ? 'Volume' : key === 'velocity' ? 'Velocity' : 'Price'}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={fetchCards}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-card text-frost-dim border border-surface-border hover:text-frost-light transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Card list */}
      <div className="space-y-3">
        {display.map((card, idx) => {
          const rank = (page - 1) * perPage + idx + 1;
          return <TrendingCard key={card.card_id || idx} card={card} rank={rank} />;
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-card border border-surface-border text-frost-dim hover:text-frost-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-frost-dim">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-card border border-surface-border text-frost-dim hover:text-frost-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};


const TrendingCard = ({ card, rank }) => {
  const hotness = card.hotness_score || 0;
  const velocity = card.velocity_score || 0;
  const volume = card.sales_count || 0;
  const price = card.avg_price || 0;

  // Heat level determines accent
  const isHot = hotness >= 70;
  const isWarm = hotness >= 40;

  const heatColor = isHot ? 'text-ember-light' : isWarm ? 'text-amber-400' : 'text-frost-dim';
  const heatBg = isHot ? 'bg-ember-glow border-ember/20' : isWarm ? 'bg-amber-500/10 border-amber-500/20' : 'bg-surface-raised border-surface-border';
  const rankColor = rank <= 3 ? 'text-ember-light' : rank <= 10 ? 'text-frost-light' : 'text-frost-dim';

  // What makes this card a mover - pick the top signal
  const signals = [];
  if (velocity > 50) signals.push({ label: 'Price surging', type: 'hot' });
  else if (velocity > 20) signals.push({ label: 'Price rising', type: 'warm' });
  else if (velocity < -20) signals.push({ label: 'Price dropping', type: 'cold' });

  if (volume >= 30) signals.push({ label: `${volume} sales/wk`, type: 'hot' });
  else if (volume >= 10) signals.push({ label: `${volume} sales/wk`, type: 'warm' });
  else signals.push({ label: `${volume} sales/wk`, type: 'neutral' });

  if (card.category?.includes('FIRE')) signals.push({ label: 'On fire', type: 'hot' });

  return (
    <Link
      to={`/card/${card.card_id}`}
      className="card-surface-hover flex items-center gap-4 px-4 py-3 group"
    >
      {/* Rank */}
      <div className={`w-8 text-right font-mono text-sm font-bold ${rankColor} shrink-0`}>
        {rank}
      </div>

      {/* Image */}
      <div className="w-12 h-16 rounded-md overflow-hidden bg-surface-raised shrink-0">
        {card.image_url ? (
          <img
            src={card.image_url}
            alt=""
            className="w-full h-full object-cover"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">
            --
          </div>
        )}
      </div>

      {/* Card info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-frost-light truncate">
            {card.player_name}
          </span>
          {card.parallel && card.parallel !== 'Base' && (
            <span className="badge-neutral text-[10px]">{card.parallel}</span>
          )}
          {card.is_rookie && (
            <span className="badge-ember text-[10px]">RC</span>
          )}
        </div>
        <div className="text-xs text-frost-dim truncate">
          {card.card_year} {card.card_set}
          {card.card_number ? ` #${card.card_number}` : ''}
        </div>
      </div>

      {/* Signals - WHY it's moving */}
      <div className="flex items-center gap-2 shrink-0">
        {signals.slice(0, 2).map((sig, i) => (
          <span
            key={i}
            className={`text-[10px] font-medium px-2 py-0.5 rounded-md ${
              sig.type === 'hot'
                ? 'bg-ember-glow text-ember-light'
                : sig.type === 'warm'
                ? 'bg-amber-500/10 text-amber-400'
                : sig.type === 'cold'
                ? 'bg-loss/10 text-loss'
                : 'bg-surface-raised text-frost-dim'
            }`}
          >
            {sig.label}
          </span>
        ))}
      </div>

      {/* Price */}
      <div className="text-right shrink-0 w-20">
        <div className="text-sm font-semibold font-mono text-frost-light">
          ${price.toFixed(2)}
        </div>
        <div className={`text-[10px] font-mono ${velocity > 0 ? 'text-gain' : velocity < 0 ? 'text-loss' : 'text-frost-dim'}`}>
          {velocity > 0 ? '+' : ''}{velocity.toFixed(1)}%
        </div>
      </div>

      {/* Hotness */}
      <div className={`w-14 text-center shrink-0 px-2 py-1 rounded-lg border ${heatBg}`}>
        <div className={`text-sm font-bold font-mono ${heatColor}`}>
          {hotness.toFixed(0)}
        </div>
        <div className="text-[9px] text-frost-dim uppercase tracking-wider">heat</div>
      </div>
    </Link>
  );
};


export default Home;
