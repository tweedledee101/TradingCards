import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getWatchlist, removeFromWatchlist } from '../api/client';

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadWatchlist(); }, []);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const data = await getWatchlist();
      setWatchlist(data.watchlist || []);
    } catch (error) {
      console.error('Failed to load watchlist:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await removeFromWatchlist(id);
      setWatchlist(prev => prev.filter(w => w.id !== id));
    } catch (error) {
      console.error('Failed to remove:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Loading watchlist...</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Watchlist</h1>
        <p className="text-sm text-frost-dim">Price targets and alerts</p>
      </div>

      {/* Empty state */}
      {watchlist.length === 0 && (
        <div className="card-surface p-12 text-center">
          <div className="text-frost-light font-medium mb-1">Watchlist empty</div>
          <div className="text-xs text-frost-dim">Add cards from the Trending page to monitor prices.</div>
        </div>
      )}

      {/* Watchlist */}
      <div className="space-y-2">
        {watchlist.map(item => {
          const current = item.current_price;
          const target = item.target_price;
          const diff = current && target ? current - target : null;
          const diffPct = diff && target ? ((diff / target) * 100).toFixed(1) : null;
          const belowTarget = diff !== null && diff <= 0;
          const hotness = item.trend?.hotness_score;

          return (
            <Link
              key={item.id}
              to={`/card/${item.card?.id}`}
              className={`card-surface-hover flex items-center gap-4 px-4 py-3 ${belowTarget ? 'border-gain/30' : ''}`}
            >
              {/* Card info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-semibold text-frost-light truncate">{item.card?.player_name}</span>
                  {belowTarget && (
                    <span className="badge-gain text-[10px]">Below Target</span>
                  )}
                </div>
                <div className="text-xs text-frost-dim truncate">
                  {item.card?.card_year} {item.card?.card_set}
                  {item.card?.card_number ? ` #${item.card.card_number}` : ''}
                </div>
              </div>

              {/* Target */}
              <div className="text-right shrink-0 w-20">
                <div className="text-xs text-frost-dim">Target</div>
                <div className="text-sm font-mono font-semibold text-frost-light">
                  {target ? `$${target}` : '--'}
                </div>
              </div>

              {/* Current */}
              <div className="text-right shrink-0 w-20">
                <div className="text-xs text-frost-dim">Current</div>
                <div className="text-sm font-mono font-semibold text-frost-light">
                  {current ? `$${current}` : '--'}
                </div>
              </div>

              {/* Difference */}
              <div className="text-right shrink-0 w-24">
                <div className="text-xs text-frost-dim">Difference</div>
                {diff !== null ? (
                  <div className={`text-sm font-mono font-semibold ${diff <= 0 ? 'text-gain' : 'text-loss'}`}>
                    {diff <= 0 ? '-' : '+'}${Math.abs(diff).toFixed(2)}
                    <span className="text-[10px] ml-1">({diffPct}%)</span>
                  </div>
                ) : (
                  <div className="text-sm text-frost-dim">--</div>
                )}
              </div>

              {/* Hotness */}
              <div className="text-center shrink-0 w-14">
                {hotness != null ? (
                  <div className={`px-2 py-1 rounded-lg border ${
                    hotness >= 70 ? 'bg-ember-glow border-ember/20' : hotness >= 40 ? 'bg-amber-500/10 border-amber-500/20' : 'bg-surface-raised border-surface-border'
                  }`}>
                    <div className={`text-sm font-bold font-mono ${hotness >= 70 ? 'text-ember-light' : hotness >= 40 ? 'text-amber-400' : 'text-frost-dim'}`}>
                      {hotness.toFixed(0)}
                    </div>
                    <div className="text-[9px] text-frost-dim uppercase tracking-wider">heat</div>
                  </div>
                ) : (
                  <div className="text-frost-dim text-xs">--</div>
                )}
              </div>

              {/* Remove */}
              <button
                onClick={(e) => handleRemove(e, item.id)}
                className="shrink-0 px-2 py-1 rounded-lg text-xs text-frost-dim hover:text-loss hover:bg-loss/10 border border-transparent hover:border-loss/20 transition-colors"
                title="Remove from watchlist"
              >
                Remove
              </button>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
