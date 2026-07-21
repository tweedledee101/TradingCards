import { useState, useEffect } from 'react';
import axios from 'axios';
import MarketDetailModal from '../components/MarketDetailModal';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const Market = () => {
  const [cards, setCards] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [volumeFilter, setVolumeFilter] = useState('daily_weekly');
  const [sort, setSort] = useState('volume');
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedCard, setSelectedCard] = useState(null);

  useEffect(() => {
    fetchCards();
    fetchStats();
  }, [volumeFilter, sort, offset]);

  const fetchCards = async (searchTerm = '') => {
    setLoading(true);
    try {
      const params = {
        volume_filter: volumeFilter,
        sort,
        limit: 50,
        offset,
        min_price: 5,
        max_price: 1000,
      };
      if (searchTerm) params.search = searchTerm;
      const resp = await axios.get(`${API_BASE}/api/market/volume-leaders`, { params });
      setCards(resp.data.cards || []);
      setTotal(resp.data.total || 0);
    } catch (err) {
      console.error('Market fetch error:', err);
      setCards([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/market/stats`);
      setStats(resp.data);
    } catch { setStats(null); }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setOffset(0);
    fetchCards(search);
  };

  const volumeLabel = (vol) => {
    if (!vol) return '';
    if (vol.includes('per day')) return 'Daily';
    if (vol.includes('per week')) return 'Weekly';
    if (vol.includes('per month')) return 'Monthly';
    return vol;
  };

  const volumeColor = (vol) => {
    if (!vol) return 'text-frost-dim';
    if (vol.includes('per day')) return 'text-gain';
    if (vol.includes('per week')) return 'text-ember-light';
    return 'text-frost-dim';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-bold text-frost-light">Volume Leaders</h1>
        <p className="text-xs text-frost-dim mt-1">Cards with proven sales velocity. Updated by SCP worm.</p>
        {stats && (
          <div className="flex gap-4 mt-3 text-xs text-frost-dim">
            <span><strong className="text-gain">{stats.daily_volume_cards}</strong> daily sellers</span>
            <span><strong className="text-ember-light">{stats.weekly_volume_cards}</strong> weekly sellers</span>
            <span><strong className="text-frost-light">{stats.monthly_volume_cards}</strong> monthly sellers</span>
            <span><strong>{stats.unique_players}</strong> players tracked</span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search player, set, parallel..."
            className="w-full px-3 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40"
          />
        </form>
        <select
          value={volumeFilter}
          onChange={(e) => { setVolumeFilter(e.target.value); setOffset(0); }}
          className="px-3 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light"
        >
          <option value="daily_weekly">Daily + Weekly</option>
          <option value="weekly">Weekly only</option>
          <option value="monthly">All (incl. Monthly)</option>
        </select>
        <select
          value={sort}
          onChange={(e) => { setSort(e.target.value); setOffset(0); }}
          className="px-3 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light"
        >
          <option value="volume">Highest Volume</option>
          <option value="price_desc">Price: High to Low</option>
          <option value="price_asc">Price: Low to High</option>
          <option value="player">Player A-Z</option>
        </select>
      </div>

      {/* Results count */}
      <div className="text-xs text-frost-dim mb-3">
        {total.toLocaleString()} cards
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-12 text-frost-dim text-sm">Loading...</div>
      ) : cards.length === 0 ? (
        <div className="text-center py-12 text-frost-dim text-sm">No volume cards found.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-frost-dim text-xs">
                <th className="text-left py-2 px-2">Player</th>
                <th className="text-left py-2 px-2">Year</th>
                <th className="text-left py-2 px-2">Set</th>
                <th className="text-left py-2 px-2">Parallel</th>
                <th className="text-left py-2 px-2">#</th>
                <th className="text-right py-2 px-2">Ungraded</th>
                <th className="text-right py-2 px-2">PSA 10</th>
                <th className="text-center py-2 px-2">Volume</th>
                <th className="text-center py-2 px-2">Links</th>
              </tr>
            </thead>
            <tbody>
              {cards.map((card, i) => (
                <tr
                  key={i}
                  className="border-b border-surface-border/50 hover:bg-surface-raised/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedCard(card)}
                >
                  <td className="py-2 px-2 font-medium text-frost-light hover:text-ember-light">{card.player_name}</td>
                  <td className="py-2 px-2 text-frost-dim">{card.card_year}</td>
                  <td className="py-2 px-2 text-frost-dim text-xs">{card.card_set}</td>
                  <td className="py-2 px-2">
                    {card.parallel && card.parallel !== 'Base' ? (
                      <span className="text-xs bg-ember/10 text-ember px-1.5 py-0.5 rounded">{card.parallel}</span>
                    ) : (
                      <span className="text-xs text-frost-dim">Base</span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-frost-dim text-xs">#{card.card_number}</td>
                  <td className="py-2 px-2 text-right font-mono text-frost-light">${card.price?.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right font-mono text-frost-dim">
                    {card.psa_10 ? `$${card.psa_10.toFixed(0)}` : '-'}
                  </td>
                  <td className={`py-2 px-2 text-center text-xs font-medium ${volumeColor(card.volume)}`}>
                    {volumeLabel(card.volume)}
                  </td>
                  <td className="py-2 px-2 text-center" onClick={e => e.stopPropagation()}>
                    <div className="flex gap-1 justify-center">
                      {card.scp_url && (
                        <a href={card.scp_url} target="_blank" rel="noopener noreferrer"
                           className="text-[10px] text-frost-dim hover:text-ember transition-colors">
                          SCP
                        </a>
                      )}
                      <a href={`https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + (card.parallel || ''))}&_sacat=261328&LH_Auction=1`}
                         target="_blank" rel="noopener noreferrer"
                         className="text-[10px] text-frost-dim hover:text-ember transition-colors">
                        eBay
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-4 mt-6">
          <button
            onClick={() => setOffset(o => Math.max(0, o - 50))}
            disabled={offset === 0}
            className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-frost-dim">
            {offset + 1}-{Math.min(offset + 50, total)} of {total.toLocaleString()}
          </span>
          <button
            onClick={() => setOffset(o => o + 50)}
            disabled={offset + 50 >= total}
            className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}

      {selectedCard && (
        <MarketDetailModal card={selectedCard} onClose={() => setSelectedCard(null)} />
      )}
    </div>
  );
};

export default Market;
