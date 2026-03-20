import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getInventory, getInventoryStats } from '../api/client';

export default function Inventory() {
  const [inventory, setInventory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('owned');

  useEffect(() => { loadData(); }, [filter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [invData, statsData] = await Promise.all([
        getInventory(filter),
        getInventoryStats(),
      ]);
      setInventory(invData.inventory || []);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load inventory:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Loading inventory...</div>
      </div>
    );
  }

  const filters = [
    { key: 'owned', label: 'In Hand' },
    { key: 'listed', label: 'Listed' },
    { key: 'sold', label: 'Sold' },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Inventory</h1>
        <p className="text-sm text-frost-dim">Portfolio tracking and P&L</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Invested" value={`$${stats.total_invested}`} />
          <StatCard label="Current Value" value={`$${stats.current_value}`} />
          <StatCard label="Profit" value={`$${stats.total_profit}`} gain={stats.total_profit >= 0} loss={stats.total_profit < 0} />
          <StatCard label="ROI" value={`${stats.roi_percentage}%`} gain={stats.roi_percentage >= 0} loss={stats.roi_percentage < 0} />
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-2 mb-6">
        {filters.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f.key
                ? 'bg-ember-glow text-ember-light border border-ember/20'
                : 'bg-surface-card text-frost-dim border border-surface-border hover:text-frost-light'
            }`}
          >
            {f.label}
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-xs text-frost-dim">{inventory.length} card{inventory.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Empty state */}
      {inventory.length === 0 && (
        <div className="card-surface p-12 text-center">
          <div className="text-frost-light font-medium mb-1">No cards in {filter}</div>
          <div className="text-xs text-frost-dim">Add cards from the Opportunities page when you make a purchase.</div>
        </div>
      )}

      {/* Inventory list */}
      <div className="space-y-2">
        {inventory.map(item => {
          const profit = item.unrealized_profit;
          const roiPct = item.roi_percentage;
          return (
            <Link
              key={item.id}
              to={`/card/${item.card?.id}`}
              className="card-surface-hover flex items-center gap-4 px-4 py-3"
            >
              {/* Card info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-semibold text-frost-light truncate">{item.card?.player_name}</span>
                  {item.graded && (
                    <span className="badge-neutral text-[10px]">{item.grade_company} {item.grade_value}</span>
                  )}
                  {!item.graded && (
                    <span className="badge-neutral text-[10px]">Raw</span>
                  )}
                </div>
                <div className="text-xs text-frost-dim truncate">
                  {item.card?.card_year} {item.card?.card_set}
                  {item.card?.card_number ? ` #${item.card.card_number}` : ''}
                  {item.card?.parallel && item.card.parallel !== 'Base' ? ` — ${item.card.parallel}` : ''}
                </div>
              </div>

              {/* Purchase */}
              <div className="text-right shrink-0 w-24">
                <div className="text-xs text-frost-dim">Purchased</div>
                <div className="text-sm font-mono font-semibold text-frost-light">${item.purchase_price}</div>
                <div className="text-[10px] text-frost-dim">{item.purchase_date}</div>
              </div>

              {/* Current value */}
              <div className="text-right shrink-0 w-20">
                <div className="text-xs text-frost-dim">Current</div>
                <div className="text-sm font-mono font-semibold text-frost-light">
                  {item.current_value ? `$${item.current_value}` : '--'}
                </div>
              </div>

              {/* Profit */}
              <div className="text-right shrink-0 w-20">
                <div className="text-xs text-frost-dim">Profit</div>
                <div className={`text-sm font-mono font-semibold ${profit >= 0 ? 'text-gain' : 'text-loss'}`}>
                  {profit != null ? `${profit >= 0 ? '+' : ''}$${profit}` : '--'}
                </div>
              </div>

              {/* ROI */}
              <div className="text-right shrink-0 w-16">
                <div className="text-xs text-frost-dim">ROI</div>
                <div className={`text-sm font-mono font-semibold ${roiPct >= 0 ? 'text-gain' : 'text-loss'}`}>
                  {roiPct != null ? `${roiPct}%` : '--'}
                </div>
              </div>

              {/* Qty */}
              <div className="text-center shrink-0 w-10">
                <div className="text-xs text-frost-dim">Qty</div>
                <div className="text-sm font-mono text-frost-light">{item.quantity}</div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}


const StatCard = ({ label, value, gain, loss }) => (
  <div className="card-surface p-3 text-center">
    <div className="text-label mb-1">{label}</div>
    <div className={`text-lg font-bold font-mono ${gain ? 'text-gain' : loss ? 'text-loss' : 'text-frost-light'}`}>
      {value}
    </div>
  </div>
);
