import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const Shop = () => {
  const [cards, setCards] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchCards();
    fetchStats();
  }, [page]);

  const fetchCards = async (searchTerm = '') => {
    setLoading(true);
    try {
      const params = { page, limit: 50 };
      if (searchTerm) params.search = searchTerm;
      const resp = await axios.get(`${API_BASE}/api/shop/ebay`, { params });
      setCards(resp.data.cards || []);
      setTotal(resp.data.total || 0);
    } catch (err) {
      console.error('Shop fetch error:', err);
      setCards([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/shop/ebay/stats`);
      setStats(resp.data);
    } catch { setStats(null); }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchCards(search);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Shop Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-display font-bold text-frost-light tracking-wide">
          Ragnarok Gaming Cards
        </h1>
        <p className="text-sm text-frost-dim mt-2">
          Trading cards for sale. Fast shipping. All cards ship from eBay.
        </p>
        {stats && (
          <div className="flex justify-center gap-6 mt-4 text-xs text-frost-dim">
            <span><strong className="text-frost-light">{stats.cards_listed}</strong> cards listed</span>
            <span>Total value: <strong className="text-frost-light">${stats.total_ask_value?.toLocaleString()}</strong></span>
          </div>
        )}
      </div>

      {/* Search */}
      <div className="flex flex-wrap gap-3 mb-6">
        <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cards..."
            className="w-full px-3 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40"
          />
        </form>
      </div>

      {/* Results count */}
      <div className="text-xs text-frost-dim mb-4">
        {total} card{total !== 1 ? 's' : ''} available
      </div>

      {/* Card Grid */}
      {loading ? (
        <div className="text-center py-12 text-frost-dim text-sm">Loading inventory...</div>
      ) : cards.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-frost-dim text-sm">No cards listed yet.</p>
          <p className="text-frost-dim text-xs mt-2">Check back soon.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {cards.map((card) => (
            <ShopCard key={card.id} card={card} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-frost-dim">Page {page}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={cards.length < 50}
            className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

const ShopCard = ({ card }) => {
  return (
    <div className="card-surface overflow-hidden hover:border-ember/30 transition-colors group">
      {/* Image */}
      <div className="aspect-[2.5/3.5] bg-surface-raised relative overflow-hidden">
        {card.image_url ? (
          <img
            src={card.image_url}
            alt={card.title}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">
            No Image
          </div>
        )}
        {/* Price badge */}
        {card.price && (
          <div className="absolute top-2 right-2 bg-surface-base/90 backdrop-blur-sm rounded-md px-2 py-1">
            <span className="text-sm font-mono font-bold text-gain">${card.price.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-2.5">
        <div className="text-xs font-semibold text-frost-light line-clamp-2">{card.title}</div>
        <div className="flex items-center justify-between mt-2">
          {card.ebay_url && (
            <a
              href={card.ebay_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-ember/90 hover:bg-ember text-white px-3 py-1 rounded-md transition-colors"
            >
              Buy on eBay
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default Shop;
